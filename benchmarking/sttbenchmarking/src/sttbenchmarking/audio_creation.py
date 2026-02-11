import os
import csv
import uuid
import json 
import base64
import asyncio
import shutil

from tqdm import tqdm

try:
    import audioop
except ModuleNotFoundError:
    import audioop_lts as audioop

from tts import GOOGLE_TTS # * Can be change to any tts as of choice

tts_client : GOOGLE_TTS = GOOGLE_TTS(# * Can be change to any tts as of choice/ change the config based on the requirements
    config = {
        "language" : "hi-IN" , 
        "service-file-path" : "/teamspace/studios/this_studio/vxp-agent-backend/sts.json" , 
        "name" : "Achernar"
    }
)

with open('assets/inp_data.json') as input_data_file : input_data : dict[str , dict[str , list[str]]] = json.load(fp = input_data_file)
# {
#     <audio_duration_group(can be any string wanted (current : 6sec , 15sec , 30sec , 1min , 6min , 15min , 30min , 1hour , ...))> : {
#         <audio_language_group(can be any language string in decoding ISO 639-1 format (current : en , hi , multi(represents multi-lingual, ISO 639-1 format still required after this string, in chronological order of thier audio_duration of time, for example a audio of 60 sec having both English and Hindi with English total as 35 sec of audio and Hindi total 25 sec of audio can be represented as multi-en-hi)))> : [list of string of texts that have to be generated ]
#     }
# }

async def tts_stream(text) : 

    audio_data = b''

    async for chunk in tts_client(text) : audio_data += base64.b64decode(chunk)

    return audio_data

def mulaw_to_wav(mulaw_data, sample_rate=8000):
    """Convert MULAW audio data to WAV format with proper header"""
    import wave
    import io
    
    # Convert MULAW to linear PCM (16-bit)
    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    
    return wav_buffer.getvalue()

def get_audio_duration(mulaw_data, sample_rate=8000) : 
    """Calculate duration from MULAW audio data"""
    # Each MULAW sample is 1 byte, so length of data = number of samples
    num_samples = len(mulaw_data)
    duration = num_samples / float(sample_rate)
    return duration

def clean_output_directories():
    """Clear the CSV file and audio files folder before generating new files"""
    
    audio_folder = 'assets/audio_files'
    csv_file = 'assets/data.csv'
    
    # Remove and recreate audio files folder
    if os.path.exists(audio_folder):
        shutil.rmtree(audio_folder)
    os.makedirs(audio_folder, exist_ok=True)
    
    # Remove CSV file if it exists
    if os.path.exists(csv_file):
        os.remove(csv_file)
    
    print("✓ Cleaned audio folder and CSV file")

async def generate_audio_files() : 

    # Clean output directories before starting
    clean_output_directories()

    os.makedirs('assets/audio_files' , exist_ok = True)
    os.makedirs('assets' , exist_ok = True)

    csv_file = 'assets/data.csv'

    with open(csv_file , 'w' , newline = '' , encoding = 'utf-8') as csvfile : 

        fieldnames = ['filename' , 'text' , 'language' , 'audio_duration' , 'audio_duration_group']
        
        writer = csv.DictWriter(csvfile , fieldnames = fieldnames)

        writer.writeheader()

        for audio_duration in tqdm(input_data.keys() , total = len(list(input_data.keys()))) : 

            audio_duration_languages : dict = input_data[audio_duration]

            for language in tqdm(audio_duration_languages.keys() , total = len(list(audio_duration_languages.keys())) , leave = False) : 

                audio_duration_texts : list = audio_duration_languages[language]

                for text in tqdm(audio_duration_texts , total = len(audio_duration_texts) , leave = False) : 

                    # Get MULAW audio data from stream
                    mulaw_data = await tts_stream(text)

                    # Calculate duration from MULAW data
                    duration = get_audio_duration(mulaw_data, sample_rate=8000)

                    # Convert MULAW to WAV format for saving
                    wav_data = mulaw_to_wav(mulaw_data, sample_rate=8000)

                    filename = f"{uuid.uuid4()}.wav"
                    filepath = os.path.join('assets/audio_files', filename)

                    with open(filepath, 'wb') as f : f.write(wav_data)

                    writer.writerow({
                        'filename' : filename , 
                        'text' : text , 
                        'language' : language , 
                        'audio_duration': duration , 
                        'audio_duration_group' : audio_duration
                    })

                    await asyncio.sleep(0.5)

def main() : asyncio.run(generate_audio_files())

if __name__ == "__main__" : main()