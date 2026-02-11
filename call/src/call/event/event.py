import base64

import numpy as np
import noisereduce as nr

from numpy import ndarray 

class EVENT : 

    def __init__(self) -> None : pass

    def base64audio_to_ndarray(self , base64_audio : str) -> ndarray : 

        try : 

            audio_bytes : bytes = self.base64_audio_to_bytes(base64_audio = base64_audio)

            audio_data : ndarray = np.frombuffer(audio_bytes , dtype = np.int16)

            audio_data = audio_data.astype(np.float32) / 32768.0

            return audio_data

        except Exception as e : raise ValueError(f'Received corrupt audio: {e}')

    def reduce_noise(
        self , 
        audio_nd_array : ndarray , 
        sample_rate : int 
    ) -> ndarray : 

        reduced_audio_nd_array : ndarray = nr.reduce_noise(
            y = audio_nd_array , 
            sr = sample_rate
        )

        return reduced_audio_nd_array

    def base64_audio_to_bytes(self , base64_audio : str) -> bytes : 

        audio_bytes : bytes = base64.b64decode(base64_audio)

        return audio_bytes