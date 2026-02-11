from httpx import AsyncClient
from redis.client import Redis

async def get_redis(user_id : str , redis_client : Redis) -> dict : 

    key = f"session:{user_id}"

    data : dict = redis_client.hgetall(key)  # Gets all fields

    # print(f'Retreived Data ---> : {data}')

    if not data : 
        return {"summary": "No prior conversation."}

    return {
        key.decode() if isinstance(key , bytes) else key :  
        value.decode() if isinstance(value , bytes) else value 
        for key , value in data.items()
    }

async def set_redis(key : str , value : dict , redis_client : Redis) -> None : 

    # print(f'Setting History as {value}')
    redis_client.hset(key , mapping = value)

async def fetch_vector_context(query : str , config : dict , http_client : AsyncClient) -> str : 

    try : 

        response = await http_client.get(
            config['vector-db-url'] , 
            params = {
                "query" : query , 
                # 'collection-name' : 'jecrc_dev'
                "top_k" : 3
            } , 
            timeout = config['timeout']
        )

        response.raise_for_status()

        data = response.json()

        # print(data)

        if 'results' not in data : 
            return 'No Context retreived'

        results = data['results']

        context = ''

        for result in results : 
            context += f'{result["context"]}\n{result["text"]}\n\n\n'
                    
        return context

    except Exception as e : 

        print(f'[Vector API Error] {e}')

        return 'No Context Retreived'
