from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import POSTGRES_DATABASE_URL, MYSQL_DATABASE_URL

# Используем MySQL для основных данных приложения
DATABASE_URL = MYSQL_DATABASE_URL

# Создайте объект engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Для Elasticsearch/RAG (если нужно)
es_engine = create_engine(
    POSTGRES_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Создайте объект SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()