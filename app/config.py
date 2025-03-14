"""
Конфигурационный файл для приложения.
Содержит настройки API, базы данных и других компонентов.
"""
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
import logging
from elasticsearch import Elasticsearch

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define database variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Construct database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Elasticsearch configuration
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ES_USER = os.getenv('ES_USER')
ES_PASS = os.getenv('ES_PASS')

# Инициализация Elasticsearch
es = None
try:
    es = Elasticsearch(
        [ELASTICSEARCH_URL],
        basic_auth=(ES_USER, ES_PASS) if ES_USER and ES_PASS else None,
        retry_on_timeout=True,
        max_retries=3
    )
    health = es.cluster.health()
    print("Статус кластера:", health['status'])
except Exception as e:
    print(f"Ошибка подключения к Elasticsearch: {e}")
    # Можно добавить логирование вместо print

# JWT настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# MySQL Configuration
DB_USER_MYSQL = os.getenv("DB_USER_MYSQL", "default_user")
DB_PASSWORD_MYSQL = os.getenv("DB_PASSWORD_MYSQL", "default_password")
DB_HOST_MYSQL = os.getenv("DB_HOST_MYSQL", "194.87.243.188")  # Ваш хост MySQL
DB_PORT_MYSQL = os.getenv("DB_PORT_MYSQL", "3306")
DB_NAME_MYSQL = os.getenv("DB_NAME_MYSQL", "default_db")

MYSQL_DATABASE_URL = f"mysql+pymysql://{DB_USER_MYSQL}:{DB_PASSWORD_MYSQL}@{DB_HOST_MYSQL}:{DB_PORT_MYSQL}/{DB_NAME_MYSQL}"


# PostgreSQL Configuration
POSTGRES_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DB_CONFIG = {
    "host": DB_HOST,
    "port": int(DB_PORT),
    "database": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD
}

# Конфигурация безопасности
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

# API ключи и настройки DeepSeek
USE_SHANDU_RESEARCH_AGENT = os.environ.get("USE_SHANDU_RESEARCH_AGENT", "False") == "True"

# Для Shandu и OpenAI 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# Новые эндпоинты для DeepSeek:
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_CHAT_COMPLETION_URL = os.environ.get("DEEPSEEK_CHAT_COMPLETION_URL", "https://api.deepseek.com/api/create-chat-completion")
DEEPSEEK_COMPLETION_URL = os.environ.get("DEEPSEEK_COMPLETION_URL", "https://api.deepseek.com/api/create-completion")
DEEPSEEK_LIST_MODELS_URL = os.environ.get("DEEPSEEK_LIST_MODELS_URL", "https://api.deepseek.com/api/list-models")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner")

# Ключи Google Custom Search
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")

# Настройки почты
MAIL_SETTINGS = {
    "MAIL_SERVER": os.environ.get("MAIL_SERVER", ""),
    "MAIL_PORT": int(os.getenv("MAIL_PORT", "587")),
    "MAIL_STARTTLS": os.getenv("MAIL_STARTTLS", "True") == "True",
    "MAIL_SSL_TLS": os.getenv("MAIL_SSL_TLS", "False") == "True",
    "MAIL_USERNAME": os.getenv("MAIL_USERNAME", ""),
    "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD", ""),
    "MAIL_FROM": os.getenv("MAIL_FROM", ""),
}

# Настройки мониторинга качества
RESPONSE_QUALITY_MONITORING = {
    "enabled": os.environ.get("RESPONSE_QUALITY_MONITORING_ENABLED", "True") == "True",
    "save_queries": os.environ.get("RESPONSE_QUALITY_MONITORING_SAVE_QUERIES", "True") == "True",
    "save_responses": os.environ.get("RESPONSE_QUALITY_MONITORING_SAVE_RESPONSES", "True") == "True",
    "feedback_enabled": os.environ.get("RESPONSE_QUALITY_MONITORING_FEEDBACK_ENABLED", "True") == "True",
    "minimum_references": int(os.environ.get("RESPONSE_QUALITY_MONITORING_MINIMUM_REFERENCES", "3")),
    "log_directory": os.environ.get("RESPONSE_QUALITY_MONITORING_LOG_DIRECTORY", "quality_logs")
}

# Настройки AI сервиса (переключение между разными провайдерами)
AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")  # Возможные значения: openai, vertex, deepseek

# Интервал индексации
INDEXING_INTERVAL = int(os.getenv('INDEXING_INTERVAL', 48))

# Словарь индексов
ES_INDICES = {
    "ruslawod_chunks": "ruslawod_chunks_index",
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index", 
    "legal_articles": "legal_articles_index"
}
