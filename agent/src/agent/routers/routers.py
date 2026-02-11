from datetime import datetime
import traceback
from redis.client import Redis
import json
from ..helpers import set_redis
import pytz

# from llm.src.llm import GROQ_LLM
from llm import GROQ_LLM


async def update_user_context_background(
    user_id : str , 
    prompt : str , 
    llm_client : GROQ_LLM , 
    old_summary : dict , 
    new_q : str , 
    new_a : str , 
    search_query : str , 
    context : list , 
    redis_client : Redis , 
    state : dict , 
    history : list
) -> None : 

    key = f"session:{user_id}"

    try : 

        response : dict = llm_client.run_model_json(
            messages = [
                {
                    'role' : 'system' , 
                    'content' : prompt.replace(
                        '{old_summary}' , str(old_summary)
                    ).replace(
                        '{new_q}' , str(new_q)
                    ).replace(
                        '{new_a}' , str(new_a)
                    ).replace(
                        '{search_q}' , str(search_query)
                    ).replace(
                        '{safe_context}' , str(context)
                    ).replace(
                        '{state}' , str(state)
                    )
                } , 
                {
                    'role' : 'user' , 
                    'content' : 'Return the json'
                }
            ]
        )

        await set_redis(
            key = key , 
            value = {
                'summary' : str(response.get('summary' , 'No Summary was able to generate, revert to own history')) , 
                'state' : str(response) , 
                'history' : json.dumps(history) , 
                'updated_at' : datetime.now(pytz.timezone('Asia/Kolkata')).isoformat()
            } , 
            redis_client = redis_client
        )

        redis_client.expire(key , 3600)

    except Exception as e : 
        print(f"[Error] Redis update failed: {e} , {traceback.format_exc()}")

async def rephrase_query(
    raw_query : str , 
    history_summary : dict , 
    prompt : str , 
    user_state : dict , 
    llm_client : GROQ_LLM
) -> list[str] : 

    try : 

        response : dict = llm_client.run_model_json(
            messages = [
                {
                    'role' : 'system' , 
                    'content' : prompt
                } , 
                {
                    'role' : 'user' , 
                    'content' : f"Context Summary: {history_summary}\nUser Input: {raw_query}\n User State : {user_state}"
                }
            ] , 
            model = 'openai/gpt-oss-20b'
        )

        rephrased_query : list = response['llm_response']

        return rephrased_query

    except : 
        return [raw_query]

async def process_query_with_state(
    query : str , 
    context : list , 
    user_state : dict , 
    summary : str , 
    llm_client : GROQ_LLM , 
    state_prompt : str 
) -> str : 

    response : dict = llm_client.run_model_json(
        messages = [
            {
                'role' : 'system' , 
                'content' : state_prompt
            } , 
            {
                'role' : 'user' , 
                'content' : f'''
                Original User Query : {query}
                History : {summary}
                Retreived Info : {str(context)}
                User State : {user_state}
                '''
            }
        ] , 
        model = 'openai/gpt-oss-20b'
    )

    try : 

        indexes : list[int] = response['indexes']
        print(indexes)

        new_context = ''

        for index in indexes : 

            new_context += context[index]['context'] + '\n' + context[index]['text']
        return new_context

    except Exception as e : 
        print(e , traceback.format_exc())

        return str([row['context'] + row['text'] for row in context])
