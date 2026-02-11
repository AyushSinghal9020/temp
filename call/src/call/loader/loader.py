from redis import Redis
import yaml

from logging import Logger
from fastapi import FastAPI
from plivo import RestClient
from ..connection import ConnectionManager

from typing import Tuple , Any

from .logging_ import load_logger
from .services import load_tts_client , load_llm_client , load_redis_client , load_plivo_client , load_connection_manager
from .api_ import load_fastapi_app

def load_clients() -> Tuple[
    dict , 
    Logger , 
    Any , 
    RestClient , 
    ConnectionManager , 
    Redis
    # FastAPI
] : 

    config = {
        "logger": {
            "colors": {
            "debug": "\u001b[33m",
            "info": "\u001b[34m",
            "warning": "\u001b[38;5;208m",
            "error": "\u001b[31m",
            "critical": "\u001b[31;1m",
            "reset": "\u001b[0m"
            },
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "date-time-format": "%Y-%m-%d %H:%M:%S"
        },
        "stt": {
            "service": "deepgram",
            "groq": {
            "model-name": "whisper-large-v3-turbo",
            "sample-rate": 16000,
            "sample-width": 2,
            "channels": 1
            },
            "deepgram": {
            "model-name": "nova-3",
            "language": "multi",
            "api-version": "1",
            "sample-rate": 16000,
            "sample-width": 2,
            "channels": 1
            }
        },
        "tts": {
            "service": "google",
            "google": {
            "language": "hi-IN",
            "name": "Aoede",
            "service-file-path": "./sts.json"
            },
            "smallestai": None,
            "murf": None
        },
        "llm": {
            "service": "groq",
            "groq": {
            "model-name": "llama-3.3-70b-versatile",
            "preprocess": {
                "dict-converter": "json"
            }
            }
        },
        "fast-api": {
            "host": "0.0.0.0",
            "port": 9888,
            "reload": False,
            "cors": {
            "allow-origins": [
                "*"
            ],
            "allow-methods": [
                "*"
            ],
            "allow-headers": [
                "*"
            ],
            "allow-credentials": True
            }
        },
        "pl": {
            "connection": {
            "inbound": {
                "url": "wss://9888-01kesszt4bnsgk9x4ct4ra8cjf.cloudspaces.litng.ai/ws/{call_uuid}/inbound",
                "bidirectional": True,
                "audio-track": "inbound",
                "stream-timeout": 3600,
                "content-type": "audio/x-l16;rate=16000"
            },
            "global": {
                "xml-path": "assets/plivo_/webhook_xml.xml",
                "stream-timeout": 3600,
                "content-type": "audio/x-l16",
                "status-cb-url": "https://insurance.voicexp.ai/stream-events",
                "audio-ws-url": "wss://insurance.voicexp.ai/ws",
                "media-type": "application/xml"
            }
            }
        },
        "session": {
            "agent-url": "http://localhost:9001/chat",
            "play-audio": {
            "event": "playAudio",
            "contentType": "audio/x-mulaw",
            "sampleRate": 8000
            },
            "clear-audio": {
            "event": "clearAudio"
            },
            "settings": {
            "min-buffer-len": 2000,
            "max-continous-interruption": 50,
            "barge-in": True
            }
        }
        }
    logger : Logger = load_logger(config = config['logger'])

    # stt_client : Any = load_stt_client(config['stt'])
    tts_client : Any = load_tts_client(config['tts'])
    # llm_client : Any = load_llm_client(config['llm'])

    plivo_client : RestClient = load_plivo_client()

    connection_manager : ConnectionManager = load_connection_manager(logger = logger)

    # app : FastAPI = load_fastapi_app(config['fast-api'])

    redis_client : Redis = load_redis_client()

    return (
        config , 
        logger , 
        tts_client , 
        # llm_client , 
        plivo_client , 
        connection_manager , 
        # app , 
        redis_client
    )