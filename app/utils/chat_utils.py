from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models import Message, Thread
from app.auth import get_current_user
from fastapi import Depends, HTTPException

async def get_messages(thread_id: str, db: Session, user_id: Optional[int] = None) -> List[Dict]:
    """
    Получает историю сообщений из базы данных и форматирует их в нужном формате.
    Args:
        thread_id: ID треда
        db: Сессия базы данных
        user_id: ID пользователя (опционально)
    Returns:
        List[Dict]: Список сообщений в формате [{'role': 'user'/'assistant', 'content': 'text'}]
    """
    # Проверяем принадлежность треда пользователю
    if user_id:
        thread = db.query(Thread).filter_by(id=thread_id).first()
        if not thread or thread.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
    
    # Получаем сообщения из базы
    query = db.query(Message).filter(Message.thread_id == thread_id)
    messages = query.order_by(Message.created_at.asc()).all()
    
    # Форматируем сообщения в нужном формате
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            'role': msg.role,  # 'user' или 'assistant'
            'content': msg.content,
            'created_at': msg.created_at.isoformat() if msg.created_at else None
        })
    
    return formatted_messages 