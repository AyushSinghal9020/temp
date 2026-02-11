import os 
import wave 

from groq import Groq 
from io import BytesIO
from typing import Tuple
from dotenv import load_dotenv

from .stt import STT 

class GROQ_STT(STT) : 

    def __init__(
        self , 
        config : dict , 
        env_path : str = '.env'
    ) : 

        load_dotenv(env_path)

        self.client : Groq = Groq(api_key = os.getenv('GROQ_API_KEY'))

        self.config : dict = config 

        print(f'GROQ_STT initialized with config : {self.config}')

    def _add_wav_header(
        self , 
        raw_audio_data : bytes
    ) -> bytes : 

        with BytesIO() as wav_file : 

            wav_writer = wave.open(wav_file , 'wb')

            try : 

                wav_writer.setnchannels(self.config['channels'])
                wav_writer.setsampwidth(self.config['sample-width'])
                wav_writer.setframerate(self.config['sample-rate'])

                wav_writer.writeframes(raw_audio_data)
            
            finally : wav_writer.close()

            return wav_file.getvalue()

    async def transcribe(
        self , 
        buffer_stream : bytes
    ) -> Tuple[str , str] : 

        wav_buffer : bytes = self._add_wav_header(raw_audio_data = buffer_stream)

        raw_transcription = self.client.audio.transcriptions.create(
            file = ('file.wav' , wav_buffer) , 
            model = self.config['model-name'] , 
            response_format = 'verbose_json'
        )

        raw_transcriptions : dict = raw_transcription.to_dict()
        transcription : str = raw_transcriptions['text']
        language : str = raw_transcriptions['language']

        return transcription , language 

    async def __call__(
        self , 
        buffer_stream : bytes
    ) : 

        return await self.transcribe(buffer_stream)