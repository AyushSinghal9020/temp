import numpy as np 

from numpy import ndarray , float32

from .event import EVENT

class MEDIA_EVENT(EVENT) : 

    def __init__(
        self , 
        sequenceNumber : int , 
        streamId : str , 
        media : dict , 
        event : str , 
        **kwargs
    ) -> None : 

        super().__init__()

        self.sequence_number : int = sequenceNumber 
        self.stream_id : str = streamId

        self.track : str = media['track']
        self.timestamp : str = media['timestamp']
        self.chunk : int = media['chunk']
        self.payload : str = media['payload']

        self.audio_nd_array : ndarray = self.base64audio_to_ndarray(base64_audio = self.payload)
        self.audio_bytes : bytes = self.base64_audio_to_bytes(base64_audio = self.payload)
        # self.reduced_noise : ndarray = self.reduce_noise(
        #     audio_nd_array = self.audio_nd_array , 
        #     sample_rate = 16_000 # ! make it dependent on the start 
        # )

        self.reduced_noise : ndarray = self.audio_nd_array

        self.find_variance()

    def find_variance(self) -> None : 

        self.variance : float32 = np.std(self.reduced_noise)

        self.possiblity : bool = bool(self.variance >= 0.01)

        # if self.possiblity : print(f'User said something , confidence : {self.variance}')