from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import POSTGRES_DATABASE_URL

# Используем PostgreSQL для основных данных приложения
DATABASE_URL = POSTGRES_DATABASE_URL


# Создаем движок PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Для Elasticsearch/RAG (если нужно)
es_engine = create_engine(
    POSTGRES_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)