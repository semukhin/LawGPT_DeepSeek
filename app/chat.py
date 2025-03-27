import tempfile
from openai import OpenAI
import uuid
import os
import re
import logging
import asyncio
from datetime import datetime
from pathlib import Path
import unicodedata

from fastapi import Request, UploadFile, File, Form, HTTPException, FastAPI, APIRouter, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import aiofiles
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Message, Thread, Document
from app.models import User, VoiceInputLog

from app.auth import get_current_user
from app.handlers.web_search import google_search
from app.handlers.ai_request import send_custom_request
from app.handlers.es_law_search import search_law_chunks
from app.handlers.user_doc_request import extract_text_from_any_document
from app.utilities import measure_time, get_url_content
from transliterate import translit

import speech_recognition as sr
from fastapi import File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session

import speech_recognition as sr
from app.utilities import get_speech_recognition_model, get_speech_content_filter
from google.cloud import speech_v1p1beta1 as speech

# Проверка и безопасный импорт Google Cloud Speech
try:
    from google.cloud import speech_v1p1beta1 as speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    logging.warning("Google Cloud Speech библиотека не установлена. Функции распознавания речи будут ограничены.")
    GOOGLE_SPEECH_AVAILABLE = False
    speech = None


# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Инициализация моделей
legal_speech_model = get_speech_recognition_model()
speech_filter = get_speech_content_filter()

# Папки для хранения файлов
UPLOAD_FOLDER = "uploads"
DOCX_FOLDER = "documents_docx"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCX_FOLDER, exist_ok=True)

# OAuth2 схема для авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Инициализация FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description="API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0"
)

router = APIRouter()

# ===================== Модели запросов =====================

class ChatRequest(BaseModel):
    query: str

# ===================== Вспомогательные функции =====================

@measure_time
async def process_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Сохраняет загруженный файл и извлекает из него текст.
    
    Args:
        file: Загруженный файл от пользователя
        
    Returns:
        tuple[str, str]: Кортеж из (путь_к_файлу, извлеченный_текст)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_filename = file.filename.replace(" ", "_")
    filename_no_ext, file_extension = os.path.splitext(original_filename)
    transliterated_filename = translit(filename_no_ext, 'ru', reversed=True)

    new_filename = f"{timestamp}_{transliterated_filename}{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, new_filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        await buffer.write(await file.read())

    logging.info("Файл сохранён: %s", file_path)

    extracted_text = extract_text_from_any_document(file_path)
    logging.info("Извлечённый текст из файла: %s", extracted_text[:200])  # Показываем первые 200 символов

    return file_path, extracted_text


def fix_encoding(text):
    """Пытается исправить проблемы с кодировкой"""
    if not isinstance(text, str):
        return text
        
    # Проверка на неправильную кодировку
    if any(ord(c) > 127 for c in text) and 'Ð' in text:
        # Текст уже в неправильной кодировке, пытаемся исправить
        try:
            # Пробуем разные комбинации кодировок
            for source in ['latin1', 'cp1252', 'iso-8859-1']:
                for target in ['utf-8', 'cp1251']:
                    try:
                        fixed = text.encode(source).decode(target)
                        if 'а' in fixed or 'А' in fixed:  # Если есть русские буквы
                            return fixed
                    except:
                        pass
        except:
            pass
    return text


