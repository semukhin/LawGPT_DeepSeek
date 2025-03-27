import os
import sys
from dotenv import load_dotenv
import logging
import time
import asyncio

# Импорт из модулей приложения
from app import models, database, auth
from app.chat import router as chat_router
from app.database import get_db
from app.models import User, Thread, Message, Document, VoiceInputLog
        
from app.handlers.deepresearch import router as deepresearch_router
from app.errors import universal_exception_handler, http_exception_handler_custom

from app.config import VEXA_INTEGRATION_ENABLED

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к сторонним пакетам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
VEXA_DIR = os.path.join(BASE_DIR, "vexa")

if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)
if VEXA_DIR not in sys.path:
    sys.path.insert(0, VEXA_DIR)


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Импорт компонентов для Vexa
if VEXA_INTEGRATION_ENABLED:
    try:
        from vexa.vexa_handlers import router as vexa_router
        from vexa.vexa_api_client import VexaApiClient
        from vexa.vexa_integration_models import VexaMeeting, VexaTranscript, VexaIntegrationSettings
    except ImportError as e:
        logger.warning(f"Не удалось импортировать модули Vexa: {e}")
        VEXA_INTEGRATION_ENABLED = False

# Настройка жизненного цикла приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Обработчик событий жизненного цикла приложения."""
    # Старт приложения
    startup_tasks = []
    
    # Проверка соединения с БД
    async def check_db_connection():
        try:
            # Вместо прямого выполнения SQL запроса
            # with database.engine.connect() as conn:
            #     result = conn.execute("SELECT 1")
            
            # Используйте правильный асинхронный подход:
            from sqlalchemy import text
            with database.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                conn.commit()  # Если нужно
            
            logger.info("Соединение с PostgreSQL успешно установлено")
        except Exception as e:
            logger.error(f"Ошибка соединения с PostgreSQL: {str(e)}")
    

        
    # Создаем задачи инициализации
    startup_tasks.append(asyncio.create_task(check_db_connection()))
    
    # Ожидаем завершения задач инициализации
    await asyncio.gather(*startup_tasks)
    
    yield  # Приложение работает здесь
    
    # Действия при завершении
    logger.info("Приложение завершает работу")

# Инициализация FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description="API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0",
    lifespan=lifespan
)

# Инициализация роутера API
api_router = APIRouter(prefix="/api", tags=["api"])

# ==================== MIDDLEWARE ====================

