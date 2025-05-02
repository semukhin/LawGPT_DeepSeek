"""
Конфигурационный файл для приложения.
Содержит настройки API, базы данных и других компонентов.
"""
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
import logging
from elasticsearch import Elasticsearch
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ===== PostgreSQL Configuration (для RAG ElasticSearch) =====
PG_DB_HOST = os.getenv("DB_HOST")
PG_DB_PORT = os.getenv("DB_PORT")
PG_DB_NAME = os.getenv("DB_NAME")
PG_DB_USER = os.getenv("DB_USER")
PG_DB_PASSWORD = os.getenv("DB_PASSWORD")

# PostgreSQL конфигурация для Elasticsearch
PG_DB_CONFIG = {
    "host": PG_DB_HOST,
    "port": int(PG_DB_PORT) if PG_DB_PORT else None,
    "database": PG_DB_NAME,
    "user": PG_DB_USER,
    "password": PG_DB_PASSWORD
}

# Формируем строку подключения к PostgreSQL
if all([PG_DB_HOST, PG_DB_PORT, PG_DB_NAME, PG_DB_USER, PG_DB_PASSWORD]):
    PG_DB_PASSWORD_ENCODED = quote_plus(PG_DB_PASSWORD)
    POSTGRES_DATABASE_URL = f"postgresql+psycopg2://{PG_DB_USER}:{PG_DB_PASSWORD_ENCODED}@{PG_DB_HOST}:{PG_DB_PORT}/{PG_DB_NAME}"
else:
    POSTGRES_DATABASE_URL = None

# ===== MySQL Configuration (основная БД) =====
MYSQL_DB_USER = os.getenv("DB_USER_MYSQL")
MYSQL_DB_PASSWORD = os.getenv("DB_PASSWORD_MYSQL")
MYSQL_DB_HOST = os.getenv("DB_HOST_MYSQL")
MYSQL_DB_PORT = os.getenv("DB_PORT_MYSQL")
MYSQL_DB_NAME = os.getenv("DB_NAME_MYSQL")

# Формируем строку подключения к MySQL
if all([MYSQL_DB_USER, MYSQL_DB_PASSWORD, MYSQL_DB_HOST, MYSQL_DB_PORT, MYSQL_DB_NAME]):
    MYSQL_DB_PASSWORD_ENCODED = quote_plus(MYSQL_DB_PASSWORD)
    MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_DB_USER}:{MYSQL_DB_PASSWORD_ENCODED}@{MYSQL_DB_HOST}:{MYSQL_DB_PORT}/{MYSQL_DB_NAME}"
else:
    MYSQL_DATABASE_URL = None

# Основной URL для базы данных (используется в приложении)
DATABASE_URL = MYSQL_DATABASE_URL

# ===== Elasticsearch Configuration =====
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USER = os.getenv("ES_USER", None)
ES_PASS = os.getenv("ES_PASS", None)
ELASTICSEARCH_URL = ES_HOST

# Инициализация Elasticsearch
es = None
try:
    if ES_USER and ES_PASS and ES_USER.lower() != 'none' and ES_PASS.lower() != 'none':
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3,
            request_timeout=30
        )
    else:
        es = Elasticsearch(
            [ES_HOST],
            retry_on_timeout=True,
            max_retries=3,
            request_timeout=30
        )

    health = es.cluster.health()
    print("Статус кластера Elasticsearch:", health['status'])
except Exception as e:
    logging.error(f"Ошибка подключения к Elasticsearch: {e}")
    print(f"Ошибка подключения к Elasticsearch: {e}")

# ===== JWT Configuration =====
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# ===== AI Provider Configuration =====
AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
USE_SHANDU_RESEARCH_AGENT = os.getenv("USE_SHANDU_RESEARCH_AGENT", "False") == "True"


# ===== Google Configuration =====
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").replace('"', '')
GOOGLE_CX = os.getenv("GOOGLE_CX", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").replace('"', '')
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-preview-03-25")

# ===== Mail Configuration =====
MAIL_SETTINGS = {
    "MAIL_SERVER": os.getenv("MAIL_SERVER"),
    "MAIL_PORT": int(os.getenv("MAIL_PORT", "587")),
    "MAIL_STARTTLS": os.getenv("MAIL_STARTTLS", "True") == "True",
    "MAIL_SSL_TLS": os.getenv("MAIL_SSL_TLS", "False") == "True",
    "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
    "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD"),
    "MAIL_FROM": os.getenv("MAIL_FROM"),
}

# ===== Quality Monitoring Configuration =====
RESPONSE_QUALITY_MONITORING = {
    "enabled": os.getenv("RESPONSE_QUALITY_MONITORING_ENABLED", "True") == "True",
    "save_queries": os.getenv("RESPONSE_QUALITY_MONITORING_SAVE_QUERIES", "True") == "True",
    "save_responses": os.getenv("RESPONSE_QUALITY_MONITORING_SAVE_RESPONSES", "True") == "True",
    "feedback_enabled": os.getenv("RESPONSE_QUALITY_MONITORING_FEEDBACK_ENABLED", "True") == "True",
    "minimum_references": int(os.getenv("RESPONSE_QUALITY_MONITORING_MINIMUM_REFERENCES", "3")),
    "log_directory": os.getenv("RESPONSE_QUALITY_MONITORING_LOG_DIRECTORY", "quality_logs")
}

# ===== Indexing Configuration =====
INDEXING_INTERVAL = int(os.getenv('INDEXING_INTERVAL', '48'))

# ===== Elasticsearch Indices =====
ES_INDICES = {
    "ruslawod_chunks": "ruslawod_chunks_index",
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index", 
    "legal_articles": "legal_articles_index",
    "procedural_forms": "procedural_forms_index"
}

