import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    MONGO_URL = os.getenv("MONGO_URL")
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set")
        if not cls.API_ID:
            raise ValueError("API_ID is not set")
        if not cls.API_HASH:
            raise ValueError("API_HASH is not set")
        if not cls.MONGO_URL:
            raise ValueError("MONGO_URL is not set")
