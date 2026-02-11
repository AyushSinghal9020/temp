import asyncio
import time
# from tts.src.tts import SMALLESTAI_TTS
from tts import SMALLESTAI_TTS

from dotenv import load_dotenv 

load_dotenv('../../.env')

tts_client : SMALLESTAI_TTS = SMALLESTAI_TTS(config = {})

async def run() : 

    start_time : float = time.time()

    async for audio in tts_client.stream('Hello') : 

        print(time.time() - start_time)

def main() : 

    asyncio.run(run())