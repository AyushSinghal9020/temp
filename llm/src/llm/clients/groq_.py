import json
import os 

from groq import Groq 
from typing import Tuple

from .llm import LLM

class GROQ_LLM(LLM) : 
    '''
    A class to interact with Groq's LLM service.

    This class extends the base LLM class and provides methods to run models, handle message history, and process responses.

    Attributes:
        - client (Groq): The Groq client for making API requests.
        - model (str): The name of the model to be used for inference.
        - dict_converter (str): The type of dictionary converter to be used for post-processing responses.

    Args:
        - env_path (str): Path to the environment file containing Groq API credentials.
        - config (dict): Configuration dictionary containing Groq settings, including model name.
    
    Methods:
        - run_model(messages: list, model: str | None = None) -> str:
            Runs the specified model with the provided messages and returns the response as a string.
        - run_model_json(messages: list, model: str | None = None, dict_converter: str | None = None) -> dict:
            Runs the specified model with the provided messages and returns the response as a JSON object.
        - run_model_history(query: str, history: list, model: str | None = None) -> Tuple[str, list]:
            Runs the model with the provided query and history, updating the history with the response.
        - run_model_history_json(query: str, history: list, model: str | None = None) -> Tuple[dict, list]:
            Runs the model with the provided query and history, returning the response as a JSON object and updating the history.
        - __call__(messages: list, model: str | None = None) -> str:
            Calls the run_model method with the provided messages and returns the response as a string.
    '''

    def __init__(self , config : dict) -> None : 

        super().__init__()

        self.config = config

        self.client : Groq = Groq(api_key = os.getenv('GROQ_API_KEY'))

        self.model = config['model-name']
        self.dict_converter = config['preprocess']['dict-converter']


        print(f'Groq LLM initialized with config : {config}')

    async def run_model_async(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str :
        '''
        Runs the specified model with the provided messages and returns the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - str: The content of the model's response.
        
        Raises:
            - Exception: If there is an error in processing the response.
        '''
        
        # print(f'Running model with messages: {messages} and model: {model if model else self.model}')
        
        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model
        )

        if chat_completion.choices[0].message.content : return chat_completion.choices[0].message.content
        else : print(f'No message from OpenAI sending empty responses') ; return ''

    def run_model(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str :
        '''
        Runs the specified model with the provided messages and returns the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - str: The content of the model's response.
        
        Raises:
            - Exception: If there is an error in processing the response.
        '''
        
        # print(f'Running model with messages: {messages} and model: {model if model else self.model}')
        
        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model
        )

        if chat_completion.choices[0].message.content : return chat_completion.choices[0].message.content
        else : print(f'No message from OpenAI sending empty responses') ; return ''


    async def run_model_json_async(
        self , 
        messages : list , 
        model : str | None = None , 
        dict_converter : str | None = None
    ) -> dict :
        '''
        Runs the specified model with the provided messages and returns the response as a JSON object.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.
            - dict_converter (str | None): The type of dictionary converter to be used for post-processing. If None, uses the default converter.

        Returns:
            - dict: The processed response from the model as a JSON object.

        Raises:
            - Exception: If there is an error processing the response.
        '''


        # print(f'Running model with messages: {messages} and model: {model if model else self.model}')

        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model , 
            response_format = {'type' : 'json_object'}
        )

        if chat_completion.choices[0].message.content : 

            try : json_response : dict = self.postprocess_response(
                chat_completion.choices[0].message.content , 
                dict_converter = dict_converter if dict_converter else self.dict_converter
            )
            except Exception as e : print(f'Invalid JSON found {chat_completion.choices[0].message.content} , sending empty json') ; json_response = {}

        else : print(f'No message receieved from OpenAI, sending empty json') ; json_response = {}

        return json_response

    def run_model_json(
        self , 
        messages : list , 
        model : str | None = None , 
        dict_converter : str | None = None
    ) -> dict :
        '''
        Runs the specified model with the provided messages and returns the response as a JSON object.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.
            - dict_converter (str | None): The type of dictionary converter to be used for post-processing. If None, uses the default converter.

        Returns:
            - dict: The processed response from the model as a JSON object.

        Raises:
            - Exception: If there is an error processing the response.
        '''


        # print(f'Running model with messages: {messages} and model: {model if model else self.model}')

        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model , 
            response_format = {'type' : 'json_object'}
        )

        if chat_completion.choices[0].message.content : 

            try : json_response : dict = self.postprocess_response(
                chat_completion.choices[0].message.content , 
                dict_converter = dict_converter if dict_converter else self.dict_converter
            )
            except Exception as e : print(f'Invalid JSON found {chat_completion.choices[0].message.content} , sending empty json') ; json_response = {}

        else : print(f'No message receieved from OpenAI, sending empty json') ; json_response = {}

        return json_response

    async def run_model_history(
        self , 
        query : str , 
        history : list , 
        model : str | None = None
    ) -> Tuple[str , list] : 
        '''
        Runs the model with the provided query and history, updating the history with the response.

        Args:

            - query (str): The user query to be sent to the model.
            - history (list): A list of previous messages in the conversation history.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - Tuple[str, list]: A tuple containing the model's response as a string and the updated history.
        '''

        print(f'Running model with query: {query} and model: {model if model else self.model}')

        history.append(
            {
                'role' : 'user' , 
                'content' : query
            }
        )

        response : str = await self.run_model_async(
            messages = history , 
            model = model
        )

        print(f'Model response: {response}')

        history.append(
            {
                'role' : 'assistant' , 
                'content' : response
            }
        )

        return response , history

    async def run_model_json_history(
        self , 
        query : str , 
        history : list , 
        model : str | None = None
    ) -> Tuple[dict , list] : 
        '''
        Runs the model with the provided query and history, returning the response as a JSON object and updating the history.

        Args:
            - query (str): The user query to be sent to the model.
            - history (list): A list of previous messages in the conversation history.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - Tuple[dict, list]: A tuple containing the model's response as a JSON object and the updated history.
        '''

        print(f'Running model with query: {query} and model: {model if model else self.model}')

        history.append(
            {
                'role' : 'user' , 
                'content' : query
            }
        )

        json_response : dict = await self.run_model_json_async(
            messages = history , 
            model = model
        )

        print(f'Model JSON response: {json_response}')

        history.append(
            {
                'role' : 'assistant' , 
                'content' : str(json_response)
            }
        )

        return json_response , history

    async def __call__(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str:

        '''
        Calls the run_model method with the provided messages and returns the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.

        Returns:
            - str: The content of the model's response.
        '''

        print(f'Calling model with messages: {messages} and model: {model if model else self.model}')
        
        response : str = await self.run_model_async(
            messages = messages , 
            model = model
        )

        print(f'Model response: {response}')

        return response

    def run_model_tool(
        self , 
        messages : list , 
        query : str , 
        tools : list , 
        model : str | None = None , 
        dict_converter : str | None = None , 
        temperature : float = 0.2
    ) -> dict :
        '''
        Runs the specified model with the provided messages and returns the response as a JSON object.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, uses the default model.
            - dict_converter (str | None): The type of dictionary converter to be used for post-processing. If None, uses the default converter.

        Returns:
            - dict: The processed response from the model as a JSON object.

        Raises:
            - Exception: If there is an error processing the response.
        '''


        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            tools = tools , 
            tool_choice = 'required' , 
            temperature = temperature , 
            model = model if model else self.model
        )

        assistant_msg = chat_completion.choices[0].message

        if assistant_msg.tool_calls : 

            messages.append({
                'role' : 'assistant' , 
                'tool_calls' : [
                    {
                        'id' : tc.id , 
                        'type' : 'function' , 
                        'function' : {
                            'name' : tc.function.name , 
                            'arguments' : tc.function.arguments
                        }
                    }
                    for tc in assistant_msg.tool_calls
                ]
            })

            for tc in assistant_msg.tool_calls : 

                args = json.loads(tc.function.arguments)
                search_query = args.get("search_query" , query)
                context = self.execute_search(search_query)

                messages.append({
                    "role" : "tool" ,
                    "tool_call_id" : tc.id , 
                    "name" : "search_documents" , 
                    "content" : context
                })

                # print(json.dumps(messages , indent = 4))

            response : dict = self.run_model_json(messages)

        return response