# ===================== Эндпоинты чата =====================
@measure_time
@router.post("/api/chat/{thread_id}")
async def chat_in_thread(
    request: Request,
    thread_id: str,
    query: str = Form(None),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Основной эндпоинт для общения с ассистентом.
    Если загружен файл — извлекает текст и передает в DeepResearch.
    Иначе анализирует запрос и при необходимости использует поиск в Elasticsearch, Гаранте или интернете.
    """
    # Проверка и обработка случая, когда query равен None
    if query is None and file is None:
        raise HTTPException(
            status_code=400, 
            detail="Необходимо предоставить текстовый запрос или файл"
        )
    
    # Если query None, но файл есть, устанавливаем пустой запрос
    query = query or ""
    
    # 1. Проверка и нормализация текста запроса
    try:
        # Исправляем кодировку запроса
        query = fix_encoding(query)
        
        # Нормализация Unicode для решения проблем с составными символами
        query = unicodedata.normalize('NFC', query)
        
        # Логируем запрос, ограничивая длину для читаемости
        log_query = query[:100] + "..." if len(query) > 100 else query
        logging.info(f"📥 Получен запрос: thread_id={thread_id}, query='{log_query}'")
    except Exception as e:
        logging.error(f"❌ Ошибка декодирования запроса: {str(e)}")
        # Попытка исправить кодировку, если она неправильная
        try:
            query = query.encode('latin1').decode('utf-8')
            logging.info(f"✅ Исправлена кодировка запроса")
        except Exception as e:
            logging.error(f"❌ Не удалось исправить кодировку: {str(e)}")
            query = ""  # Устанавливаем пустой запрос
        
    # 2. Проверка кодировки перед дальнейшей обработкой
    if isinstance(query, str):
        # Убедимся, что query действительно строка в UTF-8
        try:
            query.encode('utf-8').decode('utf-8')
        except UnicodeError:
            logging.warning("⚠️ Проблема с кодировкой в тексте запроса, пытаемся исправить")
            # Дополнительная попытка исправить кодировку
            try:
                query = query.encode('latin1').decode('utf-8', errors='replace')
            except:
                pass

    # 3. Проверка и исправление thread_id
    # Если thread_id буквально равен 'thread_id' или не соответствует формату UUID
    uuid_pattern = re.compile(r'^thread_[0-9a-f]{32}$')
    if thread_id == 'thread_id' or (not uuid_pattern.match(thread_id) and not thread_id.startswith('existing_')):
        # Создаем новый thread_id
        new_thread_id = f"thread_{uuid.uuid4().hex}"
        logging.info(f"⚠️ Получен некорректный thread_id: {thread_id}. Создан новый: {new_thread_id}")
        thread_id = new_thread_id
    
    # 4. Поиск или создание треда
    thread = db.query(Thread).filter_by(id=thread_id, user_id=current_user.id).first()
    if not thread:
        logging.info("🔑 Тред не найден. Создаем новый.")
        thread = Thread(id=thread_id, user_id=current_user.id)
        db.add(thread)
        db.commit()

    # 5. Обработка файла (если есть)
    if file:
        logging.info(f"📄 Обработка загруженного файла: {file.filename}")
        file_path, extracted_text = await process_uploaded_file(file)

        # Создаем запрос с учетом содержимого документа
        enhanced_query = f"{query}\n\nДокумент содержит:\n{extracted_text[:2000]}..."
        
        # Передаем thread_id и db в send_custom_request
        assistant_response = await send_custom_request(
            user_query=enhanced_query, 
            thread_id=thread_id,
            db=db
        )

        db.add_all([
            Message(thread_id=thread_id, role="user", content=f"Документ: {file.filename}"),
            Message(thread_id=thread_id, role="assistant", content=assistant_response)
        ])
        db.commit()

        return {
            "assistant_response": assistant_response,
            "recognized_text": extracted_text,
            "file_name": file.filename,
            "file_path": file_path
        }
    else:
        # 6. Обработка текстового запроса
        logging.info("💬 Обработка текстового запроса без файла.")

        # Передаем thread_id и db в send_custom_request
        assistant_response = await send_custom_request(
            user_query=query, 
            thread_id=thread_id,
            db=db
        )

        # Сохраняем сообщения
        db.add_all([
            Message(thread_id=thread_id, role="user", content=query),
            Message(thread_id=thread_id, role="assistant", content=assistant_response)
        ])
        db.commit()
        if not thread.first_message and query:
            thread.first_message = query[:100] + ('...' if len(query) > 100 else '')
            db.commit()

        return {"assistant_response": assistant_response}
    
# ===================== Эндпоинты работы с тредами =====================

@measure_time
@router.post("/api/create_thread")
async def create_thread(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создает новый тред для пользователя."""
    import uuid
    new_thread_id = f"thread_{uuid.uuid4().hex}"
    thread = Thread(id=new_thread_id, user_id=current_user.id)
    db.add(thread)
    db.commit()
    logging.info(f"🆕 Создан новый тред: {new_thread_id}")
    return {"thread_id": new_thread_id}


@measure_time
@router.get("/api/chat/threads")
async def get_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    threads = db.query(Thread).filter_by(user_id=current_user.id).order_by(Thread.created_at.desc()).all()
    
    # Добавляем first_message в возвращаемые данные
    return {
        "threads": [
            {
                "id": t.id, 
                "created_at": t.created_at, 
                "first_message": t.first_message
            } for t in threads
        ]
    }


@measure_time
@router.get("/api/messages/{thread_id}")
async def get_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает сообщения из выбранного треда."""
    messages = db.query(Message).filter_by(thread_id=thread_id).order_by(Message.created_at).all()
    return {"messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]}


# ===================== Эндпоинты для загрузки и скачивания файлов =====================

@measure_time
@router.post("/api/upload_file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    """Загружает файл и сохраняет в базе данных."""
    if not file.filename.lower().endswith(('.docx', '.pdf')):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx и .pdf.")

    file_path, _ = await process_uploaded_file(file)
    
    new_document = Document(user_id=current_user.id, file_path=file_path)
    db.add(new_document)
    db.commit()

    logging.info("📥 Файл '%s' успешно загружен.", file.filename)
    return {"message": "Файл успешно загружен.", "file_path": file_path}


@router.get("/api/download/{filename}")
async def download_document(filename: str):
    """Позволяет скачать документ."""
    file_path = os.path.join(DOCX_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Документ не найден.")

    logging.info("📤 Отправка файла '%s' на скачивание.", filename)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )



async def process_voice_input(
    file: UploadFile = File(...),
    language: str = Form('ru-RU'),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обработчик голосового ввода с машинным обучением
    """
    # Список поддерживаемых языков
    SUPPORTED_LANGUAGES = {
        'ru-RU': 'Русский',
        'en-US': 'Английский',
        'uk-UA': 'Украинский',
        'de-DE': 'Немецкий',
        'fr-FR': 'Французский', 
        'es-ES': 'Испанский'
    }
    
    # Проверка корректности языка
    if language not in SUPPORTED_LANGUAGES:
        language = 'ru-RU'  # По умолчанию русский
    
    try:
        # Создаем временный файл для аудио
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_filepath = temp_file.name
            temp_file.write(await file.read())
        
        # Предобработка аудио с помощью ML-модели
        ml_prediction = legal_speech_model.predict(temp_filepath)
        
        # Инициализируем распознаватель
        recognizer = sr.Recognizer()
        
        # Список попыток распознавания
        recognition_attempts = [
            ('ru-RU', recognizer.recognize_google),
            ('en-US', recognizer.recognize_google)
        ]
        
        recognized_text = None
        recognition_confidence = 0.0
        
        # Пытаемся распознать речь
        with sr.AudioFile(temp_filepath) as source:
            audio_data = recognizer.record(source)
        
        for attempt_lang, recognition_method in recognition_attempts:
            try:
                recognized_text = recognition_method(audio_data, language=attempt_lang)
                recognition_confidence = 0.9  # Базовая уверенность
                
                # Повышаем уверенность для юридических терминов
                if ml_prediction:
                    recognition_confidence *= 1.2
                
                break
            except (sr.UnknownValueError, sr.RequestError):
                continue
        
        # Если распознавание не удалось
        if not recognized_text:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось распознать речь"
            )
        
        # Анонимизация и цензура текста
        censored_text = speech_filter.censor_text(recognized_text)
        anonymized_text = speech_filter.anonymize_text(censored_text)
        
        # Определение намерения
        intent = speech_filter.detect_intent(anonymized_text)
        
        # Логирование голосового ввода
        voice_input_log = VoiceInputLog(
            user_id=current_user.id,
            language=language,
            audio_duration=len(audio_data.get_wav_data()) / 16000,  # примерная длительность
            audio_size=os.path.getsize(temp_filepath),
            recognition_success=True,
            recognition_confidence=recognition_confidence
        )
        db.add(voice_input_log)
        db.commit()
        
        # Очищаем временный файл
        os.unlink(temp_filepath)
        
        return {
            "text": anonymized_text,
            "language": language,
            "confidence": recognition_confidence,
            "legal_context": ml_prediction,
            "intent": intent
        }
    
    except Exception as e:
        # В случае ошибки удаляем временный файл
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            os.unlink(temp_filepath)
        
        logging.error(f"Ошибка при распознавании речи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при распознавании речи: {str(e)}")


