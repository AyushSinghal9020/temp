import asyncio
from .server import serve

def main():
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("Server stopped by user.")

if __name__ == "__main__":
    main()