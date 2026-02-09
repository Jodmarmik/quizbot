import os
import asyncio
import csv
import io
import re
from datetime import datetime
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, PollAnswer
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import logging
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Pyrogram Client
app = Client(
    "quiz_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# MongoDB Setup
mongo_client = AsyncIOMotorClient(Config.MONGODB_URI)
db = mongo_client[Config.DB_NAME]
quizzes_collection = db["quizzes"]
scores_collection = db["scores"]
active_quizzes_collection = db["active_quizzes"]

# In-memory storage for active quiz sessions
active_quiz_sessions: Dict[str, Dict] = {}


class QuizQuestion:
    def __init__(self, question: str, options: List[str], correct_option: int, explanation: str = ""):
        self.question = question
        self.options = options
        self.correct_option = correct_option
        self.explanation = explanation


class Quiz:
    def __init__(self, quiz_id: str, title: str, questions: List[QuizQuestion], timer: int, creator_id: int):
        self.quiz_id = quiz_id
        self.title = title
        self.questions = questions
        self.timer = timer
        self.creator_id = creator_id
        self.created_at = datetime.utcnow()


class QuizSession:
    def __init__(self, quiz: Quiz, chat_id: int, starter_id: int):
        self.quiz = quiz
        self.chat_id = chat_id
        self.starter_id = starter_id
        self.current_question_index = 0
        self.participants: Dict[int, Dict] = {}  # user_id: {name, correct, wrong, answers: {q_index: answer}}
        self.current_poll_id: Optional[str] = None
        self.current_poll_message_id: Optional[int] = None
        self.is_active = True
        self.timer_task: Optional[asyncio.Task] = None
        self.answered_users: set = set()


def parse_csv_content(content: str) -> List[QuizQuestion]:
    """Parse CSV content into QuizQuestion objects"""
    questions = []
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        question_text = row.get('question', '').strip()
        option1 = row.get('option1', '').strip()
        option2 = row.get('option2', '').strip()
        option3 = row.get('option3', '').strip()
        option4 = row.get('option4', '').strip()
        correct = int(row.get('correct', 0))
        explanation = row.get('explanation', '').strip()
        
        if question_text and option1 and option2 and option3 and option4:
            questions.append(QuizQuestion(
                question=question_text,
                options=[option1, option2, option3, option4],
                correct_option=correct,
                explanation=explanation
            ))
    
    return questions


def parse_text_content(content: str) -> List[QuizQuestion]:
    """Parse text content into QuizQuestion objects
    Format:
    Q: Question text
    A) Option 1
    B) Option 2
    C) Option 3
    D) Option 4
    Correct: A
    Explanation: Optional explanation
    """
    questions = []
    lines = content.strip().split('\n')
    
    current_question = None
    current_options = []
    current_correct = 0
    current_explanation = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_question and len(current_options) == 4:
                questions.append(QuizQuestion(
                    question=current_question,
                    options=current_options,
                    correct_option=current_correct,
                    explanation=current_explanation
                ))
                current_question = None
                current_options = []
                current_correct = 0
                current_explanation = ""
            continue
        
        if line.startswith('Q:'):
            current_question = line[2:].strip()
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            current_options.append(line[2:].strip())
        elif line.startswith('Correct:'):
            correct_letter = line.split(':', 1)[1].strip().upper()
            correct_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            current_correct = correct_map.get(correct_letter, 0)
        elif line.startswith('Explanation:'):
            current_explanation = line.split(':', 1)[1].strip()
    
    # Add last question if exists
    if current_question and len(current_options) == 4:
        questions.append(QuizQuestion(
            question=current_question,
            options=current_options,
            correct_option=current_correct,
            explanation=current_explanation
        ))
    
    return questions


async def save_quiz_to_db(quiz: Quiz):
    """Save quiz to MongoDB"""
    quiz_data = {
        "_id": quiz.quiz_id,
        "title": quiz.title,
        "questions": [
            {
                "question": q.question,
                "options": q.options,
                "correct_option": q.correct_option,
                "explanation": q.explanation
            } for q in quiz.questions
        ],
        "timer": quiz.timer,
        "creator_id": quiz.creator_id,
        "created_at": quiz.created_at
    }
    await quizzes_collection.insert_one(quiz_data)


async def load_quiz_from_db(quiz_id: str) -> Optional[Quiz]:
    """Load quiz from MongoDB"""
    quiz_data = await quizzes_collection.find_one({"_id": quiz_id})
    if not quiz_data:
        return None
    
    questions = [
        QuizQuestion(
            question=q["question"],
            options=q["options"],
            correct_option=q["correct_option"],
            explanation=q.get("explanation", "")
        ) for q in quiz_data["questions"]
    ]
    
    quiz = Quiz(
        quiz_id=quiz_data["_id"],
        title=quiz_data["title"],
        questions=questions,
        timer=quiz_data["timer"],
        creator_id=quiz_data["creator_id"]
    )
    quiz.created_at = quiz_data["created_at"]
    
    return quiz


async def delete_quiz_from_db(quiz_id: str):
    """Delete quiz from MongoDB"""
    await quizzes_collection.delete_one({"_id": quiz_id})


async def save_score(user_id: int, user_name: str, quiz_id: str, correct: int, wrong: int, accuracy: float, chat_id: int):
    """Save user score to MongoDB"""
    score_data = {
        "user_id": user_id,
        "user_name": user_name,
        "quiz_id": quiz_id,
        "chat_id": chat_id,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
        "timestamp": datetime.utcnow()
    }
    await scores_collection.insert_one(score_data)


async def check_duplicate_attempt(user_id: int, quiz_id: str, chat_id: int) -> bool:
    """Check if user already attempted this quiz in this chat"""
    existing = await scores_collection.find_one({
        "user_id": user_id,
        "quiz_id": quiz_id,
        "chat_id": chat_id
    })
    return existing is not None


async def get_leaderboard(quiz_id: str, chat_id: int) -> List[Dict]:
    """Get leaderboard for a quiz in a specific chat"""
    cursor = scores_collection.find({"quiz_id": quiz_id, "chat_id": chat_id})
    scores = await cursor.to_list(length=None)
    
    # Sort by correct answers (descending), then by accuracy (descending)
    sorted_scores = sorted(scores, key=lambda x: (x['correct'], x['accuracy']), reverse=True)
    
    return sorted_scores


async def send_next_question(session: QuizSession):
    """Send the next question in the quiz"""
    if session.current_question_index >= len(session.quiz.questions):
        await end_quiz(session)
        return
    
    # Reset answered users for new question
    session.answered_users.clear()
    
    question = session.quiz.questions[session.current_question_index]
    
    try:
        # Send poll
        poll_message = await app.send_poll(
            chat_id=session.chat_id,
            question=f"Q{session.current_question_index + 1}: {question.question}",
            options=question.options,
            type="quiz",
            correct_option_id=question.correct_option,
            explanation=question.explanation if question.explanation else None,
            is_anonymous=False
        )
        
        session.current_poll_id = poll_message.poll.id
        session.current_poll_message_id = poll_message.id
        
        # Start timer
        session.timer_task = asyncio.create_task(
            question_timer(session, session.quiz.timer)
        )
        
    except Exception as e:
        logger.error(f"Error sending question: {e}")
        await app.send_message(session.chat_id, "❌ Error sending question. Quiz cancelled.")
        session.is_active = False


async def question_timer(session: QuizSession, duration: int):
    """Timer for each question"""
    try:
        await asyncio.sleep(duration)
        
        if session.is_active and session.current_poll_id:
            # Stop the poll
            try:
                await app.stop_poll(session.chat_id, session.current_poll_message_id)
            except Exception as e:
                logger.error(f"Error stopping poll: {e}")
            
            # Move to next question
            session.current_question_index += 1
            await send_next_question(session)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Timer error: {e}")


async def end_quiz(session: QuizSession):
    """End the quiz and show leaderboard"""
    session.is_active = False
    
    # Cancel timer if running
    if session.timer_task and not session.timer_task.done():
        session.timer_task.cancel()
    
    # Save all scores
    for user_id, data in session.participants.items():
        correct = data['correct']
        wrong = data['wrong']
        total = correct + wrong
        accuracy = (correct / total * 100) if total > 0 else 0
        
        await save_score(
            user_id=user_id,
            user_name=data['name'],
            quiz_id=session.quiz.quiz_id,
            correct=correct,
            wrong=wrong,
            accuracy=accuracy,
            chat_id=session.chat_id
        )
    
    # Generate leaderboard
    leaderboard = await get_leaderboard(session.quiz.quiz_id, session.chat_id)
    
    leaderboard_text = f"🏆 **Quiz Ended: {session.quiz.title}**\n\n"
    leaderboard_text += "**📊 LEADERBOARD**\n"
    leaderboard_text += "━━━━━━━━━━━━━━━━━\n"
    
    if leaderboard:
        for idx, score in enumerate(leaderboard, 1):
            leaderboard_text += f"{idx}. **{score['user_name']}** – {score['correct']} correct – {score['accuracy']:.1f}%\n"
    else:
        leaderboard_text += "No participants\n"
    
    leaderboard_text += "━━━━━━━━━━━━━━━━━"
    
    try:
        await app.send_message(session.chat_id, leaderboard_text)
    except Exception as e:
        logger.error(f"Error sending leaderboard: {e}")
    
    # Remove from active sessions
    session_key = f"{session.chat_id}_{session.quiz.quiz_id}"
    if session_key in active_quiz_sessions:
        del active_quiz_sessions[session_key]


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    welcome_text = """
👋 **Welcome to Quiz Bot!**

I can help you create and run interactive quizzes in groups and DMs.

**Commands:**
📝 /createquiz - Create a new quiz
🎯 /startquiz <quiz_id> - Start a quiz
❌ /cancelquiz - Cancel active quiz
📊 /quizstatus - Check active quizzes
🗑 /deletequiz <quiz_id> - Delete a quiz

**Quiz Creation Formats:**

**CSV Format:**
question,option1,option2,option3,option4,correct,explanation

**Text Format:**
Q: Your question?
A) Option 1
B) Option 2
C) Option 3
D) Option 4
Correct: A
Explanation: Optional

Send me a file or text to create a quiz!
    """
    await message.reply_text(welcome_text)


@app.on_message(filters.command("createquiz") & filters.private)
async def create_quiz_command(client: Client, message: Message):
    """Handle /createquiz command"""
    instructions = """
📝 **Create a New Quiz**

Send me your quiz in one of these formats:

**1. CSV File (.csv)**
Format: question,option1,option2,option3,option4,correct,explanation

**2. Text File (.txt)**
Format:
Q: Question text
A) Option 1
B) Option 2
C) Option 3
D) Option 4
Correct: A
Explanation: Optional explanation

**3. Direct Text**
Paste the quiz in text format directly.

After sending the quiz, I'll ask for:
- Quiz title
- Timer per question (seconds)

Ready? Send your quiz data!
    """
    await message.reply_text(instructions)


@app.on_message(filters.private & (filters.document | filters.text) & ~filters.command(["start", "createquiz", "startquiz", "cancelquiz", "quizstatus", "deletequiz"]))
async def handle_quiz_input(client: Client, message: Message):
    """Handle quiz creation input"""
    questions = []
    
    try:
        # Handle document
        if message.document:
            file_name = message.document.file_name.lower()
            
            if not (file_name.endswith('.csv') or file_name.endswith('.txt')):
                await message.reply_text("❌ Please send a .csv or .txt file.")
                return
            
            # Download file
            file_path = await message.download()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Delete downloaded file
            os.remove(file_path)
            
            # Parse based on extension
            if file_name.endswith('.csv'):
                questions = parse_csv_content(content)
            else:
                questions = parse_text_content(content)
        
        # Handle text
        elif message.text:
            questions = parse_text_content(message.text)
        
        if not questions:
            await message.reply_text("❌ No valid questions found. Please check the format.")
            return
        
        # Store questions temporarily
        user_id = message.from_user.id
        active_quiz_sessions[f"create_{user_id}"] = {
            "questions": questions,
            "step": "title"
        }
        
        await message.reply_text(f"✅ Parsed {len(questions)} questions!\n\nNow send me the **quiz title**:")
        
    except Exception as e:
        logger.error(f"Error parsing quiz: {e}")
        await message.reply_text(f"❌ Error parsing quiz: {str(e)}")


@app.on_message(filters.private & filters.text)
async def handle_quiz_creation_steps(client: Client, message: Message):
    """Handle quiz creation steps (title, timer)"""
    user_id = message.from_user.id
    session_key = f"create_{user_id}"
    
    if session_key not in active_quiz_sessions:
        return
    
    session = active_quiz_sessions[session_key]
    
    # Get title
    if session.get("step") == "title":
        session["title"] = message.text.strip()
        session["step"] = "timer"
        await message.reply_text("Great! Now send the **timer per question** in seconds (e.g., 10, 20, 30):")
        return
    
    # Get timer
    elif session.get("step") == "timer":
        try:
            timer = int(message.text.strip())
            if timer < 5 or timer > 300:
                await message.reply_text("❌ Timer must be between 5 and 300 seconds.")
                return
            
            # Create quiz
            quiz_id = str(ObjectId())
            questions_obj = [
                QuizQuestion(q.question, q.options, q.correct_option, q.explanation)
                for q in session["questions"]
            ]
            
            quiz = Quiz(
                quiz_id=quiz_id,
                title=session["title"],
                questions=questions_obj,
                timer=timer,
                creator_id=user_id
            )
            
            # Save to database
            await save_quiz_to_db(quiz)
            
            # Clean up session
            del active_quiz_sessions[session_key]
            
            success_message = f"""
✅ **Quiz Created Successfully!**

**Quiz ID:** `{quiz_id}`
**Title:** {session['title']}
**Questions:** {len(questions_obj)}
**Timer:** {timer}s per question

To start this quiz, use:
`/startquiz {quiz_id}`

Share this quiz ID with others!
            """
            await message.reply_text(success_message)
            
        except ValueError:
            await message.reply_text("❌ Please send a valid number for the timer.")


@app.on_message(filters.command("startquiz"))
async def start_quiz_command(client: Client, message: Message):
    """Handle /startquiz command"""
    try:
        # Extract quiz ID
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("❌ Usage: /startquiz <quiz_id>")
            return
        
        quiz_id = parts[1].strip()
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Check if quiz already running in this chat
        session_key = f"{chat_id}_{quiz_id}"
        if session_key in active_quiz_sessions:
            await message.reply_text("❌ This quiz is already running in this chat!")
            return
        
        # Load quiz from database
        quiz = await load_quiz_from_db(quiz_id)
        if not quiz:
            await message.reply_text("❌ Quiz not found!")
            return
        
        # Check duplicate attempt
        if await check_duplicate_attempt(user_id, quiz_id, chat_id):
            await message.reply_text("❌ You have already attempted this quiz in this chat!")
            return
        
        # Create quiz session
        session = QuizSession(quiz, chat_id, user_id)
        active_quiz_sessions[session_key] = session
        
        # Send start message
        start_msg = f"""
🎯 **Quiz Started: {quiz.title}**

**Total Questions:** {len(quiz.questions)}
**Timer:** {quiz.timer}s per question
**Format:** Multiple Choice (Quiz Poll)

Get ready! First question coming up...
        """
        await message.reply_text(start_msg)
        
        # Wait a moment then send first question
        await asyncio.sleep(2)
        await send_next_question(session)
        
    except Exception as e:
        logger.error(f"Error starting quiz: {e}")
        await message.reply_text(f"❌ Error starting quiz: {str(e)}")


@app.on_poll_answer()
async def handle_poll_answer(client: Client, poll_answer: PollAnswer):
    """Handle poll answers"""
    try:
        poll_id = poll_answer.poll_id
        user_id = poll_answer.user.id
        user_name = poll_answer.user.first_name
        selected_options = poll_answer.option_ids
        
        # Find the active session for this poll
        session = None
        for sess in active_quiz_sessions.values():
            if isinstance(sess, QuizSession) and sess.current_poll_id == poll_id:
                session = sess
                break
        
        if not session or not session.is_active:
            return
        
        # Check if user already answered this question
        if user_id in session.answered_users:
            return
        
        session.answered_users.add(user_id)
        
        # Initialize participant if new
        if user_id not in session.participants:
            session.participants[user_id] = {
                "name": user_name,
                "correct": 0,
                "wrong": 0,
                "answers": {}
            }
        
        # Check answer
        current_question = session.quiz.questions[session.current_question_index]
        selected_option = selected_options[0] if selected_options else -1
        
        is_correct = selected_option == current_question.correct_option
        
        # Update participant stats
        if is_correct:
            session.participants[user_id]["correct"] += 1
        else:
            session.participants[user_id]["wrong"] += 1
        
        session.participants[user_id]["answers"][session.current_question_index] = selected_option
        
    except Exception as e:
        logger.error(f"Error handling poll answer: {e}")


@app.on_message(filters.command("cancelquiz"))
async def cancel_quiz_command(client: Client, message: Message):
    """Handle /cancelquiz command"""
    chat_id = message.chat.id
    
    # Find active quiz in this chat
    session_to_cancel = None
    session_key_to_delete = None
    
    for key, session in active_quiz_sessions.items():
        if isinstance(session, QuizSession) and session.chat_id == chat_id and session.is_active:
            session_to_cancel = session
            session_key_to_delete = key
            break
    
    if not session_to_cancel:
        await message.reply_text("❌ No active quiz in this chat.")
        return
    
    # Cancel the quiz
    session_to_cancel.is_active = False
    if session_to_cancel.timer_task and not session_to_cancel.timer_task.done():
        session_to_cancel.timer_task.cancel()
    
    # Remove from active sessions
    if session_key_to_delete:
        del active_quiz_sessions[session_key_to_delete]
    
    await message.reply_text("✅ Quiz cancelled successfully.")


@app.on_message(filters.command("quizstatus"))
async def quiz_status_command(client: Client, message: Message):
    """Handle /quizstatus command"""
    chat_id = message.chat.id
    
    active_in_chat = [
        session for session in active_quiz_sessions.values()
        if isinstance(session, QuizSession) and session.chat_id == chat_id and session.is_active
    ]
    
    if not active_in_chat:
        await message.reply_text("📊 No active quizzes in this chat.")
        return
    
    status_text = "📊 **Active Quizzes:**\n\n"
    for session in active_in_chat:
        status_text += f"**{session.quiz.title}**\n"
        status_text += f"Progress: {session.current_question_index + 1}/{len(session.quiz.questions)}\n"
        status_text += f"Participants: {len(session.participants)}\n\n"
    
    await message.reply_text(status_text)


@app.on_message(filters.command("deletequiz"))
async def delete_quiz_command(client: Client, message: Message):
    """Handle /deletequiz command"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("❌ Usage: /deletequiz <quiz_id>")
            return
        
        quiz_id = parts[1].strip()
        user_id = message.from_user.id
        
        # Load quiz to check ownership
        quiz = await load_quiz_from_db(quiz_id)
        if not quiz:
            await message.reply_text("❌ Quiz not found!")
            return
        
        if quiz.creator_id != user_id:
            await message.reply_text("❌ You can only delete quizzes you created!")
            return
        
        # Delete quiz
        await delete_quiz_from_db(quiz_id)
        await message.reply_text(f"✅ Quiz '{quiz.title}' deleted successfully!")
        
    except Exception as e:
        logger.error(f"Error deleting quiz: {e}")
        await message.reply_text(f"❌ Error deleting quiz: {str(e)}")


if __name__ == "__main__":
    logger.info("Starting Quiz Bot...")
    app.run()
