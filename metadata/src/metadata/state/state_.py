from logging import Logger
from typing import Any

from redis import Redis

class AppState : 

    config : dict 
    logger : Logger
    llm_client : Any
    stt_client : Any
    redis_client : Redis