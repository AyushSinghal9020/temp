from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

def load_fastapi_app(config : dict) -> FastAPI : 
    '''
    Load the FastAPI configuration from the provided dictionary.

    Args :
        - config (dict): Configuration dictionary containing FastAPI settings.

    Returns :
        - dict: A dictionary containing FastAPI configuration settings.
    '''

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware , 
        allow_origins = config['cors']['allow-origins'] , 
        allow_credentials = config['cors']['allow-credentials'] , 
        allow_methods = config['cors']['allow-methods'] , 
        allow_headers = config['cors']['allow-headers']
    )

    return app
