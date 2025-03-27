# app/handlers/vexa_handlers.py
"""
API роутеры для работы с Vexa.ai
Обработка запросов для транскрибации, управления встречами и поиска
"""
import base64
import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    WebSocket, 
    status,
    Request, 
    File, 
    Form, 
    Query, 
    UploadFile
)
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect  # Добавлен импорт WebSocketDisconnect
from sqlalchemy.orm import Session

from app import models
from app.models import User
from app.database import get_db
from app.auth import get_current_user
from cryptography.fernet import Fernet

# Импорт VexaApiClient из вашего клиента
from vexa.vexa_api_client import VexaApiClient 

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, Query, WebSocket, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models
from app.config import VEXA_INTEGRATION_ENABLED
from vexa.vexa_api_client import VexaApiClient, MeetingInfo, TranscriptSegment, MeetingSummary
from vexa.vexa_integration_models import VexaMeeting, VexaTranscript, VexaMeetingSummary, VexaIntegrationSettings, VexaAudioStream, extend_user_model

from fastapi.security import OAuth2PasswordBearer
import time
from datetime import datetime, timedelta

from functools import lru_cache

# Кэш для проверки токенов
token_cache = {}

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка настроек
VEXA_API_KEY = os.getenv("VEXA_API_KEY")
VEXA_STREAM_URL = os.getenv("VEXA_STREAM_URL", "https://streamqueue.dev.vexa.ai")
VEXA_ENGINE_URL = os.getenv("VEXA_ENGINE_URL", "https://engine.dev.vexa.ai")
VEXA_TRANSCRIPTION_URL = os.getenv("VEXA_TRANSCRIPTION_URL", "https://transcription.dev.vexa.ai")
ENCRYPTION_KEY = os.getenv("VEXA_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Генерируем ключ только при первом запуске и сохраняем его
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"Generated new encryption key: {ENCRYPTION_KEY}")
    print("Save this key in your environment variables as VEXA_ENCRYPTION_KEY")


# Создание роутера
router = APIRouter(
    prefix="/api/vexa",
    tags=["vexa"],
    responses={404: {"description": "Not found"}},
)


# Проверяем наличие ключа в переменных окружения
ENCRYPTION_KEY = os.getenv("VEXA_ENCRYPTION_KEY")

# Если ключ не задан, генерируем новый
if not ENCRYPTION_KEY:
    print("🔑 Генерация нового ключа шифрования для Vexa")
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"Сгенерирован новый ключ: {ENCRYPTION_KEY}")
    print("ВАЖНО: Сохраните этот ключ в переменных окружения VEXA_ENCRYPTION_KEY")

# Функция для корректного форматирования ключа
def get_valid_fernet_key(key_str):
    """Преобразует строку ключа в корректный формат для Fernet"""
    if not key_str:
        # Генерируем новый ключ, если не задан
        return Fernet.generate_key()
    
    try:
        # Проверяем длину и формат ключа
        key_bytes = key_str.encode() if isinstance(key_str, str) else key_str
        if len(base64.urlsafe_b64decode(key_bytes)) != 32:
            raise ValueError("Неверная длина ключа")
        return key_bytes
    except Exception as e:
        logging.warning(f"Некорректный ключ: {e}. Генерируем новый.")
        return Fernet.generate_key()

# Создаем корректный объект Fernet
cipher_suite = Fernet(get_valid_fernet_key(ENCRYPTION_KEY))

