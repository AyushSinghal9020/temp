from logging import Logger
import time
from redis import Redis 
import traceback
import json
from typing import Any , Optional

async def run_stt_url(
    client : Any , 
    url : str , 
    call_uuid: str,
    redis_client: Redis,
    logger: Logger
) -> tuple[bool, list[dict[str, str | int]]]:
    """
    Retrieve conversation history from Redis with separate speaker segments
    
    This version maintains speaker alternation for better analysis
    """
    
    try:
        start_time: float = time.time()
        
        history_key: str = f"livehistory:{call_uuid}"
        messages = await redis_client.lrange(history_key, 0, -1)
        
        if not messages:

            response : tuple[str , list , str] = await client.transcribe_url(
                url = url , 
                speaker_labels = True , 
                format_text = True , 
                punctuate = True , 
                language_detection = True , 
                code_switching = True , 
                # speech_understanding = True , 
                keyterm_prompting = True , 
                keyterm_prompts = ['JECRC University' , 'Riya']
            )

            # transcription : str = response[0]
            words : list = response[1]
            # language : str = response[2]

            processed_words = await process_words(words = words)

            return (True, processed_words)
        
        processed_words: list[dict[str, str | int]] = []
        
        for msg in messages:
            try:
                message_data: dict = json.loads(msg)
                role: str = message_data.get('role', '')
                content: str = message_data.get('content', '')
                
                # Map role to speaker (0 = assistant, 1 = user)
                speaker: int = 0 if role == 'assistant' else 1
                
                processed_words.append({
                    "text": content.strip(),
                    "speaker": speaker
                })
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")
                continue
        
        logger.info(f'Transcription retrieval time for call_uuid {call_uuid}: {time.time() - start_time:.2f}s')
        logger.info(f'Retrieved {len(processed_words)} speaker segments')
        
        return (True, processed_words)
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history for {call_uuid}: {e}")
        import traceback
        traceback.print_exc()
        return (False, [])

async def run_stt_file(
    client : Any , 
    file_path : str
) -> list[dict[str , str | int]] : 

    response : tuple[str , list , str] = await client.transcribe_file(file_path = file_path)

    transcription : str = response[0]
    words : list = response[1]
    language : str = response[2]

    processed_words : list[dict[str , str | int]] = await process_words(words = words)

    return processed_words

async def process_words(
    words : list[dict]
) -> list[dict[str , str | int]]: 

    diarized_transcript : list = []
    current_speaker : Optional[int] = None
    current_text : list[str] = []

    for word in words : 

        root_word : str = word['text']
        # start : float = word['start']
        # end : float = word['end']
        # word_confidence : float = word['confidence']
        # punctuated_word : str = word['punctuated_word']
        speaker : int = word['speaker']
        # language : str = word['languages']
        # speaker_confidence : float = word['speaker_confidence']

        if current_speaker is None : current_speaker = speaker

        if speaker != current_speaker : 

            diarized_transcript.append({
                'speaker' : current_speaker , 
                'text' : ' '.join(current_text)
            })

            current_speaker = speaker 
            current_text = [root_word]

        else : current_text.append(root_word)

    if current_text : diarized_transcript.append({
        'speaker' : current_speaker , 
        'text' : ' '.join(current_text)
    })


    return diarized_transcript