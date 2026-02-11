import yaml
import os 

from fastapi import FastAPI
from transformers import pipeline

from typing import Tuple , Any
from redis.asyncio import Redis

from logging import (
    Logger , getLogger , 
    StreamHandler , Formatter , 
    DEBUG , INFO , WARNING , ERROR , CRITICAL , 
    LogRecord
)


import ssl

from fastapi.middleware.cors import CORSMiddleware

# from stt.src.stt import DEEPGRAM_STT , ASSEMBLYAI_STT
from stt import DEEPGRAM_STT , ASSEMBLYAI_STT

from llm import GROQ_LLM
# from llm.src.llm import GROQ_LLM

class ColoredFormatter(Formatter) : 

    def __init__(
        self , 
        fmt : str , 
        config : dict , 
        datefmt : str | None = None
    ) -> None :

        super().__init__(fmt , datefmt)
        
        self.COLORS = {
            DEBUG : config['color']['debug'] ,
            INFO : config['color']['info'] , 
            WARNING : config['color']['warning'] , 
            ERROR : config['color']['error'] , 
            CRITICAL : config['color']['critical']
        }

        self.RESET = config['color']['reset']

        self.fmt = fmt

    def format(self , record : LogRecord) -> str : 

        color = self.COLORS.get(record.levelno)

        if color : log_fmt = color + self.fmt + self.RESET
        else : log_fmt = self.fmt

        formatter = Formatter(log_fmt , self.datefmt)

        return formatter.format(record)

def load_logger(config : dict) -> Logger:
    
    logger: Logger = getLogger(__name__)
    logger.setLevel(DEBUG) 

    if logger.handlers : 

        for handler in logger.handlers : logger.removeHandler(handler)

    console_handler = StreamHandler()

    log_format = config['log-format']

    formatter = ColoredFormatter(
        fmt = log_format , 
        config = config , 
        datefmt = ''
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger

def load_stt_client(config : dict) -> DEEPGRAM_STT | ASSEMBLYAI_STT : 

    # deepgram_client : DEEPGRAM_STT = DEEPGRAM_STT(config = config['deepgram'])
    stt_client = ASSEMBLYAI_STT(config = config['assembly-ai'])

    return stt_client

def load_llm_client(config : dict) : 

    groq_client : GROQ_LLM = GROQ_LLM(config = config['groq'])

    return groq_client 

def load_config() -> dict : # ! load config here from yml
    
    config : dict = {
        "nestjs": {
            "url": "https://52894b7997ab.ngrok-free.app",
            "single-send-analysis-result-endpoint": "webhook/analysis-result",
            "bulk-send-analysis-result-endpoint": "webhook/analysis-results-bulk",
            "max-retries": 3 , 
            "retry-delay" : 2
        },
        "nestjsurl": "https://52894b7997ab.ngrok-free.app",
        "batch-size": 10,
        "max-retries": 3,
        "retry-delay": 2,
        "stt": {
            "deepgram": {
                "model-name" : "nova-3",
                "language" : "multi" , 
                "api-version" : "1" , 
                "sample-rate": 16000,
                "sample-width": 2,
                "channels": 1,
                "smart-format": True,
                "punctuate": True,
                "diarize": True
                } , 
            'assembly-ai' : {}
        },
        "llm" : {
            "groq" : {
                "model-name" : "llama-3.3-70b-versatile" , 
                "preprocess" : {
                    "dict-converter" : "ast"
                }
            }
        },
        "logger": {
            "color": {
            "debug": "\\x1b[33m",
            "info": "\\x1b[34m",
            "warning": "\\x1b[38;5;208m",
            "error": "\\x1b[31m",
            "critical": "\\x1b[31;1m",
            "reset": "\\x1b[0m"
            },
            "log-format": "%(asctime)s - %(levelname)s - %(message)s",
            "date-format": "%Y-%m-%d %H:%M:%S"
        },
        "sentiment-analysis": {
            "task": "sentiment-analysis",
            "model-name": "distilbert-base-uncased-finetuned-sst-2-english"
        }
    }

    return config 

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

def load_fastapi(config : dict) -> FastAPI :  

    app : FastAPI = FastAPI()
    app.add_middleware(
        CORSMiddleware , 
        allow_origins = config['cors']['allowed-origins'] , 
        allow_credentials = config['cors']['allowed-credentials'] , 
        allow_methods = config['cors']['allowed-methods'] , 
        allow_headers = config['cors']['allowed-headers'] , 
    )

    return app

def load_all_clients() -> Tuple[
    dict , 
    Logger , 
    GROQ_LLM , 
    DEEPGRAM_STT | ASSEMBLYAI_STT , 
    # FastAPI , 
    Redis 
]: 
    
    config : dict = load_config()

    logger : Logger = load_logger(config['logger'])

    groq_client : GROQ_LLM = load_llm_client(config = config['llm'])
    stt_client : DEEPGRAM_STT | ASSEMBLYAI_STT = load_stt_client(config = config['stt'])

    redis_client : Redis = load_redis_client()

    # app : FastAPI = load_fastapi(config['fast-api'])
    
    return (
        config , 
        logger , 
        groq_client , 
        stt_client , 
        # app , 
        redis_client 
    )