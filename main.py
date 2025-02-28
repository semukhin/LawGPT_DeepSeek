import sys, os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.handlers import deepresearch
from app.services.deepresearch_service import DeepResearchService
import logging
import time



# Добавляем путь к сторонним пакетам (third_party) до импорта роутеров
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)

from app import models, database, auth
from app.chat import router as chat_router
from app.handlers import deepresearch  # Импортируем модуль deepresearch

# ✅ Единственный экземпляр FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description="API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0"
)

deep_research_service = DeepResearchService()


# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Формат сообщений
)
logger = logging.getLogger(__name__)  # Создаем логгер для текущего модуля



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



@app.post("/deep-research/")
async def deep_research(query: str):
    """Эндпоинт для глубокого исследования."""
    results = await deep_research_service.research(query)
    return {"results": results}


# Подключение роутеров
app.include_router(chat_router)
app.include_router(auth.router)
# Подключаем роутер для глубокого исследования
app.include_router(deepresearch.router)

# Создание всех таблиц в базе данных
models.Base.metadata.create_all(bind=database.engine)


# Настройка CORS с указанием кодировки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["content-type", "content-length"]
)

# Главная страница
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
        <head>
            <title>Главная страница</title>
        </head>
        <body>
            <h1>Добро пожаловать на сайт!</h1>
            <p>Это главное API-приложение с регистрацией, авторизацией и подтверждением почты.</p>
            <p>Используйте доступные маршруты для взаимодействия с приложением.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
