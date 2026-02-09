import asyncio
from pyrogram import Client
from pyrogram.enums import ParseMode
from database import Database
import logging

logger = logging.getLogger(__name__)


class QuizManager:
    def __init__(self, app: Client, db: Database):
        self.app = app
        self.db = db
        self.active_quizzes = {}
        self.poll_mapping = {}
    
    async def is_quiz_running(self, chat_id: int) -> bool:
        return chat_id in self.active_quizzes
    
    def get_active_quizzes(self):
        return self.active_quizzes.copy()
    
    async def start_quiz(self, chat_id: int, quiz_id: str, quiz: dict):
        self.active_quizzes[chat_id] = {
            "quiz_id": quiz_id,
            "quiz_name": quiz["name"],
            "questions": quiz["questions"],
            "current_question": 0,
            "total_questions": len(quiz["questions"]),
            "time_per_question": quiz["time_per_question"],
            "participants": {},
            "task": None
        }
        
        asyncio.create_task(self._run_quiz(chat_id))
    
    async def _run_quiz(self, chat_id: int):
        quiz_data = self.active_quizzes[chat_id]
        questions = quiz_data["questions"]
        time_per_question = quiz_data["time_per_question"]
        
        try:
            for idx, question in enumerate(questions):
                quiz_data["current_question"] = idx
                
                poll_message = await self.app.send_poll(
                    chat_id=chat_id,
                    question=question["question"],
                    options=[
                        question["option_a"],
                        question["option_b"],
                        question["option_c"],
                        question["option_d"]
                    ],
                    type="quiz",
                    correct_option_id=question["correct_option"],
                    explanation=question.get("explanation", ""),
                    is_anonymous=False,
                    open_period=time_per_question
                )
                
                self.poll_mapping[poll_message.poll.id] = {
                    "chat_id": chat_id,
                    "quiz_id": quiz_data["quiz_id"],
                    "question_index": idx,
                    "correct_option": question["correct_option"]
                }
                
                await asyncio.sleep(time_per_question + 2)
            
            await self._end_quiz(chat_id)
            
        except asyncio.CancelledError:
            logger.info(f"Quiz cancelled in chat {chat_id}")
        except Exception as e:
            logger.error(f"Error running quiz in chat {chat_id}: {e}")
            await self.app.send_message(chat_id, f"❌ Quiz error: {str(e)}")
            await self._cleanup_quiz(chat_id)
    
    async def handle_answer(self, poll_answer):
        poll_id = poll_answer.poll_id
        
        if poll_id not in self.poll_mapping:
            return
        
        poll_data = self.poll_mapping[poll_id]
        chat_id = poll_data["chat_id"]
        
        if chat_id not in self.active_quizzes:
            return
        
        quiz_data = self.active_quizzes[chat_id]
        user_id = poll_answer.user.id
        first_name = poll_answer.user.first_name
        
        if user_id not in quiz_data["participants"]:
            quiz_data["participants"][user_id] = {
                "first_name": first_name,
                "correct": 0,
                "wrong": 0,
                "answered": set()
            }
        
        participant = quiz_data["participants"][user_id]
        question_index = poll_data["question_index"]
        
        if question_index in participant["answered"]:
            return
        
        participant["answered"].add(question_index)
        
        selected_option = poll_answer.option_ids[0]
        correct_option = poll_data["correct_option"]
        
        if selected_option == correct_option:
            participant["correct"] += 1
        else:
            participant["wrong"] += 1
    
    async def _end_quiz(self, chat_id: int):
        quiz_data = self.active_quizzes[chat_id]
        quiz_id = quiz_data["quiz_id"]
        total_questions = quiz_data["total_questions"]
        participants = quiz_data["participants"]
        
        for user_id, data in participants.items():
            correct = data["correct"]
            wrong = data["wrong"]
            accuracy = (correct / total_questions * 100) if total_questions > 0 else 0
            
            await self.db.save_result(
                quiz_id=quiz_id,
                chat_id=chat_id,
                user_id=user_id,
                first_name=data["first_name"],
                correct=correct,
                wrong=wrong,
                total=total_questions,
                accuracy=accuracy
            )
        
        await self._send_leaderboard(chat_id, quiz_id, quiz_data["quiz_name"])
        
        await self._cleanup_quiz(chat_id)
    
    async def _send_leaderboard(self, chat_id: int, quiz_id: str, quiz_name: str):
        results = await self.db.get_quiz_results(quiz_id, chat_id)
        
        if not results:
            await self.app.send_message(
                chat_id,
                "🏆 **Quiz Completed!**\n\nNo participants found.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        leaderboard_text = f"🏆 **Quiz Completed: {quiz_name}**\n\n📊 **Leaderboard:**\n\n"
        
        for rank, result in enumerate(results, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            leaderboard_text += (
                f"{medal} **{result['first_name']}** — "
                f"Score: {result['correct']}/{result['total']} — "
                f"Accuracy: {result['accuracy']:.1f}%\n"
            )
        
        await self.app.send_message(chat_id, leaderboard_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel_quiz(self, chat_id: int):
        if chat_id in self.active_quizzes:
            quiz_data = self.active_quizzes[chat_id]
            
            if quiz_data.get("task"):
                quiz_data["task"].cancel()
            
            await self._cleanup_quiz(chat_id)
    
    async def _cleanup_quiz(self, chat_id: int):
        if chat_id in self.active_quizzes:
            quiz_data = self.active_quizzes[chat_id]
            
            polls_to_remove = [
                poll_id for poll_id, data in self.poll_mapping.items()
                if data["chat_id"] == chat_id
            ]
            
            for poll_id in polls_to_remove:
                del self.poll_mapping[poll_id]
            
            del self.active_quizzes[chat_id]
            
            logger.info(f"Cleaned up quiz in chat {chat_id}")
