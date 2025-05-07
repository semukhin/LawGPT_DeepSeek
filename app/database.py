from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import MYSQL_DATABASE_URL, POSTGRES_DATABASE_URL
from app.utils.logger import get_logger
import os
from urllib.parse import quote_plus

# Инициализируем логгер
logger = get_logger()

# Используем MySQL для основных данных приложения
try:
    if not MYSQL_DATABASE_URL:
        raise ValueError("MYSQL_DATABASE_URL не определен")
        
    logger.info(f"Попытка подключения к MySQL: {MYSQL_DATABASE_URL.split('@')[1] if '@' in MYSQL_DATABASE_URL else 'URL скрыт'}")
    engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
    connection = engine.connect()
    result = connection.execute(text("SELECT 1"))
    connection.close()
    logger.info("✅ Успешное подключение к MySQL БД")
except Exception as e:
    logger.error(f"❌ Ошибка подключения к MySQL: {e}")
    # Фоллбек на SQLite
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logger.warning(f"⚠️ Используется фоллбек на SQLite: {DATABASE_URL}")



# Для хранения данных Elasticsearch/RAG используем PostgreSQL (если настроен)
try:
    # Проверяем, что у нас есть все необходимые переменные окружения для PostgreSQL
    PG_DB_HOST = os.getenv('DB_HOST')
    PG_DB_PORT = os.getenv('DB_PORT', '5432')
    PG_DB_NAME = os.getenv('DB_NAME')
    PG_DB_USER = os.getenv('DB_USER')
    PG_DB_PASSWORD = os.getenv('DB_PASSWORD')

    if all([PG_DB_HOST, PG_DB_PORT, PG_DB_NAME, PG_DB_USER, PG_DB_PASSWORD]):
        PG_DB_PASSWORD_ENCODED = quote_plus(PG_DB_PASSWORD)
        POSTGRES_DATABASE_URL = f"postgresql+psycopg2://{PG_DB_USER}:{PG_DB_PASSWORD_ENCODED}@{PG_DB_HOST}:{PG_DB_PORT}/{PG_DB_NAME}"
        es_engine = create_engine(
            POSTGRES_DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        # Проверка соединения
        with es_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Успешное подключение к PostgreSQL для хранения данных Elasticsearch")
    else:
        logger.warning("❌ Не все переменные окружения для PostgreSQL определены, пропускаем подключение")
        es_engine = None
except Exception as e:
    logger.error(f"❌ Ошибка подключения к PostgreSQL для Elasticsearch: {e}")
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