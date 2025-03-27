# app/models_vexa.py
"""
Модели данных для интеграции с Vexa.ai
"""
from app.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from sqlalchemy.dialects.postgresql import JSONB, JSON
from sqlalchemy import Index

# Определяем Base здесь же, если он не импортирован
Base = declarative_base()

class VexaMeeting(Base):
    __tablename__ = "vexa_meetings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    vexa_meeting_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    source_type = Column(String(50), nullable=False)  # google_meet, zoom, etc.
    connection_id = Column(String(100), nullable=False)
    meeting_metadata = Column(JSON, nullable=True)

    user = relationship("User", back_populates="vexa_meetings")
    transcripts = relationship("VexaTranscript", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("VexaMeetingSummary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


class VexaTranscript(Base):
    __tablename__ = "vexa_transcripts"
    __table_args__ = {'extend_existing': True}
    Index('idx_transcript_meeting_starttime', 'meeting_id', 'start_time')
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("vexa_meetings.id"), nullable=False)
    vexa_transcript_id = Column(String(100), nullable=False)
    speaker = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    text = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=True)
    
    # Отношения
    meeting = relationship("VexaMeeting", back_populates="transcripts")

class VexaMeetingSummary(Base):
    """Модель для хранения саммари встречи"""
    __tablename__ = "vexa_meeting_summaries"
    __table_args__ = {'extend_existing': True}

    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("vexa_meetings.id"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text, nullable=True)  # JSON с ключевыми моментами
    action_items = Column(Text, nullable=True)  # JSON с задачами
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    meeting = relationship("VexaMeeting", back_populates="summary")


class VexaIntegrationSettings(Base):
    """Модель для хранения настроек интеграции с Vexa для пользователя"""
    __tablename__ = "vexa_integration_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    enable_recording = Column(Boolean, default=True)
    enable_summary = Column(Boolean, default=True)
    enable_search = Column(Boolean, default=True)
    vexa_token = Column(String(255), nullable=True)
    browser_extension_installed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="vexa_settings")


# Расширение существующей модели User для связи с Vexa
def extend_user_model():
    """
    Расширяет модель User для добавления связей с Vexa.
    """
    from app.models import User
    User.vexa_meetings = relationship("VexaMeeting", back_populates="user")
    User.vexa_settings = relationship("VexaIntegrationSettings", back_populates="user", uselist=False)


# Модель для хранения временных данных аудиопотока
class VexaAudioStream(Base):
    """Модель для временного хранения данных аудиопотока"""
    __tablename__ = "vexa_audio_streams"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(String(100), nullable=False, index=True)
    meeting_id = Column(Integer, ForeignKey("vexa_meetings.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_type = Column(String(50), nullable=False)
    stream_status = Column(String(50), default="active")
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stream_metadata = Column(JSON, nullable=True)
    
    # Отношения
    user = relationship("User")
    meeting = relationship("VexaMeeting", foreign_keys=[meeting_id])
