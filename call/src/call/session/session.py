import os
import time
import json
import asyncio
import requests
import traceback

from uuid import uuid4
from typing import Any
from redis import Redis
from queue import Empty
from logging import Logger
from threading import Thread
from plivo import RestClient
from fastapi import WebSocket
from requests import Response 
from deepgram import DeepgramClient

from asyncio import Queue , Task, create_task, sleep

from deepgram.core.events import EventType

from deepgram.extensions.types.sockets import ListenV1ControlMessage , ListenV1ResultsEvent

from deepgram.extensions.types.sockets.listen_v1_results_event import ListenV1Alternative , ListenV1Channel

from ..event import START_EVENT , MEDIA_EVENT , PLAYED_EVENT , CLEAR_EVENT
from ..connection import ConnectionManager

class SESSION : 

    def __init__(
        self , 
        workflow :  str , 
        config : dict , 
        tts_client : Any , 
        logger : Logger , 
        websocket_object : WebSocket , 
        stream_id : str , 
        connection_manager : ConnectionManager , 
        call_uuid : str ,
        redis_client : Redis ,
        plivo_client : RestClient
    ) : 

        self.workflow : str = workflow
        self.config : dict = config
        self.tts_client : Any = tts_client
        self.plivo_client : RestClient = plivo_client

        self.user_audio_input : bytes = bytes()

        self.user_speaking = False
        self.tts_speaking = False
        self.speech_started = False

        self.websocket_object : WebSocket = websocket_object
        self.stream_id : str = stream_id

        self.session_id : str = str(uuid4())

        self.logger : Logger = logger

        self.websocket_queue : Queue = Queue()
        self.stream_queue : Queue = Queue()

        self.stt_queue : Queue = Queue() 
        self.llm_queue : Queue = Queue() 
        self.tts_queue : Queue = Queue() 

        self.transcription : str = ''

        self.connection_manager = connection_manager

        self.call_uuid : str = call_uuid

        self.tasks : list[Task] = []

        self.deepgram_client = DeepgramClient(api_key = os.environ['DEEPGRAM_API_KEY'])

        self.redis_client : Redis = redis_client
        self.history_key : str = f"livehistory:{self.call_uuid}"
        self.hangup_status : bool = False

        self.last_transcription_time : float = time.time()
        self.inactivity_timeout : float = 20.0
        self.inactivity_message : str = "Hello, I didn't hear you for long, do you have any questions?"
        self.inactivity_counter : int = 0

        self.is_connected : bool = True

    async def receiver_task(self) : 

        while self.is_connected: 

            data = await self.websocket_object.receive()

            await self.websocket_queue.put(data)

    async def router_task(self) : 

        try : 

            while True : 

                data = await self.websocket_queue.get()

                if data['type'] == 'websocket.receive' : 

                    if 'text' in data : 

                        textual_data_str : str = data['text']
                        
                        try : 
                            textual_data_dict : dict = json.loads(textual_data_str)

                            if 'event' in textual_data_dict : 

                                if textual_data_dict['event'] == 'start' : 
                                    event_obj = START_EVENT(**textual_data_dict)

                                elif textual_data_dict['event'] == 'media' : 

                                    event_obj = MEDIA_EVENT(**textual_data_dict)
                                    await self.stream_queue.put(event_obj)

                                elif textual_data_dict['event'] == 'playedStream' : 

                                    event_obj = PLAYED_EVENT(**textual_data_dict) 

                                    self.tts_speaking = False
                                    self.last_transcription_time = time.time()

                                    self.barge_in_enabled = True
                                    self.logger.info(f"Barge-in re-enabled after short response ({self.last_response_word_count} words)")

                                    if self.hangup_status : 

                                        self.plivo_client.calls.hangup(call_uuid = self.call_uuid)

                                elif textual_data_dict['event'] == 'clearedAudio' : 

                                    event_obj = CLEAR_EVENT(**textual_data_dict) 

                                    self.tts_speaking = False

                                else : 
                                    print(f"Unhandled Event: {textual_data_dict}")

                            else : 
                                print(f"No 'event' key found: {textual_data_dict}")
                        
                        except json.JSONDecodeError : 
                            self.logger.error(f"Failed to parse JSON: {textual_data_str}")

                        except Exception as e : 

                            self.logger.error(f"Error processing message logic: {e}")

                            traceback.print_exc()
                    
                    else : 
                        print(f"Received non-text data: {data}")

                elif data['type'] == 'websocket.disconnect' : 
                    
                    code = data.get('code', 'Unknown')
                    reason = data.get('reason', 'Unknown')
                    self.logger.warning(f"Disconnected , code : '{code}', reason : {reason}")

                    self.is_connected = False

                    await self.disconnect()

                    break

                else : 
                    print(f"Unknown data type: {data}")

        except Exception as e : 

            print(f"CRITICAL ERROR IN ROUTER TASK: {e}")

            traceback.print_exc()

            self.is_connected = False

    async def inactivity_monitor_task(self) : 

        while self.is_connected : 

            try : 

                await asyncio.sleep(1)

                if not self.is_connected : 
                    break

                time_since_last_transcription = time.time() - self.last_transcription_time

                if time_since_last_transcription >= self.inactivity_timeout and not self.tts_speaking:

                    self.logger.info(f"Inactivity detected for {time_since_last_transcription:.1f}s. Sending reminder.")

                    await self.tts_queue.put(self.inactivity_message)

                    self.inactivity_counter += 1 

                    if self.inactivity_counter >= 3 : 
                        self.hangup_status = True
                        print('Hangup True')

                    self.last_transcription_time = time.time()

            except asyncio.CancelledError : 
                break

            except Exception as e : 

                self.logger.error(f"Error in inactivity monitor task: {e}")

                traceback.print_exc()

    async def vad_task(self) : 

        await self.tts_queue.put('Hello !!, This is Riya, JECRC University AI Admission Counsellor, may I please know your name and which course you are interested in ?')  

        self.loop = asyncio.get_running_loop()
        
        connection = self.connection_manager.get_stt_connection(call_uuid = self.call_uuid)

        try:
            with connection as connection : 

                create_task(
                    self._send_keepalive(connection)
                )

                def on_message(message : ListenV1ResultsEvent) -> None : 
                    if self.barge_in_enabled : 

                        if message.type == 'Results' : 

                            channel_index : list[int] = message.channel_index
                            duration : float = message.duration
                            start : float = message.start 
                            is_final : bool | None = message.is_final 
                            speech_final : bool | None = message.speech_final
                            channel : ListenV1Channel = message.channel

                            alternatives : list[ListenV1Alternative] = channel.alternatives

                            first_alternative : ListenV1Alternative = alternatives[0]

                            transcript : str = first_alternative.transcript

                            print(f'Transcription ---------------> : {transcript}')

                            if len(transcript.strip()) > 0 : 

                                # Update the last transcription time whenever we receive valid transcription
                                self.last_transcription_time = time.time()

                                if self.tts_speaking and self.barge_in_enabled : 

                                    print(f"Deepgram detected speech: '{transcript}'. Stopping AI.")

                                    asyncio.run_coroutine_threadsafe(self.stop_audio() , self.loop)

                            self.transcription += transcript
                    else : 
                        self.logger.warning('Dropping speech as barge-in is disabled')
                connection.on(EventType.OPEN , lambda _ : print("Connection opened"))
                connection.on(EventType.MESSAGE , on_message)
                connection.on(EventType.CLOSE , lambda _ : print("Connection closed"))
                connection.on(EventType.ERROR , lambda error : print(f"Error: {error}"))

                def start_listening() : connection.start_listening()

                listen_thread = Thread(target = start_listening)
                listen_thread.start()

                try : 

                    while self.is_connected: 

                        try : 

                            data : MEDIA_EVENT = await self.stream_queue.get()
                            
                            # Check connection before processing
                            if not self.is_connected:
                                break

                            connection.send_media(data.audio_bytes)
                            if data.possiblity : 

                                self.user_speaking = True 
                                self.silence_packet_counter = 0 
                                
                                print('\rListening...' , end = '\n' , flush = True)

                            else : 

                                if len(self.transcription) > 3 : 
                                    
                                    self.silence_packet_counter += 1
                                    
                                    print(f'\rSilence packet received ({self.silence_packet_counter})' , end = '' , flush = True)
                                    
                                    if self.silence_packet_counter >= self.config['settings']['max-continous-interruption'] : 

                                        await self.llm_queue.put(self.transcription)
                                        self.transcription = ''
                                        self.user_audio_input = bytes()
                                        self.silence_packet_counter = 0 

                                    else : 

                                        print(f'\rListening... for Silence {self.silence_packet_counter}' , end = '' , flush = True)
                                
                                else : print(f'\rBuffer too short, ignoring silence. Length: {len(self.user_audio_input)}' , end = '' , flush = True)

                        except asyncio.CancelledError : 
                            break
                        except Exception as e : 

                            self.logger.error(f"Error in VAD task for session {self.session_id}: {e}")
                            await asyncio.sleep(0.1)

                except Exception as e : 
                    self.logger.error(f"Fatal error in VAD task for session {self.session_id}: {e}")
                finally:
                    # Close Deepgram connection when VAD task ends
                    try:
                        connection.finish()
                        self.logger.info("Deepgram connection closed")
                    except Exception as e:
                        self.logger.error(f"Error closing Deepgram connection: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error in VAD task connection: {e}")
            traceback.print_exc()
        finally:
            # Ensure we trigger disconnect if not already disconnected
            if self.is_connected:
                self.is_connected = False
                await self.disconnect()

    async def add_to_history(self, role: str, content: str):

        try:
            message = {
                'role': role,
                'content': content,
                'timestamp': time.time()
            }
            
            # Add to Redis list
            self.redis_client.rpush(self.history_key, json.dumps(message))
            
            # Optional: Set expiry on the key (e.g., 24 hours)
            self.redis_client.expire(self.history_key, 86400)
            
            self.logger.info(f"Added to history [{role}]: {content}...")
            
        except Exception as e:
            self.logger.error(f"Error adding to history: {e}")

    async def run_llm(self) : 

        while self.is_connected: 

            try : 

                query : str = await self.llm_queue.get()

                # Skip if disconnected
                if not self.is_connected:
                    break

                # Add user message to history
                await self.add_to_history('user', query)

                start_time : float = time.time()

                response : str = await self.run_ag(query = query)

                print(f'-------------> LLM : {time.time() - start_time}')

                print(f'----------------------------> {response}')

                await self.tts_queue.put(response)

            except asyncio.CancelledError:
                break
            except Exception as e : 
                self.logger.error(f"Error in LLM task for session {self.session_id}: {e} : {traceback.format_exc()}")

    async def run_ag(self , query : str) -> str : 

        response : Response = requests.post(
            url = self.config['agent-url'] , 
            json = {
                'message' : query , 
                'user_id' : self.session_id
            }
        )

        if response.status_code == 200 : 
            if 'response' in response.json() : 
                self.hangup_status = response.json()['hangup']
                if self.hangup_status : 
                    self.barge_in_enabled = False

                print(self.hangup_status , self.barge_in_enabled)
                llm_response = response.json()['response'].replace('Hons' , 'Honors').replace('hons' , 'Honors')

                return llm_response

        return 'Sorry we were unable to process your resquest'

    async def run_tts(self) : 

        while self.is_connected: 

            try : 

                speaking_text : str = await self.tts_queue.get()

                if not self.is_connected : 
                    break

                await self.add_to_history('assistant' , speaking_text)

                word_count = len(speaking_text.split())
                self.last_response_word_count = word_count
                
                if word_count <= 30 : 

                    self.barge_in_enabled = False
                    self.logger.info(f"Barge-in disabled for short response ({word_count} words)")

                else : 

                    if self.hangup_status : 
                            self.barge_in_enabled = False 
                            self.logger.info(f'Barge in disabled as final hangup')

                    else : 
                        self.barge_in_enabled = True
                        self.logger.info(f"Barge-in enabled for response ({word_count} words)")

                # start_time : float = time.time()

                async for chunk in self.tts_client(speaking_text) : 

                    if not self.is_connected : 
                        break

                    await self.websocket_object.send_text(

                        json.dumps(
                            {
                                'event' : self.config['play-audio']['event'] , 
                                'media' : {
                                    'contentType' : self.config['play-audio']['contentType'] , 
                                    'sampleRate' : self.config['play-audio']['sampleRate'] , 
                                    'payload' : chunk
                                }
                            }
                        )
                    )

                    self.tts_speaking = True

                if self.is_connected : 

                    await self.websocket_object.send_text(
                        json.dumps(
                            {
                            'event' : 'checkpoint' , 
                            'streamId' : self.stream_id , 
                            'name' : 'something_unique' 
                        })
                    )

                self.last_transcription_time = time.time()

            except asyncio.CancelledError : 
                break

            except Exception as e : 

                if self.is_connected : 
                    self.logger.error(f"Error in TTS task for session {self.session_id}: {e}")

                else : 
                    self.logger.info(f"TTS task stopped - connection closed")


    async def start_connection(self) : 
        
        await self.websocket_object.accept()

    async def start(self) : 

        self.tasks.append(asyncio.create_task(self.run_llm()))
        self.tasks.append(asyncio.create_task(self.run_tts()))

        await self.start_connection()

        self.tasks.append(asyncio.create_task(self.receiver_task()))
        self.tasks.append(asyncio.create_task(self.router_task()))
        self.tasks.append(asyncio.create_task(self.vad_task()))
        self.tasks.append(asyncio.create_task(self.inactivity_monitor_task()))  # Add the new task

    async def _flush_queue(self, queue: Queue):

        while not queue.empty() : 

            try : 

                queue.get_nowait()
                queue.task_done()

            except Empty : break

    async def disconnect(self) : 

        # Prevent multiple disconnect calls
        if not self.is_connected:
            return
            
        self.is_connected = False

        self.logger.info(f"Disconnecting session {self.session_id}. Cancelling background tasks.")

        # Cancel all running tasks
        for task in self.tasks:
            if not task.done() : 
                task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks , return_exceptions = True)

        self.logger.info("Flushing all queues.")

        # Flush all queues
        await self._flush_queue(self.websocket_queue)
        await self._flush_queue(self.stream_queue)
        await self._flush_queue(self.stt_queue)
        await self._flush_queue(self.llm_queue)
        await self._flush_queue(self.tts_queue)

        # Close websocket if still open
        try:
            if self.websocket_object.client_state.name != 'DISCONNECTED':
                await self.websocket_object.close()
                self.logger.info("WebSocket closed")
        except Exception as e:
            self.logger.error(f"Error closing websocket: {e}")

        self.logger.info(f"Session {self.session_id} fully disconnected and cleaned up.")

        self.speaking = False
        self.tts_speaking = False
        self.user_speaking = False

    async def stop_audio(self) : 

        if not self.is_connected:
            return

        try:
            await self.websocket_object.send_text(
                data = json.dumps(
                    {
                        'event' : 'clearAudio' ,
                        'streamId' : self.stream_id
                    }
                )
            )

            self.speaking = False
            self.tts_speaking = False
            
        except Exception as e:
            self.logger.error(f"Error stopping audio: {e}")
            # If we can't send, likely disconnected
            if self.is_connected:
                self.is_connected = False
                await self.disconnect()

    async def _send_keepalive(self , connection) : 

        await sleep(5)
        connection.send_control(ListenV1ControlMessage(type = 'KeepAlive'))

        self.logger.info('Keep Alive Message sent')