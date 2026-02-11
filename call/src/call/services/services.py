import json
import base64

import numpy as np 

from typing import Tuple
from numpy import ndarray
from asyncio import Queue
from fastapi import Request
from fastapi import WebSocket

from starlette.datastructures import FormData

async def process_hook(hook) -> str : 

    if hook['type'] == 'websocket.receive' : 

        dict_hook : dict = json.loads(hook['text'])

        if 'media' in dict_hook : 

            media_hook : dict = dict_hook['media']

            if 'payload' in media_hook : 

                base64array : str = media_hook['payload']

                return base64array

            else : print(f'Didnt received `payload` in `media hook` : {json.dumps(media_hook , indent = 4)}')
        else : print(f'Didnt Received `media` in `hook` : {json.dumps(dict_hook , indent = 4)}')
    else : print(f'Didnt received `receive` type websocket : {hook}')

    return ''




async def audio_receiver(
    websocket : WebSocket , 
    audio_queue : Queue
) -> None : 

    while True : 

        hook = await websocket.receive()
        print(hook)
        base64array : str = await process_hook(hook)

        if base64array != '' : await audio_queue.put(base64array)

async def retreive_form_data(request : Request) -> Tuple[str] : 

    form_data : FormData = await request.form()

    form_json : dict = {}
    for key , value in zip(form_data.keys() , form_data.values()) : form_json[key] = value

    # bill_rate : str  = form_json.get('BillRate' , '0.0')
    # call_status : str = form_json.get('CallStatus' , 'ringing')
    call_uuid : str = form_json.get('CallUUID' , '')
    # caller_number : str = form_json.get('CallerName' , '+910000000000')
    # country_code : str = form_json.get('CountryCode' , 'IN')
    # direction : str = form_json.get('Direction' , 'inbound')
    # event : str = form_json.get('Event' , 'StartApp')
    # from_number : str = form_json.get('From' , '+910000000000')
    # parent_auth_id : str = form_json.get('ParentAuthID' , '')
    # route_type : str = form_json.get('RouteType' , 'Domestic_Anchored')
    # stir_attestation : str = form_json.get('STIRAttestation' , 'Not Applicable')
    # stir_verification : str = form_json.get('STIRVerification' , 'Not Applicable')
    # session_start : str = form_json.get('SessionStart' , '2025-08-08 07:11:01.594638')
    # to_number : str = form_json.get('To' , '+910000000000')

    return (
        # bill_rate , call_status , 
        call_uuid , 
        # caller_number , 
        # direction , 
        # event , 
        # from_number , 
        # parent_auth_id , 
        # route_type , 
        # stir_attestation , 
        # stir_verification , 
        # session_start , 
        # to_number
    )

def _parse_list(value : str) -> list : 

    if value == '*' : return ['*']

    return [x.strip() for x in value.split(',')]

def _parse_bool(value : str) -> bool : return value.lower() == 'true'

def env_str_to_list(
    value : str ,  
    default : str = '*'
) -> list : 

    if not value : value = default
    return _parse_list(value)

def env_str_to_bool(
    value : str , 
    default : str = 'True'
) -> bool : 

    if not value : value = default
    return _parse_bool(value)