def encrypt_token(token: str) -> str:
    """Шифрует токен для безопасного хранения"""
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Дешифрует токен для использования"""
    return cipher_suite.decrypt(encrypted_token.encode()).decode()



class VexaApiClientStub:
    """
    Заглушка для VexaApiClient, 
    которая будет работать, если интеграция не настроена
    """
    def __init__(self, *args, **kwargs):
        logger.warning("Vexa API не настроен. Используется режим заглушки.")
    
    async def check_connection(self) -> bool:
        return False
    
    async def register_user(self, user_id: str, user_email: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Имитация регистрации пользователя {user_id}")
        return {
            "user_id": user_id,
            "token": "mock_token",
            "registered_at": "2024-01-01T00:00:00"
        }
    
    async def start_meeting(self, meeting_info) -> Dict[str, Any]:
        logger.info(f"Имитация создания встречи {meeting_info.meeting_id}")
        return {"status": "mock_meeting_created"}
    
    async def end_meeting(self, meeting_id: str) -> Dict[str, Any]:
        logger.info(f"Имитация завершения встречи {meeting_id}")
        return {"status": "mock_meeting_ended"}
    
    async def get_meeting_transcripts(self, meeting_id: str) -> list:
        logger.info(f"Имитация получения транскриптов для встречи {meeting_id}")
        return []
    
    async def search_transcripts(self, query: str, user_id: Optional[str] = None, limit: int = 10) -> list:
        logger.info(f"Имитация поиска в транскриптах: {query}")
        return []
    
# Кэшированная функция для получения клиента Vexa
@lru_cache(maxsize=1)
def get_vexa_client():
    """
    Фабрика для получения клиента Vexa
    Возвращает реальный клиент или заглушку
    """
    if VEXA_INTEGRATION_ENABLED:
        try:
            from vexa.vexa_api_client import VexaApiClient
            return VexaApiClient(
                api_key=VEXA_API_KEY,
                stream_url=os.getenv("VEXA_STREAM_URL"),
                engine_url=os.getenv("VEXA_ENGINE_URL"),
                transcription_url=os.getenv("VEXA_TRANSCRIPTION_URL")
            )
        except ImportError:
            logger.warning("Не удалось импортировать VexaApiClient. Используется заглушка.")
            return VexaApiClientStub()
    else:
        return VexaApiClientStub()



def encrypt_token(token: str) -> str:
    """Шифрует токен для безопасного хранения"""
    return cipher_suite.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Дешифрует токен для использования"""
    return cipher_suite.decrypt(encrypted_token.encode()).decode()

