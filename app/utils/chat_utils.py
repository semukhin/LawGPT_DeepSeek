from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Message
from app.auth import get_current_user
from fastapi import Depends

async def get_messages(thread_id: str, db: Session) -> List[Dict[str, str]]:
    """Возвращает сообщения из выбранного треда."""
    messages = db.query(Message).filter_by(thread_id=thread_id).order_by(
        Message.created_at).all()
    
    # Преобразуем сообщения в формат, подходящий для контекста
    formatted_messages = []
    for m in messages:
        formatted_messages.append({
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.timestamp() if m.created_at else 0
        })
    
    return formatted_messages 