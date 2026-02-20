import os
import json
from typing import AsyncGenerator

from groq import AsyncGroq
from openai import OpenAI
from httpx import AsyncClient

from ..services import (
    set_user_data
)

import json
import aiohttp
from openai import AsyncOpenAI
from groq import AsyncGroq
from typing import AsyncGenerator

async def run_llm(
    messages : list[dict[str , str]] , 
    provider : str , 
    model : str , 
    response_format : dict[str , str] | None , 
    client : AsyncGroq | AsyncOpenAI | aiohttp.ClientSession | OpenAI ,
    temperature : float = 1, 
    stream : bool = False
) -> str | AsyncGenerator[str , None] : 

    if provider == 'groq' : 

        resp = await client.chat.completions.create(
            model = model , 
            messages = messages , 
            temperature = temperature , 
            response_format = response_format , 
            stream = stream
        )

        if stream : 

            async def groq_gen() : 

                async for chunk in resp : 

                    if chunk.choices[0].delta.content : 
                        yield chunk.choices[0].delta.content

            return groq_gen()

        return resp.choices[0].message.content

    elif provider == 'openai' : 

        if 'gpt-5' in model : 
            resp = client.chat.completions.create(
                model = model , 
                messages = messages , 
                # temperature = temperature , 
                response_format = response_format , 
                stream = stream
            )

        else : 
            resp = client.chat.completions.create(
                model = model , 
                messages = messages , 
                temperature = temperature , 
                response_format = response_format , 
                stream = stream
            )

        if stream : 

            async def openai_gen() : 

                for chunk in resp : 

                    if chunk.choices and chunk.choices[0].delta.content : 
                        yield chunk.choices[0].delta.content

            return openai_gen()

        return resp.choices[0].message.content

    elif provider == 'openrouter' : 

        payload = {
            'model' : model , 
            'messages' : messages , 
            'temperature' : temperature , 
            'stream' : stream
        }

        headers = {
            'Authorization' : f'Bearer {os.environ['OPENROUTER_API_KEY']}' , 
            'Content-Type' : 'application/json'
        }

        if stream : 

            async def gen() : 

                async with client.post(
                    url = 'https://openrouter.ai/api/v1/chat/completions' ,  
                    json = payload , 
                    headers = headers
                ) as response : 

                    async for line in response.content : 

                        line = line.decode('utf-8').strip()

                        if line.startswith('data: ') : 

                            data_str = line[6:]

                            if data_str == '[DONE]' : break

                            try : 

                                data = json.loads(data_str)
                                content = data['choices'][0]['delta'].get('content')

                                if content : yield content

                            except : continue
            return gen()

        else : 
            async with client.post(
                url = 'https://openrouter.ai/api/v1/chat/completions' ,  
                json = payload , 
                headers = headers
            ) as response : 

                result = await response.json()
                return result['choices'][0]['message']['content']

    else : 
        raise NotImplementedError(f'Provider "{provider}" not implemented')

async def get_manager_decision(
    history , 
    slots , 
    user_msg , 
    prompt : str , 
    config : dict , 
    client 
) -> dict : 

    last_bot = 'None'

    for row in reversed(history) : 

        if row['role'] == 'assistant' : 

            last_bot = row['content']

            break

    conv_history = '\n'.join(
        f'{h["role"]}: {h["content"]}' for h in history[-6 :]
    ) or 'None'

    prompt = prompt.replace(
        '{previous_slots}' , json.dumps(slots)
    ).replace(
        '{last_bot_message}' , last_bot
    ).replace(
        '{conversation_history}' , conv_history
    )

    try : 

        response : str = await run_llm(
            messages = [
                {
                    'role' : 'system' ,
                    'content' : prompt
                } , 
                {
                    'role' : 'user' , 
                    'content' : user_msg
                } , 
            ] , 
            provider = config['provider'] , 
            model = config['model'] , 
            response_format = {'type' : 'json_object'} , 
            temperature = 0 , 
            client = client
        )

        return json.loads(response)

    except Exception as e : 

        print("Manager Error:", e)

        return {}

