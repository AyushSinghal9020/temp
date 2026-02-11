from logging import Logger 
import os


from deepgram import DeepgramClient
from asyncio import Queue
from plivo.base import ResponseObject


class ConnectionManager : 

    def __init__(self , logger : Logger) -> None : 
        
        self.active_connections : dict = {}
        self.logger : Logger = logger

        self.deepgram_client = DeepgramClient(api_key = os.environ['DEEPGRAM_API_KEY'])


    async def initialize_connection(
        self , 
        call_uuid : str , 
        inbound_stream : ResponseObject
    ) -> None : 


        self.active_connections[call_uuid] = {}

        self.active_connections[call_uuid]['inbound'] = {
            'id' : inbound_stream['stream_id']
        }

        self.active_connections[call_uuid]['tts_queue'] = Queue()
        self.active_connections[call_uuid]['speaking'] = False


        connection = self.deepgram_client.listen.v1.connect(
            model='nova-3',
            encoding="linear16",
            sample_rate='16000' , 
            language = 'multi' , 
            #endpointing = 20 , 
            #vad_events = True , 
            #utterance_end_ms = 1000,
            #interim_results = True , 
            #dictation = True , 
            #smart_format = True , 
            diarize = True , 
            keyterm = 'jaipur, jaipoor, japur, btech, bca, bba, rajasthan, cse'
            # sample_rate = 16000 , 
        )

        self.active_connections[call_uuid]['stt-connection'] = connection

        self.logger.info(f'Intialzied connection with Call UUID : {self.active_connections}')

    async def get_stream_id(self , call_uuid) : 

        if call_uuid in self.active_connections : 

            return self.active_connections[call_uuid]['inbound']['id']

        else : raise ValueError(f'Call UUID : {call_uuid} was not found')

    def get_stt_connection(self , call_uuid : str) : 

        if call_uuid in self.active_connections : return self.active_connections[call_uuid].get('stt-connection')
        else : raise ValueError(f'Call UUID: {call_uuid} was not found')
