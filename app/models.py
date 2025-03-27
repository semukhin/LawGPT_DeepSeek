from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, func
from app.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from vexa.vexa_integration_models import (
    VexaMeeting, 
    VexaTranscript, 
    VexaMeetingSummary, 
    VexaIntegrationSettings, 
    VexaAudioStream, 
    extend_user_model
)


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


# Импорт и инициализацию моделей Vexa
import importlib.util

# Загружаем модуль динамически
spec = importlib.util.spec_from_file_location("vexa_models", "vexa/vexa_integration_models.py")
vexa_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vexa_models)

# Доступ к классам и функциям
VexaMeeting = vexa_models.VexaMeeting
VexaTranscript = vexa_models.VexaTranscript
VexaMeetingSummary = vexa_models.VexaMeetingSummary
VexaIntegrationSettings = vexa_models.VexaIntegrationSettings
VexaAudioStream = vexa_models.VexaAudioStream
extend_user_model = vexa_models.extend_user_model

# Расширяем модель User для связи с Vexa
extend_user_model()


from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class VoiceInputLog(Base):
    """
    Модель для логирования использования голосового ввода
    """
    __tablename__ = "voice_input_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    thread_id = Column(String(50), ForeignKey('threads.id'), nullable=False)
    language = Column(String(10), nullable=False)  # Код языка
    audio_duration = Column(Float, nullable=False)  # Длительность аудио в секундах
    audio_size = Column(Integer, nullable=False)  # Размер аудиофайла в байтах
    recognition_success = Column(Boolean, nullable=False)
    recognition_confidence = Column(Float, nullable=True)
    recognition_error = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими моделями
    user = relationship("User")
    thread = relationship("Thread")

# Обновляем модель User для связи с логами голосового ввода
def extend_user_model(Base):
    Base.voice_input_logs = relationship("VoiceInputLog", back_populates="user")