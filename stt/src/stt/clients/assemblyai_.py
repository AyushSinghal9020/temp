import assemblyai as aai
from .stt import STT
import os
from assemblyai import LanguageDetectionOptions, SpeakerIdentificationRequest, SpeechUnderstandingFeatureRequests, SpeechUnderstandingRequest, Transcriber, Transcript, TranscriptionConfig

class ASSEMBLYAI_STT(STT) : 

    def __init__(
        self , 
        config : dict
    ) -> None : 

        self.config : dict = config

        aai.settings.api_key = os.environ['ASSEMBLY_AI_API_KEY']

    def normalize_speakers_chronological(self , words_list : list[dict[str , str | int | float]]) : 

        speaker_map = {}
        next_speaker_id = 0

        processed_words = []
        
        for word in words_list : 

            new_word = word.copy()
            original_speaker = new_word.get("speaker")
            

            if original_speaker not in speaker_map:

                speaker_map[original_speaker] = next_speaker_id
                next_speaker_id += 1

            new_word["speaker"] = speaker_map[original_speaker]

            processed_words.append(new_word)

        return processed_words

    async def transcribe_url(
        self , 
        url : str , 
        summarization : bool = False , 
        iab_categories : bool = False , 
        sentiment_analysis : bool = False , 
        speaker_labels : bool = False , 
        format_text : bool = False , 
        punctuate : bool = False , 
        speech_model : str = 'universal' , 
        language_detection : bool = False , 
        code_switching : bool = False , 
        code_switching_confidence_threshold : float = 0.5 , 
        speech_understanding : bool = False , 
        speaker_type : str = 'name' , 
        known_values : list[str] = ['AI' , 'HUMAN'] , 
        keyterm_prompting : bool = False , 
        keyterm_prompts : list[str] = ['']
    ) -> tuple[str , list[dict[str , str | int]] , str] : 

        config : TranscriptionConfig = TranscriptionConfig(
            summarization = summarization , 
            iab_categories = iab_categories , 
            sentiment_analysis = sentiment_analysis , 
            speaker_labels = speaker_labels , 
            format_text = format_text , 
            punctuate = punctuate , 
            speech_model = aai.SpeechModel.universal if speech_model == 'universal' else aai.SpeechModel.universal , 
            language_detection = language_detection
        )

        if code_switching : config.language_detection_options = LanguageDetectionOptions(
            code_switching = True , 
            code_switching_confidence_threshold = code_switching_confidence_threshold
        )

        if speech_understanding : config.speech_understanding = SpeechUnderstandingRequest(
            request = SpeechUnderstandingFeatureRequests(
                speaker_identification = SpeakerIdentificationRequest(
                    speaker_type = speaker_type , 
                    known_values = known_values
                )
            )
        )

        if keyterm_prompting : config.keyterms_prompt = keyterm_prompts

        transcriber : Transcriber = Transcriber(config = config)
        transcript : Transcript = transcriber.transcribe(url)
        json_transcript : dict | None = transcript.json_response

        if json_transcript : return json_transcript['text'] , self.normalize_speakers_chronological(json_transcript['words']) , 'en'
        else : return '' , [] , ''