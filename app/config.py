"""
Конфигурационный файл для приложения.
Содержит настройки API, базы данных и других компонентов.
"""
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer

# Загружаем переменные окружения из .env файла
load_dotenv()


# JWT настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

# Схема аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Конфигурация базы данных
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./lawgpt.db")


# Конфигурация безопасности
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_replace_in_production")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# API ключи
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")



# Ключи Google Custom Search
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")

# Настройки ElasticSearch
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

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
AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")  # openai, vertex, deepseek