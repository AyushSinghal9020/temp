import base64
import os

from .tts import TTS

from smallestai.waves import WavesClient

class SMALLESTAI_TTS(TTS) : 

    def __init__(self , config : dict) -> None : 

        super().__init__()

        self.config : dict = config

        self.client : WavesClient = WavesClient(api_key = os.environ['SMALLEST_API_KEY'])

    async def stream(self , text : str) : 

        words : list[str] = text.split()

        for index in range(0 , len(words) , 15) : 

            audio_bytes : bytes = self.client.synthesize(
                ' '.join(words[index : index + 15]) , 
                output_format = 'pcm' , 
                sample_rate = 16000 , 
                language = 'hi' , 
                voice_id = 'maya' , 
                model = 'lightning-large' , 
                speed = 1.1 , 
                similarity = 0.7 , 
                enhancement = 1
                # pronounciation_dicts = ['695df353558162d9120875aa']
            ) 

            yield base64.b64encode(audio_bytes).decode('utf-8')

    async def __call__(self , text : str) : 

        async for chunk in self.stream(text = text) : yield chunk