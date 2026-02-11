import os 
import json 
import wave

from io import BytesIO

from deepgram.client import DeepgramClient
from deepgram.listen.v1.media.types.media_transcribe_response import MediaTranscribeResponse
from deepgram.types.listen_v1response import ListenV1Response
from deepgram.types.listen_v1response_results import ListenV1ResponseResults
from deepgram.types.listen_v1response_results_channels import ListenV1ResponseResultsChannels
from deepgram.types.listen_v1response_results_channels_item import ListenV1ResponseResultsChannelsItem
from deepgram.types.listen_v1response_results_channels_item_alternatives_item import ListenV1ResponseResultsChannelsItemAlternativesItem
from deepgram.types.listen_v1response_results_channels_item_alternatives_item_words_item import ListenV1ResponseResultsChannelsItemAlternativesItemWordsItem

from .stt import STT 

class DEEPGRAM_STT(STT) : 

    def __init__(
        self , 
        config : dict
    ) -> None : 

        self.config : dict = config
        self.model : str = self.config['model-name']
        self.language : str = self.config['language']
        self.smart_format : bool = self.config['smart-format']
        self.punctuate : bool = self.config['punctuate']
        self.diarize : bool = self.config['diarize']
        
        self.client : DeepgramClient = DeepgramClient(api_key = os.getenv('DEEPGRAM_API_KEY' , ''))


        print(f'DeepGram STT Client Initialized with config {json.dumps(config , indent = 4)}')

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

    def convert_deepgram_words_to_json(
        self , 
        words : list[ListenV1ResponseResultsChannelsItemAlternativesItemWordsItem]
    ) -> list[dict[str , str | float | int]] : 

        words_dict : list = []

        for word in words : 

            words_dict.append(
                {
                    'word' : word.word , 
                    'start' : word.start , 
                    'end' : word.end , 
                    'confidence' : word.confidence , 
                    'speaker' : word.speaker , 
                    'speaker_confidence' : word.speaker_confidence
                }
            )

        return words_dict

    async def process_transcription(self , transcription_obj : ListenV1Response | MediaTranscribeResponse) : 

        transcription : str = ''
        words_dict : list[dict[str , str | float | int]] = []
        languages : str = 'en'

        if isinstance(transcription_obj , ListenV1Response) : 

            results : ListenV1ResponseResults = transcription_obj.results

            channels : list[ListenV1ResponseResultsChannelsItem] = results.channels
            first_channel : ListenV1ResponseResultsChannelsItem = channels[0]

            alternatives : list[ListenV1ResponseResultsChannelsItemAlternativesItem] | None = first_channel.alternatives

            if alternatives : 

                first_alternative : ListenV1ResponseResultsChannelsItemAlternativesItem = alternatives[0]
                transcription = first_alternative.transcript if first_alternative.transcript else ''

                if transcription : 

                    words : list[ListenV1ResponseResultsChannelsItemAlternativesItemWordsItem] | None = first_alternative.words

                    if words : words_dict = self.convert_deepgram_words_to_json(words)

                    languages = first_channel.detected_language[0] if first_channel.detected_language else 'en'

        return transcription , words_dict , languages

    async def transcribe_bytes(
        self , 
        audio_bytes : bytes , 
        model : str | None = None ,  
        language : str | None = None , 
        smart_format : bool = False , 
        punctuate : bool = False , 
        diarize : bool = False , 
        keyterm : str = ''
    ) -> tuple[str , list , str] : 

        transcription = self.client.listen.v1.media.transcribe_file(
            request = self._add_wav_header(audio_bytes) , 
            model = 'nova-3' , 
            diarize = True , 
            keyterm = keyterm
        )

        transcript , words , languages = await self.process_transcription(transcription)

        return transcript  , words , languages

    async def transcribe_url(
        self , 
        url : str , 
        model : str | None = None ,  
        language : str | None = None , 
        smart_format : bool = False , 
        punctuate : bool = False , 
        diarize : bool = False , 
        keyterm : str = ''
    ) -> tuple[str , list , str] : 

        transcription : ListenV1Response | MediaTranscribeResponse = self.client.listen.v1.media.transcribe_url(
            url = url , 
            model = 'nova-3' , 
            diarize = True , 
            keyterm = keyterm
        )

        transcript , words , languages = await self.process_transcription(transcription)

        return transcript  , words , languages

    # async def transcribe_file(
    #     self , 
    #     file_path : str , 
    #     model : str | None = None ,  
    #     language : str | None = None , 
    #     smart_format : bool = False , 
    #     punctuate : bool = False , 
    #     diarize : bool = False
    # ) -> tuple[str , list , str] : 

    #     with open(file_path , 'rb') as audio_file : audio_bytes : bytes = audio_file.read()

    #     transcription = self.client.listen.rest.v(
    #         self.config['api-version']
    #     ).transcribe_file(
    #         source = {'buffer' : audio_bytes} , 
    #         options = dict(
    #             model = model if model else self.model , 
    #             language = language if language else self.language , 
    #             smart_format = smart_format if smart_format else self.smart_format , 
    #             punctuate = punctuate if punctuate else self.punctuate , 
    #             diarize = diarize if diarize else self.diarize
    #         )
    #     )

    #     transcript , words , languages = await self.process_transcription(transcription = transcription)

    #     return transcript , words , languages[0]

    # async def __call__(
    #     self , 
    #     buffer_stream : bytes , 
    #     model : str | None = None , 
    #     language : str | None = None
    # ) -> str : 

    #     transcription , words , languages = await self.transcribe_bytes(
    #         audio_bytes = buffer_stream , 
    #         model = model , 
    #         language = language
    #     )
        
    #     return transcription , words , languages[0]