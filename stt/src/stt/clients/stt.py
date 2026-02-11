import io 
import wave
from io import BytesIO


class STT : 
    
    def __init__(self) -> None : 
        '''
        Initialize the STT class.
        '''
        pass

    
    async def save_file(
        self , 
        buffer_stream : bytes , 
        num_channels : int , 
        width : int , 
        sample_rate : int , 
        file_name : str 
    ) -> str : 
        '''
        Save the audio buffer stream to a WAV file.

        Args:

            - buffer_stream (bytes): The audio data to save.
            - num_channels (int): Number of audio channels.
            - width (int): Sample width in bytes.
            - sample_rate (int): Sample rate of the audio.
            - file_name (str): The name of the file to save the audio data to.

        Returns:

            - str
        '''

        audio_bytes = io.BytesIO()

        with wave.open(audio_bytes , 'wb') as wf : 
        
            wf.setnchannels(num_channels)
            wf.setsampwidth(width)
            wf.setframerate(sample_rate) 
            wf.writeframes(buffer_stream)

        audio_bytes.seek(0)

        with open(file_name , 'wb') as wave_file : wave_file.write(audio_bytes.getvalue())

        return file_name

