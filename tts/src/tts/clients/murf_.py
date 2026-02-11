import base64
import os

from requests import Response
import requests

from .tts import TTS

class MURF_TTS(TTS) : 

    def __init__(self , config : dict) -> None : 

        super().__init__()

        self.config : dict = config

        self.url : str = 'https://global.api.murf.ai/v1/speech/stream'

    async def stream(self , text : str) : 

        data = {
            'voice_id' : 'en-IN-anisha' , 
            'text' : text , 
            'multi_native_locale' : 'en-IN' , 
            'model' : 'FALCON' , 
            'format' : 'WAV' , 
            'sampleRate' : 16000 , 
            'channelType' : 'MONO'
        }

        headers = {
            'api-key' : os.environ['MURF_AI_API_KEY'] , 
            'Content-Type' : 'application/json'
        }

        response : Response = requests.post(url = self.url , headers = headers , json = data ,  stream = True)

        print(response.status_code)

        for chunk in response.iter_content(chunk_size = 1024) : 

            if chunk : 

                # print(chunk)

                yield base64.b64encode(chunk).decode('utf-8')
            

    async def __call__(self , text : str) : 

        async for chunk in self.stream(text = text) : yield chunk