import ast 
import json

import requests 

class LLM : 
    '''
    Base class for Language Model (LLM) services.

    This class provides methods to create messages for LLM requests and to post-process responses
    from the LLM. It is designed to be extended by specific LLM implementations such as Azure OpenAI or Groq.

    Methods:
        - create_messages(system_prompt: str, user_input: str) -> list[dict[str, str]]:
            Creates a list of messages formatted for LLM requests, including system and user prompts.
        - postprocess_response(response: str, dict_converter: str) -> dict:
            Post-processes the LLM response based on the specified dictionary converter type.
        - postprocess_response_ast(response: str) -> dict:
            Post-processes the LLM response using the AST literal evaluation method.
        - postprocess_response_json(response: str) -> dict:
            Post-processes the LLM response using the JSON parsing method.
    
    Attributes: 
        - None

    Args : 
        - None
    '''

    def __init__(self) : 

        pass

    async def create_messages(
        self , 
        system_prompt : str , 
        user_input : str
    ) -> list[dict[str , str]] : 
        '''
        Create messages for LLM requests.

        Args:
            - system_prompt (str): The system prompt to be included in the messages.
            - user_input (str): The user input to be included in the messages.

        Returns:
            - list[dict[str, str]]: A list of messages formatted for LLM requests.
        '''

        messages : list[dict[str , str]] = [
            {
                'role' : 'system' , 
                'content' : system_prompt
            } , 
            {
                'role' : 'user' , 
                'content' : user_input
            }
        ]

        return messages

    def postprocess_response(self , response : str , dict_converter : str) -> dict :
        '''
        Post-process the LLM response based on the specified dictionary converter type.

        Args:

            - response (str): The raw response from the LLM.
            - dict_converter (str): The type of dictionary converter to use ('ast' or 'json').

        Returns:
            - dict: The processed response as a dictionary.

        Raises:
            - ValueError: If an unsupported dict_converter is provided.
        '''

        if dict_converter == 'ast' : return self.postprocess_response_ast(response)

        elif dict_converter == 'json' : return self.postprocess_response_json(response)

        else : 

            raise ValueError(f"Unsupported dict_converter: {dict_converter}")

    def postprocess_response_ast(self , response : str) -> dict : 
        '''
        Post-process the LLM response using the AST literal evaluation method.

        Args:
            - response (str): The raw response from the LLM.

        Returns:
            - dict: The processed response as a dictionary.
        '''

        processed_response : str = response.replace('json' , '').replace('`' , '')

        json_response : dict = ast.literal_eval(processed_response)

        return json_response

    def postprocess_response_json(self , response : str) -> dict : 
        '''
        Post-process the LLM response using the JSON parsing method.

        Args:
            - response (str): The raw response from the LLM.

        Returns:
            - dict: The processed response as a dictionary.
        '''

        processed_response : str = response.replace('json' , '').replace('`' , '')

        json_response : dict = json.loads(processed_response)

        return json_response

    def execute_search(self , query : str) -> str : 

        try : 

            payload = {'query' : query , 'top_k' : 5}

            response = requests.post(
                'http://localhost:8001/search' , 
                json = payload , 
                headers = {'Content-Type' : 'application/json'} , 
                timeout = 10
            )

            response.raise_for_status()

            data = response.json()
            results = data.get('results' , [])

            if not results : 
                return 'No relevant documents found in the database.'

            context = ''
            for item in results : 
                context += f'{item["text"]}\n'

            return context.strip()

        except Exception as e : 
            print(e)
            return 'No relevant documents found in the database.'
