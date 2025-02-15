from fastapi import FastAPI
from app.utils import measure_time
from fastapi.responses import HTMLResponse
from app import models, database, auth, chat
from app.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ✅ Единственный экземпляр FastAPI
app = FastAPI()

# Подключение маршрутов
app.include_router(chat_router)
app.include_router(auth.router)

# Создание всех таблиц в базе данных
models.Base.metadata.create_all(bind=database.engine)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://176.223.10.159:3000", "188.138.252.71"],  
    allow_credentials=True,  
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# ✅ Главная страница с замером времени
@measure_time
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


@measure_time
@app.get("/ping")
async def ping():
    return {"message": "pong"}


# ✅ Запуск сервера FastAPI
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
