from contextlib import asynccontextmanager
import json
import os
import time
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from dotenv import load_dotenv

from fastapi import FastAPI, Request

from fastapi.responses import JSONResponse

from .scripts import load_all_clients

from .scripts import process_audio_pipeline_url

load_dotenv()

from .services import env_str_to_bool , env_str_to_list

from .state import AppState 

state = AppState()

@asynccontextmanager
async def lifespan(app : FastAPI) : 

    (
        config , 
        logger , 
        llm_client , 
        stt_client , 
        redis_client 
    ) = load_all_clients()

    state.config = config 
    state.logger = logger
    state.llm_client = llm_client
    state.stt_client = stt_client
    state.redis_client = redis_client 

    yield

app : FastAPI = FastAPI(lifespan = lifespan)

app.add_middleware(
    CORSMiddleware , 
    allow_origins = env_str_to_list(os.environ['ALLOWED_ORIGINS']) , 
    allow_credentials = env_str_to_bool(os.environ['ALLOWED_CREDENTIALS']) , 
    allow_methods = env_str_to_list(os.environ['ALLOWED_METHODS']) , 
    allow_headers = env_str_to_list(os.environ['ALLOWED_HEADERS']) 
)

@app.get('/health')
async def health_check() : return {'status' : 'ok'}


@app.post('/get-metadata-audio-url')
async def get_metadata_audio_url(request : Request):

    data = await request.json()

    audio_url : str = data['recordingUrl']
    recording_id : str = data['recordingId']
    call_uuid : str = data['callUuid']

    start_time : float = time.time()
    
    results : dict = await process_audio_pipeline_url(
        stt_client = state.stt_client , 
        llm_client = state.llm_client , 
        url = audio_url , 
        logger = state.logger , 
        redis_client = state.redis_client , 
        call_uuid = call_uuid
    )


    state.logger.info(f'Total time for url : {audio_url} : {time.time() - start_time}')
    #print(json.dumps(results , indent = 4))

    response = {
        'success' : results['status'] ,
        'transcriptions' : results['transcriptions'] ,
        'summary' : results['summary'] ,
        'sentiment' : results['sentiment'] , 
        'tags' : results['tags'] , 
        'student_details' : [results['student_details']] , 
        'callUuid' : call_uuid , 
        'recordingId' : recording_id
    }

    state.logger.info('Direct processing completed successfully')

    return JSONResponse(content = response)

def main() : uvicorn.run(
    app , 
    host = '0.0.0.0' , 
    port = 9002 , 
)
