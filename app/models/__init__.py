from .scraping import ScrapedContent
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base
from typing import List, Dict, Optional
from fastapi import HTTPException

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    threads = relationship("Thread", back_populates="user")
    documents = relationship("Document", back_populates="user")

class Thread(Base):
    __tablename__ = "threads"
    id = Column(String(50), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    first_message = Column(Text, nullable=True)
    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    thread = relationship("Thread", back_populates="messages")

class PromptLog(Base):
    __tablename__ = "prompt_logs"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

class ResearchResult(Base):
    __tablename__ = "research_results"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), ForeignKey("threads.id"), nullable=False)
    query = Column(Text, nullable=False)
    findings = Column(Text, nullable=True)
    analysis = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    document_id = Column(Integer, nullable=True)
    document_name = Column(String(255), nullable=True)
    document_num = Column(String(255), nullable=True)
    document_url = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=func.now())
    download_date = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="documents")

async def get_messages(thread_id: str, db, user_id: Optional[int] = None) -> List[Dict]:
    """Получает историю сообщений из базы данных."""
    if user_id:
        thread = db.query(Thread).filter_by(id=thread_id).first()
        if not thread or thread.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
    
    query = db.query(Message).filter(Message.thread_id == thread_id)
    messages = query.order_by(Message.created_at.asc()).all()
    
    return [{'role': msg.role, 'content': msg.content, 'created_at': msg.created_at.isoformat() if msg.created_at else None} for msg in messages]

__all__ = ['ScrapedContent', 'User', 'Thread', 'Message', 'PromptLog', 'ResearchResult', 'Document', 'get_messages']