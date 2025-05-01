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


# Импорт urllib.parse для корректного кодирования URL
from urllib.parse import quote_plus

# Construct database URL с корректным кодированием
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}" if all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]) else None

# Elasticsearch configuration
ES_HOST = os.environ.get("ES_HOST", "http://localhost:9200")
ELASTICSEARCH_URL = ES_HOST  # Для обратной совместимости
ES_USER = os.environ.get("ES_USER", None)
ES_PASS = os.environ.get("ES_PASS", None)

# Инициализация Elasticsearch
es = None
try:
    # Проверяем наличие учетных данных и их валидность
    if ES_USER and ES_PASS and ES_USER.lower() != 'none' and ES_PASS.lower() != 'none':
        # С авторизацией
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3,
            request_timeout=30
        )
    else:
        # Без авторизации
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

# JWT настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# MySQL Configuration
DB_USER_MYSQL = os.getenv("DB_USER_MYSQL", "gen_user")
DB_PASSWORD_MYSQL = os.getenv("DB_PASSWORD_MYSQL", "Grisha1977!")
DB_HOST_MYSQL = os.getenv("DB_HOST_MYSQL", "194.87.243.188")  
DB_PORT_MYSQL = os.getenv("DB_PORT_MYSQL", "3306")
DB_NAME_MYSQL = os.getenv("DB_NAME_MYSQL", "default_db")

# Формируем строку подключения динамически с корректным кодированием паролей
DB_PASSWORD_MYSQL_ENCODED = quote_plus(DB_PASSWORD_MYSQL) if DB_PASSWORD_MYSQL else ""
MYSQL_DATABASE_URL = f"mysql+pymysql://{DB_USER_MYSQL}:{DB_PASSWORD_MYSQL_ENCODED}@{DB_HOST_MYSQL}:{DB_PORT_MYSQL}/{DB_NAME_MYSQL}"

# Основной URL для базы данных (используется в приложении)
DATABASE_URL = MYSQL_DATABASE_URL

# Настройки пула соединений
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 1800  # 30 минут

# PostgreSQL Configuration
POSTGRES_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# PostgreSQL конфигурация
DB_CONFIG = {
    "host": os.getenv('PG_DB_HOST', os.getenv('DB_HOST')),
    "port": int(os.getenv('PG_DB_PORT', os.getenv('DB_PORT', 5432))), 
    "database": os.getenv('PG_DB_NAME', os.getenv('DB_NAME')),
    "user": os.getenv('PG_DB_USER', os.getenv('DB_USER')),
    "password": os.getenv('PG_DB_PASSWORD', os.getenv('DB_PASSWORD'))
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
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # Возможные значения: openai, deepseek

# Настройки Google AI Studio (Gemini API) для распознавания документов
GEMINI_API_ENABLED = True  # Включаем Google AI Studio
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA_UMauxGiCnZdZvNQS3x9bOokaGdKCi-E")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-preview-03-25")  # Используем версию с предпросмотром для работы с авторскими документами

# Настройки для Google Search API
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "31a742e3d78ce478c")  # Дублирование для совместимости
GOOGLE_SEARCH_ENABLED = os.environ.get("GOOGLE_SEARCH_ENABLED", "True").lower() == "true"

# Настройки для Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA_UMauxGiCnZdZvNQS3x9bOokaGdKCi-E").replace('"', '')
GEMINI_ENABLED = os.environ.get("GEMINI_ENABLED", "True").lower() == "true"

# Расширенный вывод информации для диагностики
print(f"Настройки Google AI Studio: ENABLED={GEMINI_API_ENABLED}, MODEL={GEMINI_MODEL}")
print(f"API ключ Google AI Studio настроен: {bool(GEMINI_API_KEY)}")

# Настройки Google AI Studio удалены из конфигурации

# Интервал индексации
INDEXING_INTERVAL = int(os.getenv('INDEXING_INTERVAL', 48))

# Словарь индексов
ES_INDICES = {
    "ruslawod_chunks": "ruslawod_chunks_index",
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index", 
    "legal_articles": "legal_articles_index",
    "procedural_forms": "procedural_forms_index"
}