# Получение настроек интеграции с Vexa для текущего пользователя
async def get_user_vexa_settings(user: models.User, db: Session):
    """Получает или создает настройки интеграции с Vexa для пользователя"""
    settings = db.query(VexaIntegrationSettings).filter(VexaIntegrationSettings.user_id == user.id).first()
    
    if not settings:
        # Если настроек нет, регистрируем пользователя в Vexa и создаем настройки
        vexa_client = get_vexa_client()
        registration = await vexa_client.register_user(str(user.id), user.email)
        
        # Шифруем токен перед сохранением
        encrypted_token = encrypt_token(registration.get("token"))
        
        settings = VexaIntegrationSettings(
            user_id=user.id,
            enable_recording=True,
            enable_summary=True,
            enable_search=True,
            vexa_token=encrypted_token,
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
    
    # Не возвращаем сам токен в ответе, только его наличие
    return {
        "user_id": current_user.id,
        "enable_recording": settings.enable_recording,
        "enable_summary": settings.enable_summary,
        "enable_search": settings.enable_search,
        "has_token": bool(settings.vexa_token),
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
        "has_token": bool(settings.vexa_token),
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
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
):
    """
    Получает токен для расширения браузера
    """
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

# Роутеры для управления встречами
@router.post("/meetings")
async def create_meeting(
    title: str = Form(...),
    source_type: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
):
    """
    Создает новую встречу с поддержкой интеграции с Vexa
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
        meeting_metadata=json.dumps({
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
        # Если клиент - заглушка, используем mock-ответ
        if isinstance(vexa_client, VexaApiClientStub):
            vexa_response = {
                "status": "mock_meeting_created",
                "meeting_id": meeting_id
            }
        else:
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
        
        logger.error(f"Ошибка при создании встречи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании встречи: {str(e)}")

@router.post("/meetings/{meeting_id}/end")
async def end_meeting(
    meeting_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
        "metadata": json.loads(db_meeting.meeting_metadata) if db_meeting.meeting_metadata else None,
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
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
    meeting_id: Optional[str] = Query(None),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
            # Проверяем, есть ли в ответе token_check информация о user_id
            user_id = token_check.get("data", {}).get("user_id")
            if not user_id:
                # Если нет, парсим токен (format: lawgpt_USER_ID_TIMESTAMP)
                token_parts = token.split('_')
                if len(token_parts) >= 3 and token_parts[0] == 'lawgpt':
                    user_id = token_parts[1]
        except:
            logger.error("Не удалось извлечь user_id из токена")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        if not user_id:
            logger.error("User ID не найден в токене")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Проверка настроек пользователя
        db = next(get_db())
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            logger.error(f"Пользователь с ID {user_id} не найден")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        settings = await get_user_vexa_settings(user, db)
        if not settings.enable_recording:
            logger.warning(f"Запись отключена для пользователя {user_id}")
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
                last_activity=datetime.now(),
                stream_metadata=json.dumps({
                    "connection_type": "websocket",
                    "user_agent": websocket.headers.get("user-agent", "unknown")
                })
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
            db.refresh(stream)
        
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
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
    db: Session = Depends(get_db),
    vexa_client: VexaApiClient = Depends(get_vexa_client)
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
    vexa_client = get_vexa_client()
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



# Безопасная генерация ключа
def generate_safe_fernet_key():
    """Генерирует корректный Fernet-ключ"""
    return Fernet.generate_key()

# Проверка и генерация ключа
ENCRYPTION_KEY = os.getenv("VEXA_ENCRYPTION_KEY")

try:
    # Пытаемся создать корректный ключ
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = generate_safe_fernet_key().decode()
        print(f"🔑 Сгенерирован новый ключ: {ENCRYPTION_KEY}")
        print("ВАЖНО: Сохраните этот ключ в переменных окружения VEXA_ENCRYPTION_KEY")
    
    # Проверяем и кодируем ключ
    cipher_suite = Fernet(
        ENCRYPTION_KEY.encode('utf-8') if isinstance(ENCRYPTION_KEY, str) 
        else ENCRYPTION_KEY
    )
except Exception as e:
    # Если ключ некорректный - используем сгенерированный
    logging.warning(f"Ошибка инициализации ключа: {e}. Используется сгенерированный ключ.")
    cipher_suite = Fernet(generate_safe_fernet_key())

def encrypt_token(token: str) -> str:
    """
    Безопасное шифрование токена
    """
    try:
        return cipher_suite.encrypt(token.encode()).decode()
    except Exception as e:
        logging.error(f"Ошибка шифрования: {e}")
        return token  # Возвращаем оригинальный токен в случае ошибки

def decrypt_token(encrypted_token: str) -> str:
    """
    Безопасная дешифровка токена
    """
    try:
        return cipher_suite.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logging.error(f"Ошибка дешифровки: {e}")
        return encrypted_token  # Возвращаем оригинальный токен в случае ошибки
    

# Файл vexa/vexa_handlers.py - улучшенная обработка ошибок
def safe_encrypt_token(token: str) -> str:
    """
    Безопасное шифрование токена с обработкой ошибок
    """
    if not token:
        return ""
        
    try:
        return cipher_suite.encrypt(token.encode()).decode()
    except Exception as e:
        logging.error(f"Ошибка шифрования: {e}")
        # Создаем новый шифровщик с корректным ключом
        new_key = Fernet.generate_key()
        new_cipher = Fernet(new_key)
        
        # Сохраняем новый ключ в переменную окружения
        os.environ["VEXA_ENCRYPTION_KEY"] = new_key.decode()
        logging.info(f"Создан новый ключ шифрования: {new_key.decode()}")
        
        # Пробуем зашифровать с новым ключом
        try:
            return new_cipher.encrypt(token.encode()).decode()
        except Exception as e2:
            logging.error(f"Повторная ошибка шифрования: {e2}")
            return token  # В крайнем случае возвращаем токен без шифрования