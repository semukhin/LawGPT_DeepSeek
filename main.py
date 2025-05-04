import sys
from dotenv import load_dotenv
import os
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional

# Добавляем путь к директории scripts в путь поиска модулей Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)  # Гарантированно добавляем в начало пути
sys.path.insert(0, BASE_DIR)     # Добавляем корневой каталог

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from app.services.research_factory import ResearchAdapter

try:
    from app.services.es_init import init_elasticsearch_async, get_indexing_status
except ModuleNotFoundError:
    # Создаем заглушки для функций, если модуль недоступен
    logging.warning("Модуль scripts.es_init не найден. Используются заглушки функций.")
    def init_elasticsearch_async():
        logging.warning("Elasticsearch инициализация пропущена (модуль недоступен)")
        return False

    def get_indexing_status():
        return {"status": "unavailable", "error": "Модуль es_init недоступен"}
import time
from contextlib import asynccontextmanager
import asyncio

deep_research_service = ResearchAdapter()

# Загрузка переменных окружения из .env файла
load_dotenv()
# Проверка загрузки переменных окружения
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

# Добавляем путь к сторонним пакетам (third_party) до импорта роутеров
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)

from app import models, database, auth
from app.chat import router as chat_router

# ✅ Единственный экземпляр FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description="API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0"
)

# Монтируем статику для фронтенда
app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format="%(asctime)s - %(levelname)s - %(message)s",  # Формат сообщений
)
logger = logging.getLogger(__name__)  # Создаем логгер для текущего модуля

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

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    logger.info(f"Получен запрос для item_id: {item_id}")
    # Ваш код обработки запроса
    return {"item_id": item_id}

class DeepResearchRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

@app.post("/deep-research/")
async def deep_research(request: DeepResearchRequest):
    """Эндпоинт для глубокого исследования."""
    results = await deep_research_service.research(request.query)
    return {"results": results}

# Подключение роутеров
app.include_router(chat_router, prefix="/api")
app.include_router(auth.router, prefix="/api")


# Создание всех таблиц в базе данных
models.Base.metadata.create_all(bind=database.engine)

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

# Главная страница
@app.get("/", response_class=FileResponse)
async def read_root():
    """Отдаем index.html из папки frontend"""
    return FileResponse("frontend/index.html")

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.get("/indexing-status")
async def indexing_status():
    """Возвращает текущий статус индексации"""
    return get_indexing_status()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Обработчик событий жизненного цикла приложения."""
    # Действия при запуске
    try:
        from sqlalchemy import text
        with database.engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logging.info("Соединение с MySQL успешно установлено")
    except Exception as e:
        logging.error(f"Ошибка соединения с MySQL: {str(e)}")

    # Асинхронная инициализация Elasticsearch
    try:
        if 'init_elasticsearch_async' in globals():
            if init_elasticsearch_async():
                logger.info("Запущена асинхронная инициализация Elasticsearch")
            else:
                logger.warning("Elasticsearch инициализация пропущена. Поиск по базе знаний будет недоступен.")
        else:
            logger.warning("Функция init_elasticsearch_async недоступна. Elasticsearch не будет инициализирован.")
    except Exception as e:
        logger.warning(f"Ошибка при инициализации Elasticsearch: {str(e)}. Приложение продолжит работу без поддержки поиска.")

    yield  # Здесь можно добавить код, который будет выполняться во время работы приложения

    # Действия при завершении
    logger.info("Приложение завершает работу")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)