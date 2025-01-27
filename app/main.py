from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app import models, database, auth, chat
from app.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.include_router(chat_router)


# Создание всех таблиц в базе данных
models.Base.metadata.create_all(bind=database.engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://176.223.10.159:3000"],  
    allow_credentials=True,  
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Подключение маршрутов авторизации
app.include_router(auth.router)

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

# Запуск приложения
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
