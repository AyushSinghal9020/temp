from typing import Any
from logging import Logger 

from .transcription_ import run_stt_url , run_stt_file
from .llm_ import get_summary , get_keywords , analyze_sentiment , get_student_details
# from .sendnestjs_ import send_results_with_retry

async def process_audio_pipeline_url(
    stt_client : Any , 
    llm_client : Any ,  
    url : str , 
    logger : Logger , 
    redis_client , 
    call_uuid : str
) -> dict : 

    global_status : bool = True

    global_transcription_data : list[dict[str , str | int]] = []
    global_summary : str = ''
    global_sentiment : dict[str , float] = {'score' : 0.5}
    global_keywords : list[str] = []
    global_student_details = {
        "name" : None , 
        "12th_score"  : None , 
        "12th_result_status" : None , 
        "city" : None , 
        "hostel" : None , 
        "mode_of_transport" : None , 
        "course" : None , 
        "branch" : None
    }

    status , transcription_data = await run_stt_url(
        client = stt_client , 
        url = url , 
        redis_client = redis_client , 
        call_uuid = call_uuid , 
        logger = logger
    )

    if status : 

        status , summary = await get_summary(
            groq_client = llm_client , 
            transcription = transcription_data , 
            logger = logger
        )

        if status : 

            status , sentiment  = await analyze_sentiment(
                groq_client = llm_client , 
                transcription = transcription_data , 
                summary = summary , 
                logger = logger
            )

            if status : 

                status , keywords  = await get_keywords(
                    groq_client = llm_client , 
                    transcription = transcription_data , 
                    summary = summary , 
                    logger = logger
                )

                if status : 

                    status , student_details = await get_student_details(
                        groq_client = llm_client , 
                        transcription = transcription_data , 
                        summary = summary , 
                        logger = logger
                    )

                    if status : 

                        global_keywords = keywords
                        global_sentiment = sentiment 
                        global_summary = summary
                        global_transcription_data = transcription_data
                        global_student_details = student_details

                else : global_status = status
            else : global_status = status
        else : global_status = status
    else : global_status = status

    return {
        'status' : global_status , 
        'transcriptions' : global_transcription_data , 
        'summary' : global_summary , 
        'sentiment' : global_sentiment , 
        'tags' : global_keywords , 
        'student_details' : global_student_details
    }

# async def process_audio_pipeline_file(
#     stt_client : Any , 
#     llm_client : Any , 
#     sentiment_pipeline : Any , 
#     url : str , 
#     logger : Logger
# ) -> dict : 

#     transcription_data : dict = await run_stt_file(
#         client = stt_client , 
#         file_path = url
#     )

#     summary : str = await get_summary(
#         groq_client = llm_client , 
#         transcription = transcription_data['formatted_transcript']
#     )
    
#     sentiment : dict = await analyze_sentiment(
#         pipeline = sentiment_pipeline , 
#         text = summary
#     )
    

#     keywords : list = await get_keywords(
#         groq_client = llm_client , 
#         transcription = transcription_data['diarized_transcript'] , 
#         summary = summary
#     )

#     return {
#         'transcriptions' : transcription_data['diarized_transcript'] , 
#         'summary' : summary , 
#         'sentiment' : sentiment , 
#         'keywords' : keywords
#     }

async def process_single_conversation_url(
    stt_client : Any , 
    llm_client : Any , 
    conversation_id : str , 
    recording_url : str ,
    logger : Logger
) -> dict : 

        # logger.info(f"Processing conversation {conversation_id}...")

        results : dict = await process_audio_pipeline_url(
            stt_client = stt_client , 
            llm_client = llm_client , 
            url = recording_url , 
            logger = logger
        )

        analysis_result = {
            "success" : results['status'] , 
            "conversationId" : conversation_id , 
            "transcriptions" : results["transcriptions"] , 
            "summary" : results["summary"] , 
            "sentiment" : results["sentiment"]
        }

        # logger.info(f"Successfully processed conversation {conversation_id}")

        return analysis_result

# async def process_conversations_async(
#     stt_client : Any , 
#     llm_client : Any , 
#     conversations : list , 
#     config : dict , 
#     logger : Logger
# ) : 

#     results : list[dict] = []

#     for conversation in conversations : 

#         if (
#             'recordingUrl' in conversation and 
#             conversation['recordingUrl'] != 'No recording available'
#         ) : results.append(
#             await process_single_conversation_url(
#                 stt_client = stt_client , 
#                 llm_client = llm_client , 
#                 conversation_id = conversation['id'] , 
#                 recording_url = conversation['recordingUrl'] , 
#                 logger = logger
#             )
#         )

#     if results : response = send_results_with_retry(
#         results = results  , 
#         config = config , 
#         logger = logger
#     )

#     else : logger.warn('No results to send to nest')