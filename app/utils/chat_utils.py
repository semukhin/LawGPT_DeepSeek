from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models import Message, Thread
from app.auth import get_current_user
from fastapi import Depends, HTTPException

async def get_messages(thread_id: str, db: Session, current_user_id: Optional[int] = None) -> List[Dict[str, str]]:
    """Возвращает сообщения из выбранного треда."""
    
    # Проверяем принадлежность треда пользователю
    if current_user_id:
        thread = db.query(Thread).filter_by(id=thread_id).first()
        if not thread or thread.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
    
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