from .event import EVENT 

class PLAYED_EVENT(EVENT) : 

    def __init__(
        self , 
        event : str , 
        sequenceNumber : int , 
        streamId : str , 
        name : str
    ) -> None : 

        self.sequence_number : int = sequenceNumber 
        self.stream_id : str = streamId
        self.name : str = name 

        print(f'Received Played Event : {name}')