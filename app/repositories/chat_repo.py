from datetime import datetime
from typing import List, Optional
from app.db.mongo import get_chat_db

class ChatRepository:
    def get_sessions_collection(self):
        db = get_chat_db()
        return db["chat_sessions"] if db is not None else None

    def get_messages_collection(self):
        db = get_chat_db()
        return db["chat_messages"] if db is not None else None

    async def get_all_sessions(self) -> List[dict]:
        col = self.get_sessions_collection()
        if col is None:
            return []
        cursor = col.find({}).sort("updated_at", -1)
        sessions = []
        async for doc in cursor:
            doc.pop("_id", None)
            sessions.append(doc)
        return sessions

    async def create_or_update_session(self, session_id: str, title: str) -> dict:
        col = self.get_sessions_collection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = await col.find_one({"session_id": session_id})
        if existing:
            await col.update_one(
                {"session_id": session_id},
                {"$set": {"title": title, "updated_at": now}}
            )
            existing["title"] = title
            existing["updated_at"] = now
            existing.pop("_id", None)
            return existing
        else:
            doc = {
                "session_id": session_id,
                "title": title,
                "created_at": now,
                "updated_at": now
            }
            await col.insert_one(doc)
            doc.pop("_id", None)
            return doc

    async def update_session_title(self, session_id: str, title: str) -> Optional[dict]:
        col = self.get_sessions_collection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await col.update_one(
            {"session_id": session_id},
            {"$set": {"title": title, "updated_at": now}}
        )
        return await col.find_one({"session_id": session_id}, {"_id": 0})

    async def get_session_messages(self, session_id: str) -> List[dict]:
        col = self.get_messages_collection()
        if col is None:
            return []
        cursor = col.find({"session_id": session_id}).sort("timestamp", 1)
        messages = []
        async for doc in cursor:
            doc.pop("_id", None)
            messages.append(doc)
        return messages

    async def add_message(self, session_id: str, role: str, content: str) -> dict:
        col = self.get_messages_collection()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }
        await col.insert_one(msg_doc)

        # Generate a smart title if this is the first message for the session
        sessions_col = self.get_sessions_collection()
        existing_session = await sessions_col.find_one({"session_id": session_id})
        if not existing_session and role == "user":
            clean_content = content.replace("\n", " ").strip()
            title = clean_content[:28] + ("..." if len(clean_content) > 28 else "")
            await self.create_or_update_session(session_id, title)
        else:
            await sessions_col.update_one(
                {"session_id": session_id},
                {"$set": {"updated_at": timestamp}}
            )

        msg_doc.pop("_id", None)
        return msg_doc

    async def delete_session(self, session_id: str) -> bool:
        s_col = self.get_sessions_collection()
        m_col = self.get_messages_collection()
        if s_col is not None:
            await s_col.delete_one({"session_id": session_id})
        if m_col is not None:
            await m_col.delete_many({"session_id": session_id})
        return True

chat_repo = ChatRepository()
