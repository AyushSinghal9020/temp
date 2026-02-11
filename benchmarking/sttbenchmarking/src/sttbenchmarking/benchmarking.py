import os
import json
import pandas as pd
from jiwer import wer
import yaml
import asyncio
import time
from dotenv import load_dotenv
from stt import GROQ_STT , GOOGLE_STT , DEEPGRAM_STT
from tqdm import tqdm

with open('config.yml') as config_file : config : dict = yaml.safe_load(config_file)

load_dotenv(config['env-path'])

client_dict = { # Do not put the same key as in the json file, if doing any chnages in how the client responds, for example changing langugae for groq, create a new key representing, maybe like groq-lang-en
    # 'groq-1' : GROQ_STT(config = config['stt']['groq']) , 
    'deepgram' : DEEPGRAM_STT(config = config['stt']['deepgram'])
    # 'google' : GOOGLE_STT(config = config['stt']['google'])
}

if os.path.exists(config['benchmark-json-path']) : 

    with open(config['benchmark-json-path']) as json_file : bench = json.load(json_file)

    for key in client_dict : 

        if key in bench : raise RuntimeError(f'{key} benchmark already available')
else : bench = {}

df = pd.read_csv(config['csv-file-path'])

async def run_benchmarks() : 

    for _ , row in tqdm(
        df.iterrows() , 
        total = df.shape[0] , 
        leave = False , 
        desc = 'Calculating Time to Transcribe'
    ) : 

        filename = row['filename']
        root_text = row['text']
        language = row['language']
        audio_duration_group = row['audio_duration_group']

        file_path : str = f'{config["audio-dir"]}/{filename}'

        with open(file_path , 'rb') as audio_file : audio_bytes : bytes = audio_file.read()

        for client in tqdm(
            client_dict , 
            total = len(client_dict) , 
            leave = False
        ) : 

            for client in tqdm(
                client_dict , 
                total = len(client_dict) , 
                leave = False
            ) : 

                start_time = time.time()

                transcription , _ = await client_dict[client](buffer_stream = audio_bytes)

                latency : float = time.time() - start_time
                error_rate : float = wer(root_text , transcription)

                if client not in bench : bench[client] = {
                    'latency' : {
                        'average' : 0 , 
                        'groups' : {}
                    } , 
                    'wer' : {
                        'average' : 0 , 
                        'groups' : {}
                    }
                }

                if language not in bench[client]['wer']['groups'] : bench[client]['wer']['groups'][language] = {
                    'average' : 0 , 
                    'all' : [error_rate]
                }
                else : bench[client]['wer']['groups'][language]['all'].append(error_rate)

                if audio_duration_group not in bench[client]['latency']['groups'] : bench[client]['latency']['groups'][audio_duration_group] = {
                    'average' : 0 , 
                    'all' : [latency]
                }
                else : bench[client]['latency']['groups'][audio_duration_group]['all'].append(latency)

    with open(config['benchmark-json-path'] , 'w') as json_file : json.dump(bench , json_file)

def main() : 

    asyncio.run(run_benchmarks())