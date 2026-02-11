from .event import EVENT

class CLEAR_EVENT(EVENT) : 

    def __init__(
        self , 
        sequenceNumber : int , 
        streamId : str , 
        event : str
    ) -> None : 

        self.sequence_number : int = sequenceNumber
        self.stream_id : str = streamId
        self.event : str = event

        print(f'Audio Clear event received')