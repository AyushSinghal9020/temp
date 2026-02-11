from typing import Any
from redis import Redis
from httpx import AsyncClient

class AppState : 

    llm_client : Any
    config : dict 
    redis_client : Redis
    http_client : AsyncClient

    rephrase_prompt : str
    update_prompt : str
    system_prompt : str
    state_prompt : str 