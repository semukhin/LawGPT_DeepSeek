from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import MYSQL_DATABASE_URL, POSTGRES_DATABASE_URL
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Используем MySQL для основных данных приложения
try:
    if not MYSQL_DATABASE_URL:
        raise ValueError("MYSQL_DATABASE_URL не определен")
        
    logging.info(f"Попытка подключения к MySQL: {MYSQL_DATABASE_URL.split('@')[1] if '@' in MYSQL_DATABASE_URL else 'URL скрыт'}")
    engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
    connection = engine.connect()
    result = connection.execute(text("SELECT 1"))
    connection.close()
    logging.info(f"✅ Успешное подключение к MySQL БД")
except Exception as e:
    logging.error(f"❌ Ошибка подключения к MySQL: {e}")
    # Фоллбек на SQLite
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logging.warning(f"⚠️ Используется фоллбек на SQLite: {DATABASE_URL}")



# Для хранения данных Elasticsearch/RAG используем PostgreSQL (если настроен)
try:
    # Проверяем, что у нас есть POSTGRES_DATABASE_URL
    if 'POSTGRES_DATABASE_URL' in globals() and POSTGRES_DATABASE_URL:
        es_engine = create_engine(
            POSTGRES_DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        # Проверка соединения
        with es_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logging.info("Успешное подключение к PostgreSQL для хранения данных Elasticsearch")
    else:
        logging.warning("POSTGRES_DATABASE_URL не определен, пропускаем подключение к PostgreSQL")
        es_engine = None
except Exception as e:
    logging.error(f"Ошибка подключения к PostgreSQL для Elasticsearch: {e}")
    es_engine = None # Устанавливаем None чтобы показать, что подключение не удалось


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