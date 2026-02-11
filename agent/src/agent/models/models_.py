from pydantic import BaseModel

class ChatRequest(BaseModel) : 

    user_id : str
    query_text : str

class ChatResponse(BaseModel) : 

    response_text : str
    latency_ms : float
    rephrased_query : str
