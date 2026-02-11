class START_EVENT : 

    def __init__(
        self , 
        sequenceNumber : int , 
        start : dict , 
        event : str , 
        **kwargs
    ) -> None : 

        self.supported_audio_encodings : list[str] = ['audio/x-l16']
        self.supported_sample_rate : list[int] = [16_000]

        self.call_id : str = start['callId']

        self.stream_id : str = start['streamId']
        self.account_id : str = start['accountId']

        self.tracks : list = start['tracks']

        self.media_format : dict = start['mediaFormat']

        if self.media_format['encoding'] not in self.supported_audio_encodings : raise ValueError(f'Media Format : "{self.media_format['encoding']}" not supported , supported formats include : "{self.supported_audio_encodings}"')
        if self.media_format['sampleRate'] not in self.supported_sample_rate : raise ValueError(f'Sample Rate : "{self.media_format['sampleRate']}" not supported , supported formats include : {self.supported_sample_rate}')

        print('Stream Started')