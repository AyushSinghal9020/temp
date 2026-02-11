from llm import GROQ_LLM , AZURE_OPENAI_LLM
import time 
import os 
import json
from tqdm import tqdm
import asyncio
from dotenv import load_dotenv
import yaml


with open('config.yml') as config_file : config : dict = yaml.safe_load(config_file)
load_dotenv(config['env-path'])

client_dict = {
    'groq-openai/gpt-oss-20b' : GROQ_LLM(config = config['llm']['groq']) , 
    # 'azure-openai' : AZURE_OPENAI_LLM(config = config['llm']['azure-openai'])
}

if os.path.exists(config['benchmark-json-path']) : 

    with open(config['benchmark-json-path']) as json_file : bench = json.load(json_file)

    for key in client_dict : 

        if key in bench : raise RuntimeError(f'{key} benchmark already available')
else : bench = {}
async def run_llm() : 

    with open(config['input-file']) as input_file : texts : list = input_file.read().splitlines()

    for text in tqdm(
        texts , 
        total = len(texts) , 
        leave = False
    ) : 

        for client in tqdm(
            client_dict , 
            total = len(client_dict) , 
            leave = False
        ) : 

            start_time = time.time()

            _ : str = await client_dict[client](
                [
                    {
                        'role' : 'user' , 
                        'content' : text
                    }
                ]
            )

            latency = time.time() - start_time

            if client not in bench : bench[client] = {
                'latency' : []
            }

            bench[client]['latency'].append(latency)

    with open(config['benchmark-json-path'] , 'w') as json_file : json.dump(bench , json_file)

def main() : 

    asyncio.run(run_llm())