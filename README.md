# Telegram Quiz Bot

A fully-featured Telegram quiz bot built with Pyrogram, supporting multiple quiz formats, real-time scoring, and leaderboards.

## Features

- ✅ Create quizzes via CSV, TXT, or direct text input
- ✅ Native Telegram quiz polls with timers
- ✅ Real-time scoring and leaderboards
- ✅ Multi-user support in groups and DMs
- ✅ Prevent duplicate quiz attempts
- ✅ Admin controls (cancel, status, delete)
- ✅ MongoDB persistence
- ✅ Async-safe implementation
- ✅ Heroku deployment ready

## Tech Stack

- Python 3.11
- Pyrogram (async Telegram client)
- MongoDB (Motor driver)
- python-dotenv
- pandas

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- MongoDB Atlas account (free tier works)
- Telegram Bot Token (from @BotFather)
- Telegram API credentials (from https://my.telegram.org)

### 2. Local Development
```bash
# Clone repository
git clone <your-repo-url>
cd quiz-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Environment Variables

Create a `.env` file with the following:
```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
BOT_TOKEN=your_bot_token_from_botfather
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=quiz_bot
```

**Getting Credentials:**

1. **API_ID & API_HASH**: Visit https://my.telegram.org/apps
2. **BOT_TOKEN**: Message @BotFather on Telegram and create a new bot
3. **MONGODB_URI**: Create a free cluster at https://www.mongodb.com/cloud/atlas

### 4. Run Locally
```bash
python main.py
```

## Heroku Deployment

### 1. Install Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Ubuntu
curl https://cli-assets.heroku.com/install.sh | sh
```

### 2. Deploy to Heroku
```bash
# Login to Heroku
heroku login

# Create new app
heroku create your-quiz-bot

# Set environment variables
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set MONGODB_URI=your_mongodb_uri
heroku config:set DB_NAME=quiz_bot

# Deploy
git push heroku main

# Scale worker dyno
heroku ps:scale worker=1

# Check logs
heroku logs --tail
```

### 3. Important Notes for Heroku

- The bot uses a **worker** dyno (not web)
- Ensure `Procfile` specifies: `worker: python main.py`
- Free tier gives 550 hours/month (sufficient for one bot)
- Add credit card to Heroku for 1000 hours/month free

## Quiz Creation Formats

### CSV Format
```csv
question,option1,option2,option3,option4,correct,explanation
What is 2+2?,3,4,5,6,1,Basic arithmetic
Capital of France?,London,Paris,Berlin,Rome,1,Paris is the capital
```

### Text Format
```
Q: What is the capital of India?
A) Mumbai
B) New Delhi
C) Kolkata
D) Chennai
Correct: B
Explanation: New Delhi is the capital city

Q: Who wrote "Hamlet"?
A) Charles Dickens
B) William Shakespeare
C) Mark Twain
D) Jane Austen
Correct: B
Explanation: Shakespeare wrote Hamlet
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/createquiz` | Create a new quiz |
| `/startquiz <quiz_id>` | Start a quiz |
| `/cancelquiz` | Cancel active quiz |
| `/quizstatus` | Check active quizzes |
| `/deletequiz <quiz_id>` | Delete your quiz |

## Usage Flow

1. **Create Quiz**: Send `/createquiz` in bot DM
2. **Upload Data**: Send CSV/TXT file or paste text
3. **Configure**: Provide title and timer duration
4. **Get Quiz ID**: Bot returns unique quiz ID
5. **Start Quiz**: Use `/startquiz <quiz_id>` in group or DM
6. **Participate**: Users answer via Telegram quiz polls
7. **Auto-Progress**: Bot moves to next question after timer
8. **View Results**: Leaderboard sent when quiz ends

## Database Schema

### Quizzes Collection
```json
{
  "_id": "quiz_id",
  "title": "Quiz Title",
  "questions": [...],
  "timer": 20,
  "creator_id": 12345,
  "created_at": "2025-02-09T..."
}
```

### Scores Collection
```json
{
  "user_id": 12345,
  "user_name": "John",
  "quiz_id": "quiz_id",
  "chat_id": 67890,
  "correct": 8,
  "wrong": 2,
  "accuracy": 80.0,
  "timestamp": "2025-02-09T..."
}
```

## Troubleshooting

### Bot not responding
```bash
# Check Heroku logs
heroku logs --tail

# Restart dyno
heroku restart
```

### Database connection issues

- Verify MongoDB URI is correct
- Ensure IP whitelist allows all IPs (0.0.0.0/0) in MongoDB Atlas
- Check database user permissions

### Poll not working

- Ensure bot has admin rights in groups
- Check if quiz session is active with `/quizstatus`

## Development

### Project Structure
```
quiz-bot/
├── main.py           # Main bot logic
├── config.py         # Configuration management
├── requirements.txt  # Python dependencies
├── Procfile         # Heroku worker configuration
├── .env             # Environment variables (gitignored)
├── .env.example     # Example env file
└── README.md        # Documentation
```

### Adding Features

1. Create new command handler in `main.py`
2. Add database operations if needed
3. Test locally before deploying
4. Push to Heroku: `git push heroku main`

## Security

- Never commit `.env` file
- Use environment variables for all secrets
- Restrict MongoDB access to specific IPs in production
- Regularly rotate API tokens

## License

MIT License - Feel free to modify and distribute

## Support

For issues or questions:
1. Check logs: `heroku logs --tail`
2. Verify environment variables: `heroku config`
3. Test locally first
4. Open GitHub issue with error details

## Credits

Built with:
- [Pyrogram](https://docs.pyrogram.org/)
- [MongoDB Motor](https://motor.readthedocs.io/)
- [Heroku](https://www.heroku.com/)

---

**Ready to deploy!** Follow the setup instructions and your quiz bot will be live in minutes.
```

# .gitignore
```
# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# Pyrogram session
*.session
*.session-journal

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log

# OS
.DS_Store
Thumbs.db

# Heroku
.heroku/
