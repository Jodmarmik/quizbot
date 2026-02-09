import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram Bot Configuration
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI")
    DB_NAME = os.getenv("DB_NAME", "quiz_bot")
    
    # Validate required environment variables
    @staticmethod
    def validate():
        required_vars = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGODB_URI"]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Validate configuration on import
Config.validate()
```

# requirements.txt
```
pyrogram==2.0.106
TgCrypto==1.2.5
motor==3.3.2
python-dotenv==1.0.0
pandas==2.1.4
dnspython==2.4.2
```

# Procfile
```
worker: python main.py
```

# .env.example
```
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=quiz_bot