# Middleware для логирования запросов и добавления Process-Time
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Middleware для логирования всех запросов и времени выполнения"""
    start_time = time.time()
    
    # Получаем клиентский IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    
    # Логируем входящий запрос
    logger.info(f"Запрос {request.method} {request.url.path} от {client_ip}")
    
    # Обрабатываем запрос
    response = await call_next(request)
    
    # Вычисляем время обработки
    process_time = time.time() - start_time
    
    # Добавляем заголовок с временем обработки
    response.headers["X-Process-Time"] = str(process_time)
    
    # Логируем ответ
    logger.info(
        f"Ответ {request.method} {request.url.path} - {response.status_code} "
        f"({process_time:.4f} сек)"
    )
    
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

# Middleware для обработки исключений
@app.middleware("http")
async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Логируем ошибку
        logging.error(f"Необработанная ошибка: {str(e)}", exc_info=True)
        
        # Возвращаем структурированный ответ
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(e),
                "path": request.url.path,
                "timestamp": datetime.now().isoformat()
            }
        )

# Регистрация обработчиков ошибок
app.add_exception_handler(Exception, universal_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler_custom)
app.add_exception_handler(RequestValidationError, universal_exception_handler)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Подключение папки frontend для раздачи статических файлов
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# ==================== ЭНДПОИНТЫ ====================

# API endpoints
@app.get("/api/ping")
async def ping_api():
    """Проверка доступности сервера"""
    return {"status": "ok", "message": "pong", "timestamp": datetime.now().isoformat()}

@app.get("/ping")
async def ping():
    """Старый endpoint для совместимости"""
    return {"message": "pong"}

@app.get("/api/health")
async def health_check():
    """Проверка здоровья всех компонентов системы"""
    health_data = {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Проверка БД
    try:
        with database.engine.connect() as conn:
            conn.execute("SELECT 1")
        health_data["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_data["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "degraded"
    
    # Проверка Elasticsearch
    try:
        from app.config import es
        if es:
            es_health = es.cluster.health()
            health_data["components"]["elasticsearch"] = {
                "status": "healthy" if es_health['status'] in ['green', 'yellow'] else "degraded",
                "cluster_status": es_health['status']
            }
        else:
            health_data["components"]["elasticsearch"] = {"status": "disabled"}
    except Exception as e:
        health_data["components"]["elasticsearch"] = {"status": "unhealthy", "error": str(e)}
        health_data["status"] = "degraded"
    
    # Проверка Vexa API (если интеграция включена)
    if VEXA_INTEGRATION_ENABLED:
        try:
            vexa_client = VexaApiClient()
            connection_ok = await vexa_client.check_connection()
            health_data["components"]["vexa_api"] = {
                "status": "healthy" if connection_ok else "degraded"
            }
        except Exception as e:
            health_data["components"]["vexa_api"] = {"status": "unhealthy", "error": str(e)}
            health_data["status"] = "degraded"
    
    return health_data

@app.get("/api/stats", dependencies=[Depends(auth.get_current_user)])
async def get_usage_statistics(db: Session = Depends(get_db)):
    """Получение статистики использования системы"""
    # Получаем основные показатели использования
    user_count = db.query(func.count(User.id)).scalar()
    thread_count = db.query(func.count(Thread.id)).scalar()
    message_count = db.query(func.count(Message.id)).scalar()
    document_count = db.query(func.count(Document.id)).scalar()
    
    # Статистика по голосовому вводу
    voice_input_count = db.query(func.count(VoiceInputLog.id)).scalar()
    
    # Статистика по Vexa (если включено)
    vexa_stats = {}
    if VEXA_INTEGRATION_ENABLED:
        try:
            vexa_meeting_count = db.query(func.count(VexaMeeting.id)).scalar()
            vexa_transcript_count = db.query(func.count(VexaTranscript.id)).scalar()
            vexa_settings_count = db.query(func.count(VexaIntegrationSettings.id)).scalar()
            
            vexa_stats = {
                "meetings": vexa_meeting_count,
                "transcripts": vexa_transcript_count,
                "users_with_settings": vexa_settings_count
            }
        except Exception as e:
            vexa_stats = {"error": str(e)}
    
    return {
        "users": user_count,
        "threads": thread_count,
        "messages": message_count,
        "documents": document_count,
        "voice_inputs": voice_input_count,
        "vexa": vexa_stats
    }

@app.get("/api/indexing-status")
async def indexing_status_api():
    """Возвращает текущий статус индексации"""
    return get_indexing_status()

@app.get("/indexing-status")
async def indexing_status_legacy():
    """Старый endpoint для совместимости"""
    return get_indexing_status()

@app.get("/", response_class=FileResponse)
async def read_root():
    """Главная страница приложения"""
    return FileResponse("frontend/index.html")

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info(f"Получен запрос для item_id: {item_id}")
    return {"item_id": item_id}

@app.post("/deep-research/")
async def deep_research(query: str):
    """Эндпоинт для глубокого исследования."""
    from app.services.research_factory import ResearchAdapter
    deep_research_service = ResearchAdapter()
    results = await deep_research_service.research(query)
    return {"results": results}

# ==================== ПОДКЛЮЧЕНИЕ РОУТЕРОВ ====================

# Подключение основных роутеров
app.include_router(chat_router)
app.include_router(auth.router)
app.include_router(deepresearch_router)

# Создание всех таблиц в базе данных
models.Base.metadata.create_all(bind=database.engine)

# Подключение роутера Vexa, если интеграция включена
if VEXA_INTEGRATION_ENABLED:
    try:
        app.include_router(vexa_router)
        logger.info("Роутер Vexa успешно подключен")
    except NameError:
        logger.warning("Роутер Vexa не найден")

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)