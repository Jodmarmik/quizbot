from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.quizzes = None
        self.results = None
    
    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(Config.MONGO_URL)
            self.db = self.client.quiz_bot
            self.quizzes = self.db.quizzes
            self.results = self.db.results
            
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully!")
            
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
    
    async def create_quiz(self, creator_id: int, name: str, questions: list, time_per_question: int) -> str:
        quiz_id = str(uuid.uuid4())[:8]
        
        quiz_doc = {
            "quiz_id": quiz_id,
            "creator_id": creator_id,
            "name": name,
            "questions": questions,
            "time_per_question": time_per_question,
            "created_at": datetime.utcnow()
        }
        
        await self.quizzes.insert_one(quiz_doc)
        logger.info(f"Quiz created: {quiz_id}")
        return quiz_id
    
    async def get_quiz(self, quiz_id: str):
        quiz = await self.quizzes.find_one({"quiz_id": quiz_id})
        return quiz
    
    async def delete_quiz(self, quiz_id: str) -> bool:
        result = await self.quizzes.delete_one({"quiz_id": quiz_id})
        
        if result.deleted_count > 0:
            await self.results.delete_many({"quiz_id": quiz_id})
            logger.info(f"Quiz deleted: {quiz_id}")
            return True
        
        return False
    
    async def save_result(self, quiz_id: str, chat_id: int, user_id: int, first_name: str, 
                         correct: int, wrong: int, total: int, accuracy: float):
        result_doc = {
            "quiz_id": quiz_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "first_name": first_name,
            "correct": correct,
            "wrong": wrong,
            "total": total,
            "accuracy": accuracy,
            "completed_at": datetime.utcnow()
        }
        
        await self.results.insert_one(result_doc)
        logger.info(f"Result saved for user {user_id} in quiz {quiz_id}")
    
    async def has_user_attempted(self, quiz_id: str, user_id: int) -> bool:
        result = await self.results.find_one({"quiz_id": quiz_id, "user_id": user_id})
        return result is not None
    
    async def get_quiz_results(self, quiz_id: str, chat_id: int):
        cursor = self.results.find({"quiz_id": quiz_id, "chat_id": chat_id})
        results = await cursor.to_list(length=None)
        
        results.sort(key=lambda x: (x["correct"], x["accuracy"]), reverse=True)
        
        return results
