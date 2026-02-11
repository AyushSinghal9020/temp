from math import e
from uuid import uuid4
import yaml 
import json 
from tqdm import tqdm
import requests
from requests import Response

from llm import GROQ_LLM
# from llm.src.llm import GROQ_LLM

from dotenv import load_dotenv

load_dotenv('../../.env')

def run_test(config : dict) : 

    llm_client : GROQ_LLM = GROQ_LLM(config['groq'])

    results = []

    with open(config['cases']) as cases_file : 
        cases : list = json.load(cases_file)

    if config['test-limit'] != 'no-limit' : 
        cases = cases[: config['test-limit']]

    with open(config['final_verdict_prompt']) as final_verdict_file :
        final_verdict_prompt : str = final_verdict_file.read()

    for case in tqdm(cases , desc = 'Running conversation') : 

        user_id : str = str(uuid4())

        result = {'conversation' : [] , 'final_verdict' : {} , 'tags' : []}

        conversations : list = []

        for conversation in tqdm(case['conversation'] , total = len(case['conversation']) , leave = False) : 

            response : Response = requests.post(
                url = config['test-url'] , 
                json = {
                    'query_text' : conversation['question'] , 
                    'user_id' : user_id
                }
            )

            # print(response.json())

            if response.status_code == 200 : 
                if 'response_text' in response.json() : 

                    answer : str = response.json()['response_text'] 
                    time : float = response.json()['latency_ms']

                else :

                    answer = 'Incorrect API Hit' 
                    time = 0

            else : 

                answer = 'Incorrect API Hit' 
                time = 0

            similarity : float = 1 # ! Write function here 

            conversations.append({
                'question' : conversation['question'] , 
                'answer' : answer
            })

            result['conversation'].append({
                'question' : conversation['question'] , 
                'expected' : conversation['expected'] , 
                'time' : time , 
                'received' : answer , 
                'similarity' : similarity
            })

        result['tags'] = case['tags']

        

        final_verdict : dict = llm_client.run_model_json([
            {
                'role' : 'system' , 
                'content' : final_verdict_prompt
            } , 
            {
                'role' : 'user' , 
                'content' : f'COnversation : {str(conversations)}'
            }
        ]
        )

        result['final_verdict'] = final_verdict

        results.append(result)

    with open('assets/tresults.json' , 'w') as json_file : 
        json.dump(results , json_file)

def main() : 

    with open('config.yml') as config_file : 
        config : dict = yaml.safe_load(config_file)

    run_test(config)