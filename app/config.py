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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define database variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")




# Elasticsearch configuration
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
ES_HOST = os.environ.get("ES_HOST", ELASTICSEARCH_URL)  
ES_USER = os.environ.get("ES_USER", "elastic")  
ES_PASS = os.environ.get("ES_PASS", "GIkb8BKzkXK7i2blnG2O")

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
SECRET_KEY = os.getenv("SECRET_KEY", "Grisha1977!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Основное подключение для приложения
DATABASE_CONFIG = {
    "host": os.getenv('DB_HOST_V', '147.45.232.224'),
    "port": int(os.getenv('DB_PORT_V', 5432)),
    "database": os.getenv('DB_NAME_V', 'default_db'),
    "user": os.getenv('DB_USER_V', 'gen_user'),
    "password": os.getenv('DB_PASSWORD_V', 'Grisha1977!')
}

# Подключение к PostgreSQL для индексации Elasticsearch
POSTGRES_INDEXING_CONFIG = {
    "host": os.getenv('PG_DB_HOST', '82.97.242.92'),
    "port": int(os.getenv('PG_DB_PORT', 5432)),
    "database": os.getenv('PG_DB_NAME', 'ruslaw_db'),
    "user": os.getenv('PG_DB_USER', 'gen_user'),
    "password": os.getenv('PG_DB_PASSWORD', 'P?!ri#ag5%G1Si')
}

# Построение строки подключения
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

# PostgreSQL Configuration
POSTGRES_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Конфигурация безопасности
SECRET_KEY = os.environ.get("SECRET_KEY", "Grisha1977!")
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


VEXA_INTEGRATION_ENABLED = bool(os.getenv("VEXA_API_KEY") and os.getenv("VEXA_API_KEY") != 'sk-vexa-1234567890')
