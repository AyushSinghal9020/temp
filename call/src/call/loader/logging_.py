from logging import (
    Logger , getLogger , StreamHandler , Formatter , 
    DEBUG , INFO , WARNING , ERROR , CRITICAL , 
    LogRecord
)

class ColoredFormatter(Formatter) : 

    def __init__(
        self , 
        fmt : str , 
        color_config : dict , 
        datefmt : str | None = None
    ) -> None :

        super().__init__(fmt , datefmt)

        self.fmt = fmt

        self.colors = {
            DEBUG : color_config['debug'] ,
            INFO : color_config['info'] , 
            WARNING : color_config['warning'] , 
            ERROR : color_config['error'] , 
            CRITICAL : color_config['critical']
        }
        self.reset = color_config['reset']

    def format(self , record : LogRecord) -> str : 

        color = self.colors.get(record.levelno)

        if color : log_fmt = color + self.fmt + self.reset
        else : log_fmt = self.fmt

        formatter = Formatter(log_fmt , self.datefmt)

        return formatter.format(record)

def load_logger(config : dict) -> Logger:
    
    logger: Logger = getLogger(__name__)
    logger.setLevel(DEBUG) 

    if logger.handlers : 

        for handler in logger.handlers : logger.removeHandler(handler)

    console_handler : StreamHandler = StreamHandler()

    formatter : ColoredFormatter = ColoredFormatter(
        fmt = config['format'] , 
        color_config = config['colors'] , 
        datefmt = config['date-time-format']
    )

    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger