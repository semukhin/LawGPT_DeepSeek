import sys
from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI, Request, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from sqlalchemy.orm import Session

# Добавляем путь к директории scripts в путь поиска модулей Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)  # Гарантированно добавляем в начало пути
sys.path.insert(0, BASE_DIR)     # Добавляем корневой каталог

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from app.utils.logger import get_logger
from app.services.deepresearch_service import deep_research_service

# Инициализируем логгер
logger = get_logger()

try:
    from app.services.es_init import init_elasticsearch_async, get_indexing_status
except ModuleNotFoundError:
    # Создаем заглушки для функций, если модуль недоступен
    logger.warning("Модуль scripts.es_init не найден. Используются заглушки функций.")
    def init_elasticsearch_async():
        logger.warning("Elasticsearch инициализация пропущена (модуль недоступен)")
        return False

    def get_indexing_status():
        return {"status": "unavailable", "error": "Модуль es_init недоступен"}

import time
from contextlib import asynccontextmanager
import asyncio

# Загрузка переменных окружения из .env файла
load_dotenv()
# Проверка загрузки переменных окружения
logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

# Добавляем путь к сторонним пакетам (third_party) до импорта роутеров
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from app.models import PromptLog, ResearchResult, User, Thread, Message
from app.database import Base, engine, get_db
print("Импорт auth_router ОК")
from app.auth import router as auth_router, get_current_user
print("Импорт chat_router ОК")
from app.chat import router as chat_router

# ✅ Единственный экземпляр FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description="API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0"
)

# --- Диагностика: вывод всех маршрутов ---
for route in app.routes:
    print(f"{route.path} -> {route.methods}")

# Монтирую папку frontend как корень сайта
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

# Отключаем отладочные сообщения для multipart parser
logging.getLogger('fastapi.multipart.multipart').setLevel(logging.INFO)
logging.getLogger('multipart.multipart').setLevel(logging.INFO)
# Отключаем сообщения о перезагрузке uvicorn
logging.getLogger('uvicorn.reload').setLevel(logging.WARNING)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Запрос {request.method} {request.url.path} обработан за {process_time:.2f}с")
    return response

# Middleware для установки правильной кодировки в HTTP заголовках
@app.middleware("http")
async def add_charset_middleware(request: Request, call_next):
    response = await call_next(request)

    # Добавляем charset=utf-8 в заголовки Content-Type, если его нет
    content_type = response.headers.get("content-type")
    if content_type and "charset" not in content_type.lower():
        if "text/html" in content_type:
            response.headers["content-type"] = f"{content_type}; charset=utf-8"
        elif "application/json" in content_type:
            response.headers["content-type"] = f"{content_type}; charset=utf-8"

    return response

# --- Переношу вспомогательные эндпоинты под /api ---
from fastapi import APIRouter
api_router = APIRouter()

@api_router.get("/ping")
async def ping():
    return {"message": "pong"}

@api_router.get("/indexing-status")
async def indexing_status():
    """Возвращает текущий статус индексации"""
    return get_indexing_status()

class DeepResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

@api_router.post("/deep-research/")
async def deep_research(
    request: DeepResearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Эндпоинт для глубокого исследования."""
    # 1. Сохраняем сообщение пользователя
    thread_id = request.thread_id or f"thread_{uuid.uuid4().hex}"
    # Проверяем, существует ли тред, если нет — создаём
    thread = db.query(Thread).filter_by(id=thread_id, user_id=current_user.id).first()
    if not thread:
        thread = Thread(id=thread_id, user_id=current_user.id)
        db.add(thread)
        db.commit()
    user_message = Message(thread_id=thread_id, role="user", content=request.query)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    # 2. Запускаем исследование с передачей всех параметров
    result = await deep_research_service.research(
        request.query,
        thread_id=thread_id,
        user_id=current_user.id,
        db=db,
        message_id=user_message.id
    )
    # 3. Сохраняем ответ ассистента
    assistant_message = Message(thread_id=thread_id, role="assistant", content=result.analysis)
    db.add(assistant_message)
    db.commit()
    # 4. Возвращаем результат в старом и новом формате
    return {"assistant_response": result.analysis, "results": result}

@api_router.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info(f"Получен запрос для item_id: {item_id}", context={"item_id": item_id})
    return {"item_id": item_id}

# --- Подключаю api_router ---
app.include_router(api_router, prefix="/api")
print("api_router подключён")
app.include_router(chat_router, prefix="/api")
print("chat_router подключён")
app.include_router(auth_router, prefix="/api")
print("auth_router подключён")

# --- Fallback для SPA: отдаём index.html на все не-API-запросы ---
from starlette.responses import FileResponse as StarletteFileResponse
from starlette.requests import Request as StarletteRequest

@app.middleware("http")
async def spa_fallback(request: StarletteRequest, call_next):
    # Если путь начинается с /api или /static, отдаём как есть
    if request.url.path.startswith("/api") or request.url.path.startswith("/static"):
        return await call_next(request)
    # Если файл реально существует, отдаём его
    static_path = os.path.join("frontend", request.url.path.lstrip("/"))
    if os.path.isfile(static_path):
        return StarletteFileResponse(static_path)
    # Иначе отдаём index.html (SPA fallback)
    return StarletteFileResponse("frontend/index.html")

# Создание всех таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Настройка CORS с указанием кодировки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В режиме разработки разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Expose-Headers",
    ],
    expose_headers=["X-Process-Time", "Content-Disposition"]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Обработчик событий жизненного цикла приложения."""
    # Действия при запуске
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Соединение с MySQL успешно установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка соединения с MySQL: {str(e)}")

    # Асинхронная инициализация Elasticsearch
    try:
        if 'init_elasticsearch_async' in globals():
            if init_elasticsearch_async():
                logger.info("✅ Запущена асинхронная инициализация Elasticsearch")
            else:
                logger.warning("⚠️ Elasticsearch инициализация пропущена. Поиск по базе знаний будет недоступен.")
        else:
            logger.warning("⚠️ Функция init_elasticsearch_async недоступна. Elasticsearch не будет инициализирован.")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при инициализации Elasticsearch: {str(e)}. Приложение продолжит работу без поддержки поиска.")

    yield  # Здесь можно добавить код, который будет выполняться во время работы приложения

    # Действия при завершении
    logger.info("Приложение завершает работу")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)