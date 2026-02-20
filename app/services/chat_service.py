import json, uuid
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from config import config
from app.models import Message, ChatSession

class ChatService:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        
    def create_session(self, chat_type: str = "general") -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            chat_type=chat_type,
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.sessions[session_id] = session
        print(f"[ChatService] Created new session: {session_id} ({chat_type})")
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self.sessions.get(session_id)
    
    def get_or_create_session(self, session_id: Optional[str], chat_type: str = "general") -> ChatSession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session(chat_type)
    
    def add_message(self, session_id: str, role: str, content: str) -> Message:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        message = Message(role=role, content=content)
        session.messages.append(message)
        session.updated_at = datetime.now()
        return message
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        session = self.get_session(session_id)
        if not session:
            return []
        return [{"role": msg.role, "content": msg.content} for msg in session.messages]
    
    def save_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        try:
            config.CHATS_PATH.mkdir(parents=True, exist_ok=True)
            file_path = config.CHATS_PATH / f"{session_id}.json"
            data = {
                "session_id": session.session_id,
                "chat_type": session.chat_type,
                "messages": [{"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()} for msg in session.messages],
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[ChatService] Saved session: {session_id}")
            return True
        except Exception as e:
            print(f"[ChatService] Error saving session: {e}")
            return False
    
    def list_sessions(self) -> List[Dict]:
        sessions = []
        if not config.CHATS_PATH.exists():
            return sessions
        for file_path in config.CHATS_PATH.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({"session_id": data["session_id"], "chat_type": data["chat_type"], "message_count": len(data["messages"]), "created_at": data["created_at"], "updated_at": data["updated_at"]})
            except Exception as e:
                print(f"[ChatService] Error reading {file_path}: {e}")
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
        file_path = config.CHATS_PATH / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

chat_service = ChatService()
