class TTS : 
    '''
    Base class for Text-to-Speech (TTS) services.

    This class provides a method to calculate the duration of audio based on its byte size, sample rate, number of channels, and bytes per sample.

    Methods:
        - calculate_audio_duration(num_bytes: int, sample_rate: int, num_channels: int, bytes_per_sample: int) -> float:
            Calculates the duration of audio in seconds based on the provided parameters.

    Attributes:
        - None

    Args:
        - None
    '''

    def __init__(self) -> None : pass

    async def calculate_audio_duration(
        self , 
        num_bytes : int , 
        sample_rate : int , 
        num_channels : int , 
        bytes_per_sample : int 
    ) -> float : 

        duration_seconds : float = (
            num_bytes / 
            (
                sample_rate * 
                num_channels * 
                bytes_per_sample
            )
        )

        return duration_seconds