import os 

from dotenv import load_dotenv
from redis import Redis
from plivo import RestClient
from logging import Logger

from ..connection import ConnectionManager

from tts import (
    GOOGLE_TTS
)

from llm import GROQ_LLM

def load_redis_client() -> Redis : 

    redis_client = Redis(
        host=os.environ['REDIS_HOST'],
        port=15410,
        decode_responses=True,
        username="default",
        password=os.environ['REDIS_PASSWORD'], 
        ssl=False,
        ssl_cert_reqs=None
    )

    return redis_client

def load_tts_client(config : dict) : 

    if config['service'] == 'murf' : tts_client = MURF_TTS(config = config['murf'])
    if config['service'] == 'google' : tts_client = GOOGLE_TTS(config = config['google'])
    if config['service'] == 'smallestai' : tts_client = SMALLESTAI_TTS(config = config['smallestai'])

    return tts_client

def load_llm_client(config : dict) : 

    if config['service'] == 'groq' : llm_client = GROQ_LLM(config = config['groq'])

    return llm_client

def load_plivo_client() -> RestClient : 

    client : RestClient = RestClient(
        auth_id = os.getenv('PLIVO_AUTH_ID') , 
        auth_token = os.getenv('PLIVO_AUTH_TOKEN')
    )

    return client 

def load_connection_manager(logger : Logger) -> ConnectionManager : 
    
    connection_manger : ConnectionManager = ConnectionManager(logger = logger)

    return connection_manger