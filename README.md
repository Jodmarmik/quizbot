# 🎯 Advanced Telegram Quiz Bot

A production-ready Telegram Quiz Bot built with Pyrogram, MongoDB, and Docker. Supports CSV/TXT file uploads, multiple simultaneous quizzes, real-time scoring, and automatic leaderboards.

## ✨ Features

- 📁 **Multiple Input Methods**: CSV file, TXT file, or direct text paste
- ⏱️ **Configurable Timers**: 10s, 20s, 30s, or custom time per question
- 👥 **Multi-User Support**: Multiple users can participate simultaneously
- 🏆 **Auto Leaderboards**: Rankings by score and accuracy
- 🔄 **Concurrent Quizzes**: Run multiple quizzes in different chats
- 🛡️ **Error Handling**: Robust validation and error recovery
- 📊 **Analytics**: Track scores, accuracy, and participant stats

## 📋 Requirements

- Python 3.11+
- MongoDB database
- Telegram Bot Token
- Telegram API credentials (API_ID, API_HASH)

## 🚀 Quick Setup

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd telegram-quiz-bot
```

### 2. Environment Variables

Create a `.env` file:
```env
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id_here
API_HASH=your_api_hash_here
MONGO_URL=mongodb://username:password@host:port/database
```

### 3. Local Development
```bash
pip install -r requirements.txt
python main.py
```

## 🐳 Docker Deployment

### Local Docker
```bash
docker build -t quiz-bot .
docker run --env-file .env quiz-bot
```

### Heroku Container Deployment

#### Prerequisites
- Heroku CLI installed
- Heroku account
- MongoDB Atlas account (free tier available)

#### Steps

1. **Login to Heroku**
```bash
heroku login
```

2. **Create Heroku App**
```bash
heroku create your-quiz-bot-name
```

3. **Set Environment Variables**
```bash
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set MONGO_URL=your_mongodb_connection_string
```

4. **Login to Container Registry**
```bash
heroku container:login
```

5. **Deploy**
```bash
git push heroku main
```

Heroku will automatically:
- Detect `heroku.yml`
- Build Docker container
- Deploy to Heroku dynos

6. **Scale Dyno**
```bash
heroku ps:scale web=1
```

7. **View Logs**
```bash
heroku logs --tail
```

## 📝 Quiz File Format

### CSV Format
```csv
What is 2+2?,3,4,5,6,1,Basic arithmetic
Capital of France?,Berlin,Paris,Rome,Madrid,1,Geography question
```

### TXT Format
```
What is 2+2? | 3 | 4 | 5 | 6 | 1 | Basic arithmetic
Capital of France? | Berlin | Paris | Rome | Madrid | 1 | Geography question
```

### Format Specification
```
Question | Option A | Option B | Option C | Option D | Correct Index (0-3) | Explanation (optional)
```

**Rules:**
- Correct option index: 0 = Option A, 1 = Option B, 2 = Option C, 3 = Option D
- Question: 5-300 characters
- Each option: 1-100 characters
- Explanation: 0-200 characters (optional)
- Maximum 100 questions per quiz

## 🎮 Bot Commands

### User Commands
- `/start` - Welcome message and help
- `/createquiz` - Create new quiz (DM only)
- `/startquiz <quiz_id>` - Start a quiz
- `/quizstatus` - View active quizzes
- `/cancelquiz` - Cancel running quiz in current chat
- `/deletequiz <quiz_id>` - Delete your quiz (DM only)

## 📊 How It Works

### Quiz Creation Flow
1. User sends `/createquiz`
2. Selects input method (CSV/TXT/Paste)
3. Uploads file or pastes text
4. Bot validates and parses questions
5. User enters quiz name
6. User selects time per question
7. Bot generates unique quiz ID
8. Quiz saved to MongoDB

### Quiz Execution Flow
1. User sends `/startquiz <quiz_id>` in group or DM
2. Bot validates quiz and checks for existing quiz
3. Questions sent as Telegram native quiz polls
4. Timer automatically moves to next question
5. Bot tracks answers in real-time
6. After last question, results are saved
7. Leaderboard automatically sent

### Scoring System
- **Score**: Number of correct answers
- **Accuracy**: (Correct / Total Questions) × 100
- **Ranking**: Sorted by score (primary), then accuracy (secondary)

## 🗄️ MongoDB Collections

### quizzes
```javascript
{
  quiz_id: String,
  creator_id: Number,
  name: String,
  questions: Array,
  time_per_question: Number,
  created_at: Date
}
```

### results
```javascript
{
  quiz_id: String,
  chat_id: Number,
  user_id: Number,
  first_name: String,
  correct: Number,
  wrong: Number,
  total: Number,
  accuracy: Number,
  completed_at: Date
}
```

## 🛡️ Error Handling

The bot handles:
- Invalid quiz IDs
- Quiz already running in chat
- User already attempted quiz
- Invalid file formats
- Malformed question data
- MongoDB connection failures
- Poll sending errors
- Concurrent quiz conflicts

## 📱 Supported Chat Types

- ✅ Private chats (DMs)
- ✅ Groups
- ✅ Supergroups

**Note**: Quiz creation only works in private chats for security.

## 🔒 Security Features

- Quiz creators can only delete their own quizzes
- One attempt per user per quiz
- Input validation on all user data
- Safe concurrent quiz handling
- MongoDB injection prevention

## 🐛 Troubleshooting

### Bot Not Responding
```bash
heroku logs --tail
```

### Database Connection Issues
- Verify MONGO_URL is correct
- Check MongoDB Atlas whitelist (allow 0.0.0.0/0 for Heroku)
- Ensure database user has read/write permissions

### Quiz Not Starting
- Verify quiz_id is correct
- Check if another quiz is running
- Ensure bot has permission to send polls

## 📄 License

MIT License - feel free to use and modify.

## 🤝 Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- All features tested
- Environment variables documented

## 📞 Support

For issues or questions:
1. Check logs: `heroku logs --tail`
2. Review error messages in chat
3. Verify environment variables
4. Check MongoDB connection

## 🎯 Example Quiz
```
What is the capital of Japan? | Beijing | Tokyo | Seoul | Bangkok | 1 | Tokyo is Japan's capital
Who painted the Mona Lisa? | Van Gogh | Da Vinci | Picasso | Monet | 1 | Leonardo da Vinci painted it
What is 10 + 15? | 20 | 25 | 30 | 35 | 1 | Simple addition
```

---

**Built with ❤️ using Pyrogram, MongoDB, and Docker**
```

===== .gitignore =====
```
__pycache__/
*.py[cod]
*$py.class

*.so

.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/

*.log

.DS_Store
.AppleDouble
.LSOverride

Thumbs.db
ehthumbs.db
Desktop.ini

*.session
*.session-journal

.idea/
.vscode/
*.swp
*.swo
*~

heroku.yml
Dockerfile
