# app/handlers/vexa_handlers.py
"""
API роутеры для работы с Vexa.ai
Обработка запросов для транскрибации, управления встречами и поиска
"""
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, Query, WebSocket, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models
from app.models_vexa import VexaMeeting, VexaTranscript, VexaMeetingSummary, VexaIntegrationSettings, VexaAudioStream, extend_user_model
from app.database import get_db
from app.auth import get_current_user
from app.services.vexa_client import VexaApiClient, MeetingInfo, TranscriptSegment, MeetingSummary
from cryptography.fernet import Fernet

from fastapi.security import OAuth2PasswordBearer
from starlette.requests import Request
import time
from datetime import datetime, timedelta

from functools import lru_cache
from datetime import datetime, timedelta

# Кэш для проверки токенов
token_cache = {}

# Создаем ключ шифрования при запуске приложения
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка настроек
VEXA_API_KEY = os.getenv("VEXA_API_KEY")
VEXA_STREAM_URL = os.getenv("VEXA_STREAM_URL", "https://streamqueue.dev.vexa.ai")
VEXA_ENGINE_URL = os.getenv("VEXA_ENGINE_URL", "https://engine.dev.vexa.ai")
VEXA_TRANSCRIPTION_URL = os.getenv("VEXA_TRANSCRIPTION_URL", "https://transcription.dev.vexa.ai")

# Создание клиента Vexa
vexa_client = VexaApiClient(
    api_key=VEXA_API_KEY,
    stream_url=VEXA_STREAM_URL,
    engine_url=VEXA_ENGINE_URL,
    transcription_url=VEXA_TRANSCRIPTION_URL
)

# Расширение модели User
extend_user_model()

# Создание роутера
router = APIRouter(
    prefix="/api/vexa",
    tags=["vexa"],
    responses={404: {"description": "Not found"}},
)


def encrypt_token(token: str) -> str:
    """Шифрует токен для безопасного хранения"""
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Дешифрует токен для использования"""
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

# Затем в API-маршрутах:
@router.get("/extension/token")
async def get_extension_token(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.vexa_token:
        # Если токена нет, регистрируем пользователя заново
        registration = await vexa_client.register_user(str(current_user.id), current_user.email)
        
        # Шифруем токен перед сохранением
        settings.vexa_token = encrypt_token(registration.get("token"))
        settings.updated_at = datetime.now()
        
        db.commit()
        db.refresh(settings)
    
    # Дешифруем токен для использования
    token = decrypt_token(settings.vexa_token)
    
    return {
        "token": token,
        "extension_config": {
            "stream_url": VEXA_STREAM_URL,
            "enable_recording": settings.enable_recording,
            "user_id": str(current_user.id),
            "extension_version": "1.0.0"
        }
    }



# Получение настроек интеграции с Vexa для текущего пользователя
async def get_user_vexa_settings(user: models.User, db: Session):
    settings = db.query(VexaIntegrationSettings).filter(VexaIntegrationSettings.user_id == user.id).first()
    
    if not settings:
        # Если настроек нет, регистрируем пользователя в Vexa и создаем настройки
        registration = await vexa_client.register_user(str(user.id), user.email)
        
        settings = VexaIntegrationSettings(
            user_id=user.id,
            enable_recording=True,
            enable_summary=True,
            enable_search=True,
            vexa_token=registration.get("token"),
            browser_extension_installed=False,
            updated_at=datetime.now()
        )
        
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings

# Роутеры для настройки интеграции с Vexa

@router.get("/settings")
async def get_vexa_integration_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает текущие настройки интеграции пользователя с Vexa
    """
    settings = await get_user_vexa_settings(current_user, db)
    
    return {
        "user_id": current_user.id,
        "enable_recording": settings.enable_recording,
        "enable_summary": settings.enable_summary,
        "enable_search": settings.enable_search,
        "vexa_token": settings.vexa_token,
        "browser_extension_installed": settings.browser_extension_installed,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }

