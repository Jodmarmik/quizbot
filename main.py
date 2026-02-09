import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ParseMode
from config import Config
from database import Database
from quiz_manager import QuizManager
from utils import parse_quiz_file, validate_quiz_data
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client(
    "quiz_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

db = Database()
quiz_manager = QuizManager(app, db)

user_states = {}


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "**🎯 Welcome to Advanced Quiz Bot!**\n\n"
        "**Available Commands:**\n"
        "• /createquiz - Create a new quiz\n"
        "• /startquiz <quiz_id> - Start a quiz\n"
        "• /quizstatus - View active quizzes\n"
        "• /cancelquiz - Cancel running quiz\n"
        "• /deletequiz <quiz_id> - Delete a quiz\n\n"
        "**Quiz File Format:**\n"
        "`Question | Option A | Option B | Option C | Option D | Correct Index (0-3) | Explanation`",
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("createquiz") & filters.private)
async def create_quiz_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = {"step": "select_method"}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Upload CSV File", callback_data="method_csv")],
        [InlineKeyboardButton("📝 Upload TXT File", callback_data="method_txt")],
        [InlineKeyboardButton("✍️ Paste Text Directly", callback_data="method_paste")]
    ])
    
    await message.reply_text(
        "**📋 Create New Quiz**\n\n"
        "Choose your input method:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_callback_query(filters.regex("^method_"))
async def method_selection(client: Client, callback_query):
    user_id = callback_query.from_user.id
    method = callback_query.data.split("_")[1]
    
    user_states[user_id] = {"step": "awaiting_data", "method": method}
    
    if method in ["csv", "txt"]:
        await callback_query.message.edit_text(
            f"**📤 Upload your {method.upper()} file**\n\n"
            "**Expected Format:**\n"
            "`Question | Option A | Option B | Option C | Option D | Correct Index (0-3) | Explanation`\n\n"
            "**Example:**\n"
            "`What is 2+2? | 3 | 4 | 5 | 6 | 1 | Basic arithmetic`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback_query.message.edit_text(
            "**✍️ Paste your quiz text**\n\n"
            "**Format (one question per line):**\n"
            "`Question | Option A | Option B | Option C | Option D | Correct Index (0-3) | Explanation`\n\n"
            "**Example:**\n"
            "`What is 2+2? | 3 | 4 | 5 | 6 | 1 | Basic arithmetic`\n"
            "`Capital of France? | Berlin | Paris | Rome | Madrid | 1 | Geography`",
            parse_mode=ParseMode.MARKDOWN
        )


@app.on_message(filters.private & filters.document)
async def handle_file_upload(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id].get("step") != "awaiting_data":
        return
    
    method = user_states[user_id].get("method")
    file_ext = message.document.file_name.split(".")[-1].lower()
    
    if method == "csv" and file_ext != "csv":
        await message.reply_text("❌ Please upload a CSV file!")
        return
    
    if method == "txt" and file_ext != "txt":
        await message.reply_text("❌ Please upload a TXT file!")
        return
    
    file_path = await message.download()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        questions = parse_quiz_file(content, file_ext)
        
        if not questions:
            await message.reply_text("❌ No valid questions found in file!")
            return
        
        is_valid, error_msg = validate_quiz_data(questions)
        if not is_valid:
            await message.reply_text(f"❌ **Validation Error:**\n{error_msg}", parse_mode=ParseMode.MARKDOWN)
            return
        
        user_states[user_id] = {
            "step": "awaiting_name",
            "questions": questions
        }
        
        await message.reply_text(
            f"✅ **Parsed {len(questions)} questions successfully!**\n\n"
            "📝 **Enter quiz name:**",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await message.reply_text(f"❌ Error processing file: {str(e)}")


@app.on_message(filters.private & filters.text & ~filters.command(["start", "createquiz", "startquiz", "quizstatus", "cancelquiz", "deletequiz"]))
async def handle_text_input(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state.get("step") == "awaiting_data" and state.get("method") == "paste":
        content = message.text
        
        try:
            questions = parse_quiz_file(content, "txt")
            
            if not questions:
                await message.reply_text("❌ No valid questions found!")
                return
            
            is_valid, error_msg = validate_quiz_data(questions)
            if not is_valid:
                await message.reply_text(f"❌ **Validation Error:**\n{error_msg}", parse_mode=ParseMode.MARKDOWN)
                return
            
            user_states[user_id] = {
                "step": "awaiting_name",
                "questions": questions
            }
            
            await message.reply_text(
                f"✅ **Parsed {len(questions)} questions successfully!**\n\n"
                "📝 **Enter quiz name:**",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await message.reply_text(f"❌ Error processing text: {str(e)}")
    
    elif state.get("step") == "awaiting_name":
        quiz_name = message.text.strip()
        
        if len(quiz_name) < 3:
            await message.reply_text("❌ Quiz name must be at least 3 characters!")
            return
        
        user_states[user_id]["quiz_name"] = quiz_name
        user_states[user_id]["step"] = "awaiting_time"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱ 10 seconds", callback_data="time_10")],
            [InlineKeyboardButton("⏱ 20 seconds", callback_data="time_20")],
            [InlineKeyboardButton("⏱ 30 seconds", callback_data="time_30")],
            [InlineKeyboardButton("⏱ Custom time", callback_data="time_custom")]
        ])
        
        await message.reply_text(
            "⏱ **Select time per question:**",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif state.get("step") == "awaiting_custom_time":
        try:
            custom_time = int(message.text)
            
            if custom_time < 5 or custom_time > 300:
                await message.reply_text("❌ Time must be between 5 and 300 seconds!")
                return
            
            await finalize_quiz_creation(user_id, custom_time, message)
            
        except ValueError:
            await message.reply_text("❌ Please enter a valid number!")


@app.on_callback_query(filters.regex("^time_"))
async def time_selection(client: Client, callback_query):
    user_id = callback_query.from_user.id
    
    if user_id not in user_states:
        await callback_query.answer("❌ Session expired. Please start again.", show_alert=True)
        return
    
    time_option = callback_query.data.split("_")[1]
    
    if time_option == "custom":
        user_states[user_id]["step"] = "awaiting_custom_time"
        await callback_query.message.edit_text(
            "⏱ **Enter custom time per question (5-300 seconds):**",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        time_per_question = int(time_option)
        await finalize_quiz_creation(user_id, time_per_question, callback_query.message)


async def finalize_quiz_creation(user_id: int, time_per_question: int, message: Message):
    state = user_states[user_id]
    quiz_name = state["quiz_name"]
    questions = state["questions"]
    
    quiz_id = await db.create_quiz(user_id, quiz_name, questions, time_per_question)
    
    del user_states[user_id]
    
    await message.reply_text(
        f"✅ **Quiz Created Successfully!**\n\n"
        f"**Quiz ID:** `{quiz_id}`\n"
        f"**Name:** {quiz_name}\n"
        f"**Questions:** {len(questions)}\n"
        f"**Time/Question:** {time_per_question}s\n\n"
        f"**Start with:** `/startquiz {quiz_id}`",
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command("startquiz"))
async def start_quiz_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/startquiz <quiz_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    quiz_id = message.command[1]
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    quiz = await db.get_quiz(quiz_id)
    
    if not quiz:
        await message.reply_text("❌ Quiz not found!")
        return
    
    if await quiz_manager.is_quiz_running(chat_id):
        await message.reply_text("❌ A quiz is already running in this chat!")
        return
    
    has_attempted = await db.has_user_attempted(quiz_id, user_id)
    if has_attempted and message.chat.type == "private":
        await message.reply_text("❌ You have already attempted this quiz!")
        return
    
    await message.reply_text(
        f"🎯 **Starting Quiz: {quiz['name']}**\n\n"
        f"**Total Questions:** {len(quiz['questions'])}\n"
        f"**Time per Question:** {quiz['time_per_question']}s\n\n"
        "Get ready! First question in 3 seconds...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await asyncio.sleep(3)
    await quiz_manager.start_quiz(chat_id, quiz_id, quiz)


@app.on_poll_answer()
async def handle_poll_answer(client: Client, poll_answer):
    await quiz_manager.handle_answer(poll_answer)


@app.on_message(filters.command("quizstatus"))
async def quiz_status_command(client: Client, message: Message):
    active_quizzes = quiz_manager.get_active_quizzes()
    
    if not active_quizzes:
        await message.reply_text("📊 No active quizzes running.")
        return
    
    status_text = "📊 **Active Quizzes:**\n\n"
    
    for chat_id, quiz_data in active_quizzes.items():
        quiz_name = quiz_data.get("quiz_name", "Unknown")
        current = quiz_data.get("current_question", 0) + 1
        total = quiz_data.get("total_questions", 0)
        participants = len(quiz_data.get("participants", {}))
        
        status_text += f"**Chat ID:** `{chat_id}`\n"
        status_text += f"**Quiz:** {quiz_name}\n"
        status_text += f"**Progress:** {current}/{total}\n"
        status_text += f"**Participants:** {participants}\n\n"
    
    await message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


@app.on_message(filters.command("cancelquiz"))
async def cancel_quiz_command(client: Client, message: Message):
    chat_id = message.chat.id
    
    if not await quiz_manager.is_quiz_running(chat_id):
        await message.reply_text("❌ No quiz is running in this chat!")
        return
    
    await quiz_manager.cancel_quiz(chat_id)
    await message.reply_text("✅ Quiz cancelled successfully!")


@app.on_message(filters.command("deletequiz") & filters.private)
async def delete_quiz_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/deletequiz <quiz_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    quiz_id = message.command[1]
    user_id = message.from_user.id
    
    quiz = await db.get_quiz(quiz_id)
    
    if not quiz:
        await message.reply_text("❌ Quiz not found!")
        return
    
    if quiz["creator_id"] != user_id:
        await message.reply_text("❌ You can only delete quizzes you created!")
        return
    
    success = await db.delete_quiz(quiz_id)
    
    if success:
        await message.reply_text(f"✅ Quiz `{quiz_id}` deleted successfully!", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ Failed to delete quiz!")


async def main():
    await db.connect()
    await app.start()
    logger.info("Bot started successfully!")
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
