from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func
from app.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from typing import List, Dict, Optional
from fastapi import HTTPException


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="verification_code")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    verification_code = relationship("VerificationCode", back_populates="user", uselist=False)
    threads = relationship("Thread", back_populates="user")
    documents = relationship("Document", back_populates="user")  # Добавляем связь
    prompt_logs = relationship("PromptLog", back_populates="user")



class TempUser(Base):
    __tablename__ = "temp_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=False, index=True)
    code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)

class Thread(Base):
    __tablename__ = "threads"
    id = Column(String(50), primary_key=True, default=lambda: f"thread_{uuid.uuid4().hex}")  # Сюда передать ИМЯ треда ("thread_ ....") которое нам приходит по API. 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    first_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread")
    prompt_logs = relationship("PromptLog", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    role = Column(String(10), nullable=False)  # 'user' или 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    tokens = Column(Integer, nullable=True)  # Добавленный столбец
    context_summary = Column(Text, nullable=True)  # Добавленный столбец

    thread = relationship("Thread", back_populates="messages")
    prompt_log = relationship("PromptLog", back_populates="message", uselist=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    document_id = Column(Integer, nullable=True)
    document_name = Column(String(255), nullable=True)
    document_num = Column(String(255), nullable=True)
    document_url = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    download_date = Column(DateTime, default=datetime.utcnow)

    # Связи
    user = relationship("User", back_populates="documents")


class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    thread = relationship("Thread", back_populates="prompt_logs")
    message = relationship("Message", back_populates="prompt_log", uselist=False)
    user = relationship("User", back_populates="prompt_logs")

class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    query = Column(Text, nullable=False)
    findings = Column(Text, nullable=True)  # JSON строка с результатами поиска
    analysis = Column(Text, nullable=False)  # Итоговый анализ
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    thread = relationship("Thread", backref="research_results")


async def get_messages(thread_id: str, db, user_id: Optional[int] = None) -> List[Dict]:
    """Получает историю сообщений из базы данных."""
    if user_id:
        thread = db.query(Thread).filter_by(id=thread_id).first()
        if not thread or thread.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
    
    query = db.query(Message).filter(Message.thread_id == thread_id)
    messages = query.order_by(Message.created_at.asc()).all()
    
    return [{'role': msg.role, 'content': msg.content, 'created_at': msg.created_at.isoformat() if msg.created_at else None} for msg in messages]