@router.post("/settings")
async def update_vexa_integration_settings(
    enable_recording: bool = Form(...),
    enable_summary: bool = Form(...),
    enable_search: bool = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновляет настройки интеграции пользователя с Vexa
    """
    settings = await get_user_vexa_settings(current_user, db)
    
    settings.enable_recording = enable_recording
    settings.enable_summary = enable_summary
    settings.enable_search = enable_search
    settings.updated_at = datetime.now()
    
    db.commit()
    db.refresh(settings)
    
    return {
        "user_id": current_user.id,
        "enable_recording": settings.enable_recording,
        "enable_summary": settings.enable_summary,
        "enable_search": settings.enable_search,
        "vexa_token": settings.vexa_token,
        "browser_extension_installed": settings.browser_extension_installed,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }

@router.post("/extension/install")
async def mark_extension_installed(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отмечает, что расширение браузера установлено
    """
    settings = await get_user_vexa_settings(current_user, db)
    
    settings.browser_extension_installed = True
    settings.updated_at = datetime.now()
    
    db.commit()
    db.refresh(settings)
    
    return {"status": "success", "message": "Статус расширения браузера обновлен"}

@router.get("/extension/token")
async def get_extension_token(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает токен для расширения браузера
    """
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.vexa_token:
        # Если токена нет, регистрируем пользователя заново
        registration = await vexa_client.register_user(str(current_user.id), current_user.email)
        
        settings.vexa_token = registration.get("token")
        settings.updated_at = datetime.now()
        
        db.commit()
        db.refresh(settings)
    
    return {
        "token": settings.vexa_token,
        "extension_config": {
            "stream_url": VEXA_STREAM_URL,
            "enable_recording": settings.enable_recording,
            "user_id": str(current_user.id),
            "extension_version": "1.0.0"
        }
    }

# Роутеры для управления встречами

@router.post("/meetings")
async def create_meeting(
    title: str = Form(...),
    source_type: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создает новую встречу
    """
    # Проверяем настройки пользователя
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.enable_recording:
        raise HTTPException(status_code=403, detail="Запись встреч отключена в настройках пользователя")
    
    # Генерируем ID встречи и ID соединения
    meeting_id = f"lawgpt_meeting_{int(time.time())}_{current_user.id}"
    connection_id = f"conn_{int(time.time())}_{current_user.id}"
    
    # Создаем запись о встрече в БД
    db_meeting = VexaMeeting(
        vexa_meeting_id=meeting_id,
        user_id=current_user.id,
        title=title,
        start_time=datetime.now(),
        status="active",
        source_type=source_type,
        connection_id=connection_id,
        metadata=json.dumps({
            "created_by": "lawgpt",
            "user_id": str(current_user.id),
            "user_email": current_user.email
        })
    )
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    
    # Создаем встречу в Vexa
    meeting_info = MeetingInfo(
        meeting_id=meeting_id,
        title=title,
        start_time=db_meeting.start_time,
        source_type=source_type,
        connection_id=connection_id,
        metadata={
            "user_id": str(current_user.id),
            "user_email": current_user.email
        }
    )
    
    try:
        vexa_response = await vexa_client.start_meeting(meeting_info)
        
        return {
            "id": db_meeting.id,
            "meeting_id": meeting_id,
            "title": title,
            "start_time": db_meeting.start_time.isoformat(),
            "connection_id": connection_id,
            "status": "active",
            "source_type": source_type,
            "vexa_response": vexa_response
        }
    except Exception as e:
        # В случае ошибки удаляем созданную запись
        db.delete(db_meeting)
        db.commit()
        
        raise HTTPException(status_code=500, detail=f"Ошибка при создании встречи в Vexa: {str(e)}")

@router.post("/meetings/{meeting_id}/end")
async def end_meeting(
    meeting_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Завершает встречу
    """
    # Находим встречу в БД
    db_meeting = db.query(VexaMeeting).filter(
        VexaMeeting.vexa_meeting_id == meeting_id,
        VexaMeeting.user_id == current_user.id
    ).first()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Встреча не найдена")
    
    if db_meeting.status != "active":
        raise HTTPException(status_code=400, detail="Встреча уже завершена")
    
    # Обновляем статус встречи в БД
    db_meeting.status = "completed"
    db_meeting.end_time = datetime.now()
    db.commit()
    db.refresh(db_meeting)
    
    # Завершаем встречу в Vexa
    try:
        vexa_response = await vexa_client.end_meeting(meeting_id)
        
        # Если включено создание саммари, запускаем его
        settings = await get_user_vexa_settings(current_user, db)
        
        if settings.enable_summary:
            try:
                summary = await vexa_client.generate_meeting_summary(meeting_id)
                
                # Сохраняем саммари в БД
                db_summary = VexaMeetingSummary(
                    meeting_id=db_meeting.id,
                    summary_text=summary.summary_text,
                    key_points=json.dumps(summary.key_points) if summary.key_points else None,
                    action_items=json.dumps(summary.action_items) if summary.action_items else None,
                    generated_at=summary.generated_at
                )
                db.add(db_summary)
                db.commit()
                
                vexa_response["summary"] = {
                    "generated": True,
                    "summary_text": summary.summary_text[:100] + "..." if len(summary.summary_text) > 100 else summary.summary_text
                }
            except Exception as e:
                logger.error(f"Ошибка при генерации саммари: {str(e)}")
                vexa_response["summary"] = {
                    "generated": False,
                    "error": str(e)
                }
        
        # Получаем и сохраняем транскрипты
        try:
            transcripts = await vexa_client.get_meeting_transcripts(meeting_id)
            
            # Сохраняем транскрипты в БД
            for transcript in transcripts:
                db_transcript = VexaTranscript(
                    meeting_id=db_meeting.id,
                    vexa_transcript_id=transcript.transcript_id,
                    speaker=transcript.speaker,
                    start_time=transcript.start_time,
                    end_time=transcript.end_time,
                    text=transcript.text,
                    confidence=transcript.confidence
                )
                db.add(db_transcript)
            
            db.commit()
            
            vexa_response["transcripts"] = {
                "count": len(transcripts),
                "saved": True
            }
        except Exception as e:
            logger.error(f"Ошибка при получении транскриптов: {str(e)}")
            vexa_response["transcripts"] = {
                "count": 0,
                "saved": False,
                "error": str(e)
            }
        
        return {
            "id": db_meeting.id,
            "meeting_id": meeting_id,
            "title": db_meeting.title,
            "start_time": db_meeting.start_time.isoformat(),
            "end_time": db_meeting.end_time.isoformat() if db_meeting.end_time else None,
            "status": db_meeting.status,
            "vexa_response": vexa_response
        }
    except Exception as e:
        # В случае ошибки возвращаем статус встречи
        raise HTTPException(status_code=500, detail=f"Ошибка при завершении встречи в Vexa: {str(e)}")


# Простой in-memory лимитер запросов
class RateLimiter:
    def __init__(self, requests_limit: int = 100, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.requests = {}  # user_id -> [timestamps]
    
    def is_rate_limited(self, user_id: str) -> bool:
        now = time.time()
        
        # Инициализация для нового пользователя
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Удаление старых запросов
        self.requests[user_id] = [ts for ts in self.requests[user_id] 
                                  if now - ts < self.window_seconds]
        
        # Проверка лимита
        if len(self.requests[user_id]) >= self.requests_limit:
            return True
        
        # Добавление текущего запроса
        self.requests[user_id].append(now)
        return False

# Создание экземпляра лимитера
rate_limiter = RateLimiter()

def rate_limit_dependency(
    request: Request,
    current_user: models.User = Depends(get_current_user)
):
    """Зависимость для ограничения скорости запросов"""
    if rate_limiter.is_rate_limited(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    return current_user


@router.get("/meetings")
async def get_meetings(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by meeting status"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (from)"),
    date_to: Optional[datetime] = Query(None, description="Filter by start date (to)"),
    sort_by: str = Query("start_time", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    current_user: models.User = Depends(rate_limit_dependency),
    db: Session = Depends(get_db)
):
    """
    Получает список встреч пользователя с расширенной фильтрацией и сортировкой
    """
    # Базовый запрос
    query = db.query(VexaMeeting).filter(VexaMeeting.user_id == current_user.id)
    
    # Применение фильтров
    if status:
        query = query.filter(VexaMeeting.status == status)
    
    if date_from:
        query = query.filter(VexaMeeting.start_time >= date_from)
    
    if date_to:
        query = query.filter(VexaMeeting.start_time <= date_to)
    
    # Общее количество с учетом фильтров
    total_count = query.count()
    
    # Применение сортировки
    sort_column = getattr(VexaMeeting, sort_by, VexaMeeting.start_time)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Применение пагинации
    meetings = query.offset(offset).limit(limit).all()
    
    result = []
    for meeting in meetings:
        # Проверяем, есть ли саммари
        summary = db.query(VexaMeetingSummary).filter(VexaMeetingSummary.meeting_id == meeting.id).first()
        
        meeting_data = {
            "id": meeting.id,
            "meeting_id": meeting.vexa_meeting_id,
            "title": meeting.title,
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
            "status": meeting.status,
            "source_type": meeting.source_type,
            "has_summary": summary is not None,
            "duration": (meeting.end_time - meeting.start_time).total_seconds() if meeting.end_time else None
        }
        
        result.append(meeting_data)
    
    return {
        "meetings": result,
        "total": total_count,
        "offset": offset,
        "limit": limit
    }


def verify_meeting_ownership(meeting_id: str, user_id: int, db: Session):
    """Проверяет, принадлежит ли встреча пользователю"""
    meeting = db.query(VexaMeeting).filter(
        VexaMeeting.vexa_meeting_id == meeting_id,
        VexaMeeting.user_id == user_id
    ).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or you don't have access to it"
        )
    
    return meeting

@router.get("/meetings/{meeting_id}")
async def get_meeting_details(
    meeting_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает детальную информацию о встрече
    """
    # Проверка владения встречей
    meeting = verify_meeting_ownership(meeting_id, current_user.id, db)

    # Находим встречу в БД
    db_meeting = db.query(VexaMeeting).filter(
        VexaMeeting.vexa_meeting_id == meeting_id,
        VexaMeeting.user_id == current_user.id
    ).first()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Встреча не найдена")
    
    # Получаем саммари, если есть
    summary = db.query(VexaMeetingSummary).filter(VexaMeetingSummary.meeting_id == db_meeting.id).first()
    
    # Получаем количество транскриптов
    transcript_count = db.query(VexaTranscript).filter(VexaTranscript.meeting_id == db_meeting.id).count()
    
    return {
        "id": db_meeting.id,
        "meeting_id": db_meeting.vexa_meeting_id,
        "title": db_meeting.title,
        "start_time": db_meeting.start_time.isoformat(),
        "end_time": db_meeting.end_time.isoformat() if db_meeting.end_time else None,
        "status": db_meeting.status,
        "source_type": db_meeting.source_type,
        "connection_id": db_meeting.connection_id,
        "metadata": json.loads(db_meeting.metadata) if db_meeting.metadata else None,
        "summary": {
            "available": summary is not None,
            "summary_text": summary.summary_text if summary else None,
            "key_points": json.loads(summary.key_points) if summary and summary.key_points else None,
            "action_items": json.loads(summary.action_items) if summary and summary.action_items else None,
            "generated_at": summary.generated_at.isoformat() if summary and summary.generated_at else None
        },
        "transcripts": {
            "count": transcript_count
        }
    }

@router.get("/meetings/{meeting_id}/transcript")
async def get_meeting_transcript(
    meeting_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает полный транскрипт встречи
    """
    # Находим встречу в БД
    db_meeting = db.query(VexaMeeting).filter(
        VexaMeeting.vexa_meeting_id == meeting_id,
        VexaMeeting.user_id == current_user.id
    ).first()
    
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Встреча не найдена")
    
    # Получаем транскрипты
    transcripts = db.query(VexaTranscript).filter(
        VexaTranscript.meeting_id == db_meeting.id
    ).order_by(
        VexaTranscript.start_time
    ).all()
    
    if not transcripts:
        raise HTTPException(status_code=404, detail="Транскрипты для встречи не найдены")
    
    result = []
    for transcript in transcripts:
        transcript_data = {
            "id": transcript.id,
            "transcript_id": transcript.vexa_transcript_id,
            "speaker": transcript.speaker,
            "start_time": transcript.start_time.isoformat(),
            "end_time": transcript.end_time.isoformat() if transcript.end_time else None,
            "text": transcript.text,
            "confidence": transcript.confidence
        }
        
        result.append(transcript_data)
    
    return {
        "meeting_id": meeting_id,
        "title": db_meeting.title,
        "segments": result,
        "count": len(result)
    }

# Роутеры для поиска по транскриптам

@router.post("/search")
async def search_in_transcripts(
    query: str = Form(...),
    limit: int = Form(10),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ищет в транскриптах встреч по запросу
    """
    # Проверяем настройки пользователя
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.enable_search:
        raise HTTPException(status_code=403, detail="Поиск по транскриптам отключен в настройках пользователя")
    
    # Выполняем поиск в Vexa
    try:
        search_results = await vexa_client.search_transcripts(query, str(current_user.id), limit)
        
        # Форматируем результаты
        formatted_results = []
        for result in search_results:
            # Находим встречу в БД для получения дополнительной информации
            meeting_id = result.get("meeting_id")
            db_meeting = db.query(VexaMeeting).filter(
                VexaMeeting.vexa_meeting_id == meeting_id,
                VexaMeeting.user_id == current_user.id
            ).first()
            
            if db_meeting:
                formatted_result = {
                    "text": result.get("text", ""),
                    "speaker": result.get("speaker", ""),
                    "meeting_id": meeting_id,
                    "meeting_title": db_meeting.title,
                    "meeting_date": db_meeting.start_time.isoformat(),
                    "timestamp": result.get("timestamp", 0),
                    "score": result.get("score", 0)
                }
                
                formatted_results.append(formatted_result)
        
        return {
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске в транскриптах: {str(e)}")

# Роутеры для обработки аудиоданных из расширения браузера

@router.put("/stream/audio")
async def upload_audio_chunk(
    chunk_index: int = Query(...),
    connection_id: str = Query(...),
    meeting_id: Optional[str] = Query(None),
    source_type: str = Query("google_meet"),
    audio_file: UploadFile = File(...),
    sample_rate: int = Query(16000, description="Audio sample rate"),
    channels: int = Query(1, description="Audio channels count"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загружает аудиочанк из расширения браузера с дополнительной информацией о формате
    """
    # Проверяем настройки пользователя
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.enable_recording:
        raise HTTPException(status_code=403, detail="Запись встреч отключена в настройках пользователя")
    
    # Проверка типа файла, если возможно
    content_type = audio_file.content_type
    valid_audio_types = ["audio/webm", "audio/wav", "audio/ogg", "audio/mpeg"]
    
    if content_type and content_type not in valid_audio_types:
        logger.warning(f"Unusual content type for audio: {content_type}")
    
    # Читаем аудиоданные
    audio_data = await audio_file.read()
    
    # Сохраняем метаданные об аудио для отладки
    stream = db.query(VexaAudioStream).filter(
        VexaAudioStream.connection_id == connection_id,
        VexaAudioStream.user_id == current_user.id
    ).first()
    
    # Если нет, создаем новую запись
    if not stream:
        stream = VexaAudioStream(
            connection_id=connection_id,
            user_id=current_user.id,
            source_type=source_type,
            stream_status="active",
            last_activity=datetime.now(),
            stream_metadata=json.dumps({
                "content_type": content_type,
                "sample_rate": sample_rate,
                "channels": channels,
                "first_chunk": chunk_index
            })
        )
       
        # Если указан meeting_id, связываем с ним
        if meeting_id:
            db_meeting = db.query(VexaMeeting).filter(
                VexaMeeting.vexa_meeting_id == meeting_id,
                VexaMeeting.user_id == current_user.id
            ).first()
            
            if db_meeting:
                stream.meeting_id = db_meeting.id
        
        db.add(stream)
        db.commit()
        db.refresh(stream)
    else:
        # Обновляем время последней активности
        stream.last_activity = datetime.now()
        db.commit()
    
    # Читаем аудиоданные
    audio_data = await audio_file.read()
    
    # Отправляем аудиоданные в Vexa
    try:
        result = await vexa_client.upload_audio_chunk(
            connection_id=connection_id,
            chunk_index=chunk_index,
            audio_data=audio_data,
            meeting_id=meeting_id,
            source=source_type
        )
        
        if not result.get("success", False):
            logger.error(f"Ошибка при загрузке аудиочанка в Vexa: {result.get('error')}")
            return {"status": "error", "message": result.get("error")}
        
        return {"status": "success", "message": "Аудиочанк загружен"}
    except Exception as e:
        logger.error(f"Ошибка при загрузке аудиочанка: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.websocket("/stream/ws/{connection_id}")
async def websocket_audio_stream(
    websocket: WebSocket,
    connection_id: str,
    token: str = Query(...),
    meeting_id: Optional[str] = Query(None)
):
    """
    WebSocket эндпоинт для потоковой передачи аудио в реальном времени
    """
    # Проверка токена
    try:
        # Проверка токена через VexaApiClient
        token_check = await vexa_client._make_request(
            "GET", 
            f"{vexa_client.stream_url}/api/v1/extension/check-token?token={token}"
        )
        
        if not token_check.get("success") or not token_check.get("data", {}).get("is_valid"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # Извлечение user_id из токена
        user_id = None
        try:
            # Логика получения user_id из токена
            pass
        except:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Проверка настроек пользователя
        db = next(get_db())
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        settings = await get_user_vexa_settings(user, db)
        if not settings.enable_recording:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return
        
        # Принимаем соединение
        await websocket.accept()
        
        # Инициализируем запись о потоке
        stream = db.query(VexaAudioStream).filter(
            VexaAudioStream.connection_id == connection_id,
            VexaAudioStream.user_id == user.id
        ).first()
        
        if not stream:
            stream = VexaAudioStream(
                connection_id=connection_id,
                user_id=user.id,
                source_type="websocket",
                stream_status="active",
                last_activity=datetime.now()
            )
            
            # Если указан meeting_id, связываем с ним
            if meeting_id:
                db_meeting = db.query(VexaMeeting).filter(
                    VexaMeeting.vexa_meeting_id == meeting_id,
                    VexaMeeting.user_id == user.id
                ).first()
                
                if db_meeting:
                    stream.meeting_id = db_meeting.id
            
            db.add(stream)
            db.commit()
        
        # Обрабатываем аудиоданные
        chunk_index = 0
        try:
            while True:
                # Получаем двоичные данные
                audio_data = await websocket.receive_bytes()
                
                # Обрабатываем аудиоданные с помощью VexaApiClient
                result = await vexa_client.upload_audio_chunk(
                    connection_id=connection_id,
                    chunk_index=chunk_index,
                    audio_data=audio_data,
                    meeting_id=meeting_id,
                    source="google_meet"  # или другой источник
                )
                
                # Обновляем индекс чанка
                chunk_index += 1
                
                # Обновляем время последней активности
                stream.last_activity = datetime.now()
                db.commit()
                
                # Отправляем подтверждение
                await websocket.send_json({"status": "ok", "chunk": chunk_index})
                
        except WebSocketDisconnect:
            # Обрабатываем отключение
            stream.stream_status = "disconnected"
            db.commit()
            logger.info(f"WebSocket disconnected for connection_id {connection_id}")
            
        except Exception as e:
            # Обрабатываем другие ошибки
            logger.error(f"Error in WebSocket audio stream: {str(e)}")
            stream.stream_status = "error"
            db.commit()
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            
    except Exception as e:
        # Обрабатываем ошибки аутентификации
        logger.error(f"Authentication error in WebSocket: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)


@router.put("/stream/speakers")
async def update_speakers_data(
    connection_id: str = Query(...),
    meeting_id: Optional[str] = Query(None),
    speakers_data: Dict[str, Any] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновляет информацию о говорящих
    """
    # Проверяем настройки пользователя
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.enable_recording:
        raise HTTPException(status_code=403, detail="Запись встреч отключена в настройках пользователя")
    
    # Отправляем данные о говорящих в Vexa
    try:
        result = await vexa_client.update_speakers(
            connection_id=connection_id,
            speakers_data=speakers_data,
            meeting_id=meeting_id
        )
        
        if not result.get("success", False):
            logger.error(f"Ошибка при обновлении данных о говорящих: {result.get('error')}")
            return {"status": "error", "message": result.get("error")}
        
        return {"status": "success", "message": "Данные о говорящих обновлены"}
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных о говорящих: {str(e)}")
        return {"status": "error", "message": str(e)}

# Роутер для интеграции с LawGPT для обогащения ответов контекстом из встреч

@router.post("/context")
async def get_context_for_llm(
    query: str = Form(...),
    thread_id: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает релевантный контекст из транскриптов для запроса к LLM
    """
    # Проверяем настройки пользователя
    settings = await get_user_vexa_settings(current_user, db)
    
    if not settings.enable_search:
        return {"context": "", "has_context": False}
    
    # Получаем релевантный контекст из Vexa
    try:
        context = await vexa_client.get_relevant_context(query, str(current_user.id), 5)
        
        return {
            "context": context,
            "has_context": bool(context),
            "source": "vexa_transcripts"
        }
    except Exception as e:
        logger.error(f"Ошибка при получении контекста: {str(e)}")
        return {"context": "", "has_context": False}



async def validate_token_with_cache(token: str) -> bool:
    """Проверяет токен с использованием кэша"""
    now = datetime.now()
    
    # Проверка кэша
    if token in token_cache:
        cache_time, is_valid = token_cache[token]
        # Кэш действителен в течение часа
        if now - cache_time < timedelta(hours=1):
            return is_valid
    
    # Если нет в кэше или кэш устарел, делаем запрос к API
    result = await vexa_client._make_request(
        "GET", 
        f"{vexa_client.stream_url}/api/v1/extension/check-token?token={token}"
    )
    
    is_valid = result.get("success") and result.get("data", {}).get("is_valid", False)
    
    # Обновляем кэш
    token_cache[token] = (now, is_valid)
    
    return is_valid

# LRU-кэш для данных пользователя
@lru_cache(maxsize=128)
def get_cached_user_meetings(user_id: int, limit: int = 10, offset: int = 0):
    """Кэшированное получение встреч пользователя"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        meetings = db.query(VexaMeeting).filter(
            VexaMeeting.user_id == user_id
        ).order_by(
            VexaMeeting.start_time.desc()
        ).offset(offset).limit(limit).all()
        
        # Преобразуем в словарь для сериализации
        result = []
        for meeting in meetings:
            result.append({
                "id": meeting.id,
                "meeting_id": meeting.vexa_meeting_id,
                "title": meeting.title,
                "start_time": meeting.start_time.isoformat(),
                "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
                "status": meeting.status
            })
        
        return result
    finally:
        db.close()

# Использование в API-маршруте
@router.get("/meetings/cached")
async def get_cached_meetings(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    refresh: bool = Query(False, description="Force refresh cache"),
    current_user: models.User = Depends(get_current_user)
):
    """
    Получает кэшированный список встреч пользователя
    """
    # Инвалидация кэша при необходимости
    if refresh:
        get_cached_user_meetings.cache_clear()
    
    meetings = get_cached_user_meetings(current_user.id, limit, offset)
    
    return {
        "meetings": meetings,
        "cached": True,
        "timestamp": datetime.now().isoformat()
    }