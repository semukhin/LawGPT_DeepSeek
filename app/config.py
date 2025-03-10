"""
Конфигурационный файл для приложения.
Содержит настройки API, базы данных и других компонентов.
"""
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from fastapi.security import OAuth2PasswordBearer
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загружаем переменные окружения из .env файла
load_dotenv()

# JWT настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Конфигурация базы данных
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./lawgpt.db")

# Конфигурация безопасности
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_replace_in_production")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# API ключи и настройки DeepSeek
USE_SHANDU_RESEARCH_AGENT = os.environ.get("USE_SHANDU_RESEARCH_AGENT", "False") == "True"


# Для Shandu и OpenAI 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")

# Новые эндпоинты для DeepSeek:
DEEPSEEK_CHAT_COMPLETION_URL = os.environ.get("DEEPSEEK_CHAT_COMPLETION_URL", "https://api.deepseek.com/api/create-chat-completion")
DEEPSEEK_COMPLETION_URL = os.environ.get("DEEPSEEK_COMPLETION_URL", "https://api.deepseek.com/api/create-completion")
DEEPSEEK_LIST_MODELS_URL = os.environ.get("DEEPSEEK_LIST_MODELS_URL", "https://api.deepseek.com/api/list-models")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner")


# Базовый URL для DeepSeek API
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")



# Ключи Google Custom Search
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")


# Настройки почты
MAIL_SETTINGS = {
    "MAIL_SERVER": os.environ.get("MAIL_SERVER", ""),
    "MAIL_PORT": int(os.environ.get("MAIL_PORT", "587")),
    "MAIL_STARTTLS": os.environ.get("MAIL_STARTTLS", "True") == "True",
    "MAIL_SSL_TLS": os.environ.get("MAIL_SSL_TLS", "False") == "True",
    "MAIL_USERNAME": os.environ.get("MAIL_USERNAME", ""),
    "MAIL_PASSWORD": os.environ.get("MAIL_PASSWORD", ""),
    "MAIL_FROM": os.environ.get("MAIL_FROM", ""),
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


# Настройки ElasticSearch
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

# Elasticsearch конфигурация
ES_HOST = os.getenv('ES_HOST', 'http://localhost:9200')
ES_USER = os.getenv('ES_USER')
ES_PASS = os.getenv('ES_PASS')

# PostgreSQL конфигурация
DB_CONFIG = {
    "host": os.getenv('DB_HOST'),
    "port": int(os.getenv('DB_PORT', 5432)),
    "database": os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD')
}

# Интервал индексации
INDEXING_INTERVAL = int(os.getenv('INDEXING_INTERVAL', 48))

# Словарь индексов
ES_INDICES = {
    "ruslawod_chunks": "ruslawod_chunks_index",
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index", 
    "legal_articles": "legal_articles_index"
}

if __name__ == "__main__":
    try:
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3
        )
        health = es.cluster.health()
        print("Статус кластера:", health['status'])
    except Exception as e:
        print("Ошибка подключения:", str(e))
