import base64
import asyncio

from .tts import TTS

from google.cloud.texttospeech import (
    AudioEncoding , 
    SsmlVoiceGender , 
    TextToSpeechClient , 
    VoiceSelectionParams , 
    StreamingSynthesizeConfig , 
    StreamingSynthesizeRequest , 
    StreamingSynthesisInput , 
    StreamingAudioConfig
)

class GOOGLE_TTS(TTS) : 

    def __init__(self , config : dict) -> None : 

        super().__init__()

        self.config : dict = config

        self.client : TextToSpeechClient = TextToSpeechClient.from_service_account_file(filename = self.config['service-file-path'])

    async def stream(self , text : str) : 

        streaming_config : StreamingSynthesizeConfig = StreamingSynthesizeConfig(
            voice = VoiceSelectionParams(
                language_code = self.config['language'] , 
                ssml_gender = SsmlVoiceGender.FEMALE , 
                name = f'{self.config["language"]}-Chirp3-HD-{self.config["name"]}'
            ) , 
            streaming_audio_config = StreamingAudioConfig(
                audio_encoding = AudioEncoding.MULAW , 
                sample_rate_hertz = 8000
            )
        )

        def request_generator() : 

            yield StreamingSynthesizeRequest(streaming_config = streaming_config)
            yield StreamingSynthesizeRequest(input = StreamingSynthesisInput(text = text))

        streaming_responses = await asyncio.to_thread(
            self.client.streaming_synthesize , 
            request_generator()
        )

        for response in streaming_responses : 

            if response.audio_content : yield base64.b64encode(response.audio_content).decode('utf-8')

    async def __call__(self , text : str) : 

        async for chunk in self.stream(text = text) : yield chunk