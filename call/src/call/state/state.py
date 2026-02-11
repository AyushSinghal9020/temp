from logging import Logger
from typing import Any

from redis import Redis
from plivo import RestClient
from ..connection import ConnectionManager

class AppState : 

    config : dict 
    logger : Logger

    tts_client : Any 

    plivo_client : RestClient

    connection_manager : ConnectionManager

    redis_client : Redis 