async def create_pre_response(
    response : str , 
    history : list[dict[str , str]] , 
    slots : list , 
    user_id : str , 
    cannot_provide : dict , 
    user_input : str , 
    user_confirmation : bool , 
    redis_client , 
    hangup_status : bool
) -> dict : 

    history.extend(
        [
            {
                'role' : 'user' , 
                'content' : user_input
            } , 
            {
                'role' : 'assistant' , 
                'content' : response
            }
        ]
    )

    await set_user_data(
        user_id = user_id , 
        redis_client = redis_client , 
        data = {
            'history' : history , 
            'slots' : slots , 
            'cannot_provide_key' : cannot_provide , 
            'awaiting_form_confirmation' : user_confirmation
        }
    )

    return {
        'state' : {
            'history' : history 
        } , 
        'response' : {
            'response' : response , 
            'slots' : slots , 
            'hangup' : hangup_status
        }
    }

async def rephrase_query(
    history , 
    user_input , 
    prompt : str , 
    config : dict , 
    client : AsyncGroq , 
) -> str : 

    try : 
        
        response : str = await run_llm(
            messages = [
                {
                    'role' : 'system' , 
                    'content' : prompt
                } , 
                {
                    'role' : 'user' , 
                    'content' : f'''
                        Convertsation History : {history}

                        User Current Message : {user_input}
                    '''
                }
            ] , 
            provider = config['provider'] , 
            response_format = None , 
            temperature = config['temperature'] , 
            client = client , 
            model = config['model']
        )

        return response

    except Exception as e : 

        print("Rephraser Error:" , e)

        return user_input

async def search_vector_db(query : str , config : dict) -> str : 

    if not query : 
        return ''

    async with AsyncClient() as client:
        try:
            resp = await client.get(
                url = config['url'] , 
                params = {'query' : query} , 
                timeout = 2
            )

            if resp.status_code == 200 : 

                result = resp.json()

                return result

            return ''

        except Exception as e : 

            print('Vector DB Error:', e)

            return ''

async def check_for_pre_response(
    hangup_type : bool | str , 
    manager : dict , 
    user_data : dict , 
    user_input : str , 
    responses : dict , 
    language : str , 
    history : list[dict[str , str]] , 
    rephraser_prompt : str , 
    config : dict , 
    client : AsyncGroq
) -> tuple[bool , bool , str] :  

    pre_response = ''
    category = 'None'
    response_type = 'None'

    if hangup_type : 

        print('Recieved instruction to end the call')

        response_type = 'hangup'
        hangup = True

        if manager.get('has_gap_year' , False) : 
            category = 'gap_year'

        elif (
            manager.get("requesting_counselor_call", False) and 
            manager.get("hangup_reason") == "counselor_requested"
        ) : 

            print('Received counsellor end instruction')

            category = 'counsellor'

        elif (
            manager.get("non_admission_query", False) and 
            manager.get("hangup_reason") == "non_admission_intent"
        ) : 
            category = 'non_amdission'

        elif user_data['awaiting_form_confirmation'] : 

            user_response_lower = user_input.lower()
            
            if any(word in user_response_lower for word in [
                "yes", "yeah", 
                "filled", "submitted", "registered", 
                "हाँ", "हां", "हा", "भरा", "कर दिया"
            ]) : 
                category = 'course_change'

        else : 
            category = hangup_type

    else : 

        response_type = 'normal'
        hangup = False

        if manager.get('course_change_after_registeration' , False) : 
            category = 'course_change'
    if (
        category != 'None' and 
        response_type != 'None'
    ) : 

        pre_response : str = responses[response_type][category][language]

        print(f'Sending pre response as : {pre_response}')

    else : 

        vector_query = await rephrase_query(
            history , 
            user_input , 
            rephraser_prompt , 
            config['rephraser'] , 
            client = client
        )

        print(f'Vector Query : {vector_query}')

        is_hangup = "<hangup>" in vector_query.lower()

        if is_hangup:
            hangup = True
            pre_response = "Thank you for your time, Our counsellors will reach out to you soon!"

    if pre_response : 
        return True , hangup , pre_response

    else : 
        return False , hangup , vector_query