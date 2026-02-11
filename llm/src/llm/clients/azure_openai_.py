import os 

from openai import AzureOpenAI
from typing import Tuple

from .llm import LLM

class AZURE_OPENAI_LLM(LLM) : 
    '''
    A class to interact with Azure OpenAI's LLM service.

    This class extends the base LLM class and provides methods to run models, handle message history, and process responses.

    Attributes:
        - client (AzureOpenAI): The Azure OpenAI client for making API requests.
        - model (str): The name of the model to be used for inference.
        - dict_converter (str): The type of dictionary converter to be used for post-processing responses.
    
    Args:
        - env_path (str): Path to the environment file containing Azure OpenAI API credentials.
        - config (dict): Configuration dictionary containing Azure OpenAI settings, including model name and API version.

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

    def __init__(self , config : dict) : 

        super().__init__()

        self.config = config

        self.client : AzureOpenAI = AzureOpenAI(
            api_key = os.getenv('AZURE_OPENAI_API_KEY') ,   
            api_version = config['api-version'] , 
            azure_endpoint = config['endpoint']
        )

        self.model = config['model-name']
        self.dict_converter = config['preprocess']['dict-converter']

        print(f'Azure OpenAI LLM initialized with config : {config}')

    async def run_model(
        self , 
        messages : list , 
        model : str | None = None
    ) -> str :
        '''
        Run the specified model with the provided messages and return the response as a string.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, the default model is used.
        
        Returns:
            - str: The response from the model as a string.
        '''

        # print(f'Running model with messages: {messages} and model: {model if model else self.model}')
        
        chat_completion = self.client.chat.completions.create(
            messages = messages , 
            model = model if model else self.model
        )

        if chat_completion.choices[0].message.content : return chat_completion.choices[0].message.content
        else : print(f'No message from OpenAI sending empty responses') ; return ''

    async def run_model_json(
        self , 
        messages : list , 
        model : str | None = None , 
        dict_converter : str | None = None
    ) -> dict :
        '''
        Run the specified model with the provided messages and return the response as a JSON object.

        Args:
            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, the default model is used.
            - dict_converter (str | None): The type of dictionary converter to be used for post-processing the response. If None, the default converter is used.
        
        Returns:
            - dict: The response from the model as a JSON object.

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

            try : json_response : dict = await self.postprocess_response(
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
        Run the model with the provided query and history, updating the history with the response.

        Args:
            - query (str): The user query to be sent to the model.
            - history (list): A list of previous messages to maintain context.
            - model (str | None): The name of the model to be used. If None, the default model is used.

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

        response : str = await self.run_model(
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
        Run the model with the provided query and history, returning the response as a JSON object and updating the history.

        Args:
            - query (str): The user query to be sent to the model.
            - history (list): A list of previous messages to maintain context.
            - model (str | None): The name of the model to be used. If None, the default model is used.

        Returns : 
            - Tuple[dict, list]: A tuple containing the model's response as a JSON object and the updated history.

        Raises:
            - Exception: If there is an error processing the response.
        '''

        print(f'Running model with query: {query} and model: {model if model else self.model}')

        history.append(
            {
                'role' : 'user' , 
                'content' : query
            }
        )

        json_response : dict = await self.run_model_json(
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
    ) -> str : 
        '''
        Calls the run_model method with the provided messages and returns the response as a string.

        Args:

            - messages (list): A list of messages to be sent to the model.
            - model (str | None): The name of the model to be used. If None, the default model is used.

        Returns:
            - str: The response from the model as a string.
        '''

        # print(f'Calling model with messages: {messages} and model: {model if model else self.model}')
        
        response : str = await self.run_model(
            messages = messages , 
            model = model
        )

        print(f'Model response: {response}')

        return response