from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func
from app.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


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
    documents = relationship("Document", back_populates="user")
    prompt_logs = relationship("PromptLog", back_populates="user")
    
    # Пустые заглушки для отношений с Vexa
    vexa_meetings = None
    vexa_settings = None


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="verification_code")


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
    id = Column(String(50), primary_key=True, default=lambda: f"thread_{uuid.uuid4().hex}")
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
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    download_date = Column(DateTime, default=func.now())  # Поле есть?

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


try:
    # Импортируем модели Vexa
    from vexa.vexa_integration_models import (
        VexaMeeting, 
        VexaTranscript, 
        VexaMeetingSummary, 
        VexaIntegrationSettings, 
        VexaAudioStream, 
        extend_user_model
    )
    
    # Вызываем функцию расширения модели User
    extend_user_model()
    
except ImportError as e:
    print(f"Не удалось импортировать модели Vexa: {e}")
    # Создаем заглушки для моделей Vexa, если не удалось импортировать
    class VexaMeeting: pass
    class VexaTranscript: pass
    class VexaMeetingSummary: pass
    class VexaIntegrationSettings: pass
    class VexaAudioStream: pass
except NameError as e:
    print(f"Ошибка импорта функции: {e}")
except Exception as e:
    print(f"Неожиданная ошибка при работе с моделями Vexa: {e}")