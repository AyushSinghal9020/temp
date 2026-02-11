This folder contains the classes and helper functions for different STT Modules 

Currently Supported are 
* STT -> `stt.STT` # ! Base Parent Class
* Google STT -> `google_.GOOGLE_STT`
* Groq STT -> `groq_.GROQ_STT`

Creating a new class is expected to have this class format 

* The `class` must establish inheritance from the foundational STT Class
* The `__init__` constructor method shall be responsible for the initialization and instantiation of the `client` object
* The `transcribe` method (asynchronous implementation preferred) shall encapsulate the transcription logic and yield both `transcription` and `language` parameters. In circumstances where the function lacks the language identification capabilities, the method shall return an empty string as the language parameter
* The `__call__` method (asynchronous implementation preferred) shall serve as a delegating interface, invoking the `transcription` method in turn

```py

class Any_custom_STT(STT) : 

    def __init__(
        self , 
        config : dict
    ) -> None : 

        self.config : dict = config 
        self.client : <clientclass> = clientclass()

        print(f'Any custom STT Initialized with config : {self.config}')

    async def transcribe(
        self , 
        buffer_stream : bytes
    ) -> Tuple[str , str] : 

        ###############################
        ##### Transcription Logic #####
        ###############################

        async def __call__(
        self , 
        buffer_stream : bytes
    ) -> Tuple[str , str] : 

        return await self.transcribe(buffer_stream = buffer_stream) 
```