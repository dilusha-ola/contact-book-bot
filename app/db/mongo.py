import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class MongoManager:
    def __init__(self):
        self.client: AsyncIOMotorClient = None

    def connect(self):
        try:
            logger.info("Connecting to MongoDB Atlas for Chat Bot...")
            self.client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
            logger.info("MongoDB Atlas connection established for Chat Bot.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas for Chat Bot: {e}")

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB Atlas connection closed for Chat Bot.")

    def get_database(self):
        if self.client is None:
            self.connect()
        return self.client["chat_bot_db"]

mongo_manager = MongoManager()

def get_chat_db():
    return mongo_manager.get_database()
