
from io import BytesIO
import wave

from typing import Tuple

from google.api_core.client_options import ClientOptions

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types.cloud_speech import RecognizeRequest , AutoDetectDecodingConfig , RecognitionConfig

from .stt import STT

class GOOGLE_STT(STT) : 

    def __init__(
        self , 
        config : dict
    ) -> None : 

        self.config : dict = config

        self.client = SpeechClient.from_service_account_file(
            filename = '/teamspace/studios/this_studio/voicexpgpuassignment-1763a1ea9bd0 (1).json' , 
            client_options = ClientOptions(
                api_endpoint = f"us-speech.googleapis.com"
            )
        )

        # self.client = SpeechClient.from_service_account_info(
        #     info = {
        #         'type' : self.auth_config['type'] , 
        #         'project_id' : self.auth_config['project-id'] , 
        #         'private_key_id' : os.getenv('GCP_PRIVATE_KEY_ID') , 
        #         'private_key' : os.getenv('GCP_PRIVATE_KEY') , 
        #         'client_email' : self.auth_config['client-email'] , 
        #         'client_id' : os.getenv('GCP_CLIENT_ID') , 
        #         'auth_uri' : self.auth_config['auth-uri'] , 
        #         'token_uri' : self.auth_config['token-uri'] , 
        #         'auth_provider_x509_cert_url' : self.auth_config['auth-provider-x509-cert-url'] , 
        #         'client_x509_cert_url' : self.auth_config['client-x509-cert-url'] , 
        #         'universe_domain' : self.auth_config['universe-domain']
        #     }
        # )

        print(self.client , type(self.client))
        print(f'GOOGLE STT Initialized with config : {self.config}')

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


        config : RecognitionConfig = RecognitionConfig(
            auto_decoding_config = AutoDetectDecodingConfig() , 
            language_codes = self.config['detect-langs'] , 
            model = self.config['model-name']
        )

        request = RecognizeRequest(
            recognizer = 'projects/1017478711177/locations/us/recognizers/himrpt-ia-goa' , 
            config = config , 
            content = self._add_wav_header(buffer_stream)
            # content = buffer_stream
        )

        response = self.client.recognize(request=request)

        print(response , type(response))

        if not response.results : return ''

        result = response.results[0]
        print(result , type(result))

        transcription = result.alternatives[0].transcript

        return transcription , ''

    async def __call__(
        self , 
        buffer_stream : bytes
    ) -> Tuple[str , str]: 
        '''
        Call the transcribe method and return the transcription. 

        Args :

            - buffer_stream (bytes): The audio data to transcribe.
            - sample_rate (int | None): Sample rate of the audio. Defaults to self.sample_rate.
            - num_channels (int | None): Number of audio channels. Defaults to self.num_channels.
            - width (int | None): Sample width in bytes. Defaults to self.width.
            - file_name (str | None): Name of the file to save the audio data to. Defaults to self.file_name.

        Returns : 

            - str: The transcription of the audio stream.
        '''

        print(f'Calling Google STT with audio stream of length : {len(buffer_stream)} bytes')

        return await self.transcribe(buffer_stream = buffer_stream)  