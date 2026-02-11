This folder contains the classes and helper functions for different TTS Modules 

Currently Supported are 
* TTS -> `TTS.TTS` # ! Base Parent Class
* Google TTS -> `google_.GOOGLE_TTS`


Creating a new class is expected to have this class format 

* The `class` must establish inheritance from the foundational TTS Class
* The `__init__` constructor method shall be responsible for the initialization and instantiation of the `client` object
* The `stream` method (asynchronous implementation preferred) shall `yield` / `stream` the audio in `base64 format`
* The `__call__` method (asynchronous implementation preferred) shall serve as a delegating interface, invoking the `stream` method in turn

```py

class Any_custom_TTS(TTS) : 

    def __init__(
        self , 
        config : dict
    ) -> None : 

        self.config : dict = config 
        self.client : <clientclass> = clientclass()

        print(f'Any custom TTS Initialized with config : {self.config}')

    async def stream(
        self , 
        text : str
    ) : 

        ###############################
        ###### TTS Stream Logic #######
        ###############################

        async def __call__(
        self , 
        text : str
    ) : 

        return await self.transcribe(text = text) 
```