@router.post("/api/chat/{thread_id}/voice-input")
async def handle_voice_input(
    thread_id: str,
    file: UploadFile = File(...),
    language: str = Form('ru-RU'),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await process_voice_input(file, language, current_user, db)


# Функция для инициализации клиента
def get_speech_client():
    if not GOOGLE_SPEECH_AVAILABLE:
        logging.error("Невозможно создать клиент Google Cloud Speech. Библиотека не установлена.")
        return None
    
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        logging.error(f"Ключ credentials не найден: {credentials_path}")
        return None
    
    try:
        return speech.SpeechClient()
    except Exception as e:
        logging.error(f"Ошибка при создании клиента Google Cloud Speech: {e}")
        return None

# Заглушка для функции распознавания, если библиотека недоступна
def recognize_speech_fallback(file_path, language_code='ru-RU'):
    logging.warning("Используется базовое распознавание без Google Cloud")
    # Реализуйте базовное распознавание или верните пустой результат
    return "Распознавание недоступно"

# Основная функция распознавания
def recognize_speech(file_path, language_code='ru-RU'):
    if not GOOGLE_SPEECH_AVAILABLE:
        return recognize_speech_fallback(file_path, language_code)
    
    client = get_speech_client()
    if not client:
        return recognize_speech_fallback(file_path, language_code)
    
    # Существующая логика распознавания
    try:
        with open(file_path, 'rb') as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
            alternative_language_codes=['en-US']
        )
        
        response = client.recognize(config=config, audio=audio)
        
        return response.results[0].alternatives[0].transcript
    except Exception as e:
        logging.error(f"Ошибка при распознавании речи: {e}")
        return recognize_speech_fallback(file_path, language_code)


# ===================== Подключение роутера =====================

app.include_router(router)