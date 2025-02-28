from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL


# Добавляем параметры кодировки в URL соединения
if "mysql" in DATABASE_URL and "charset" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&charset=utf8mb4"
    else:
        DATABASE_URL += "?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"use_unicode": True, "charset": "utf8mb4"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    print("🔍 Инициализация сессии БД...")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()