from contextlib import asynccontextmanager
import os
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from fastapi import WebSocket , Request , Response

from plivo.base import ResponseObject


from .services import retreive_form_data
from .loader import FastAPI, load_clients
from .session import SESSION

from dotenv import load_dotenv 
load_dotenv()


from .state import AppState 

from .services import env_str_to_bool , env_str_to_list

state : AppState = AppState()

@asynccontextmanager
async def lifespan(app : FastAPI) : 

    (
        config ,  
        logger ,  
        tts_client , 
        plivo_client , 
        connection_manager , 
        redis_client
    ) = load_clients()

    state.config = config 
    state.logger = logger
    state.tts_client = tts_client 
    state.plivo_client = plivo_client 
    state.connection_manager = connection_manager
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


@app.post('/answer' , tags = ['webhook'])
async def answer(request : Request)  : 

    call_details : tuple = await retreive_form_data(request)
    call_uuid : str = call_details[0]

    max_retries : int = 3
    retry_delay : float = 0.5

    if call_uuid : 

        for attempt in range(max_retries) : 

            try : 

                inbound_stream : ResponseObject = state.plivo_client.calls.start_stream(
                    call_uuid = call_uuid , 
                    service_url = state.config['pl']['connection']['inbound']['url'].format(call_uuid = call_uuid) , 
                    bidirectional = state.config['pl']['connection']['inbound']['bidirectional'] , 
                    audio_track = state.config['pl']['connection']['inbound']['audio-track'] , 
                    stream_timeout = state.config['pl']['connection']['inbound']['stream-timeout'] , 
                    content_type = state.config['pl']['connection']['inbound']['content-type']
                )

                recording_response = state.plivo_client.calls.record(
                    call_uuid = call_uuid , 
                    time_limit = 28_800 , 
                    file_format = 'wav' , 
                    # callback_url = 'https://insurance.voicexp.ai/v2/recordings'
                    callback_url = 'https://9888-01kesszt4bnsgk9x4ct4ra8cjf.cloudspaces.litng.ai/recordings'

                )

                await state.connection_manager.initialize_connection(
                    call_uuid = call_uuid , 
                    inbound_stream = inbound_stream
                )

                with open(state.config['pl']['connection']['global']['xml-path']) as xml_file : xml : str = xml_file.read().format(
                    stream_timeout = state.config['pl']['connection']['global']['stream-timeout'] , 
                    content_type = state.config['pl']['connection']['global']['content-type'] , 
                    status_cb_url = state.config['pl']['connection']['global']['status-cb-url'] , 
                    audio_ws_url = state.config['pl']['connection']['global']['audio-ws-url']
                )

                return Response(xml , media_type = state.config['pl']['connection']['global']['media-type'])

            except Exception as e:
                
                if attempt < max_retries - 1 : 

                    state.logger.warning(f'Call UUID {call_uuid} not found (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s... {e}')

                    await asyncio.sleep(retry_delay)

                    retry_delay *= 2  

                else : state.logger.error(f'Failed to start stream after {max_retries} attempts: {e}') ; raise

    else : raise ValueError(f'Call UUID was empty : {call_uuid}')

@app.post('/stream-events')
async def stream_events(request : Request) -> None : print(await request.form())

@app.post('/recordings')
async def recordings(request : Request) -> None : print(await request.form())

# Track TTS playback state
tts_active: bool = False
tts_checkpoint_names: set = set()

@app.websocket('/ws/{call_uuid}/inbound')
async def inbound(websocket : WebSocket , call_uuid : str) -> None : 

    session : SESSION = SESSION(
        workflow = 'jecrc' , 
        config = state.config['session'] , 
        tts_client = state.tts_client , 
        logger = state.logger , 
        websocket_object = websocket , 
        stream_id = await state.connection_manager.get_stream_id(call_uuid = call_uuid) , 
        connection_manager = state.connection_manager , 
        call_uuid = call_uuid , 
        redis_client = state.redis_client , 
        plivo_client = state.plivo_client
    )

    try : 

        await session.start()

        await asyncio.gather(*session.tasks , return_exceptions = True)

    except Exception as e : state.logger.error(f"Error in session {session.session_id}: {e}")
    finally : await session.disconnect()


@app.websocket('/ws')
async def websocket_endpoint(websocket : WebSocket) : 

    await websocket.accept()

    while True : _ = await websocket.receive()

def main() : uvicorn.run(
    'call.server:app' , 
    host = '0.0.0.0' ,  
    port = 9888 , 
    # workers = 2
)
