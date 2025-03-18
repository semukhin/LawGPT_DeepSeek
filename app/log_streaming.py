"""
Модуль для стриминга логов на фронтенд через WebSocket.
"""
import logging
import asyncio
from typing import List, Dict, Any
from app.websocket_state import connected_clients
from datetime import datetime
from starlette.websockets import WebSocketState


class WebSocketLogHandler(logging.Handler):
    """Обработчик логов для отправки упрощенных сообщений через WebSocket."""
    
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)
        # Форматируем логи в упрощенном виде
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
    def emit(self, record):
        # Пропускаем некоторые логи, которые не нужно показывать пользователю
        if any(skip_term in record.getMessage() for skip_term in 
                ['HEAD http', 'GET http', 'POST http', 'OPTIONS http']):
            return
        
        # Форматируем лог
        log_entry = self.format(record)
        
        # Преобразуем лог для фронтенда
        user_friendly_log = self._simplify_log(log_entry, record)
        
        # Отправляем лог всем подключенным клиентам
        if user_friendly_log:
            asyncio.create_task(self._send_to_clients(user_friendly_log))
    
    
    def _simplify_log(self, log_entry: str, record) -> str:
        """Преобразует детальный лог в упрощенную версию для пользователя."""
        msg = record.getMessage()
        
        # Включаем прямое логирование для отладки
        print(f"LOG MESSAGE: {msg}")
        
        # Расширенные шаблоны для соответствия
        if any(pattern in msg for pattern in ["Начинаем исследование", "исследование", "DeepResearch", "запрос", "Длина запроса"]):
            # Пытаемся извлечь длину запроса, если есть
            if "Длина запроса:" in msg:
                symbols_count = msg.split("Длина запроса:")[1].split("символов")[0].strip()
                return f"📋 Подготовка запроса ({symbols_count} символов)"
            return f"📋 Подготовка запроса"
            
        if any(pattern in msg for pattern in ["ElasticSearch", "Elasticsearch", "поиск в закон", "es_law_search"]):
            return "🔍 Поиск в законодательстве..."
            
        if any(pattern in msg for pattern in ["google_search", "интернет", "web_search"]):
            return "🌐 Поиск в интернете..."
            
        if "Найдено" in msg:
            # Пытаемся извлечь количество результатов
            count = "несколько"
            if "релевантных чанков" in msg:
                try:
                    count = msg.split("Найдено ")[1].split(" релевантных")[0]
                except:
                    pass
            return f"✅ Найдено {count} релевантных документов"
            
        if any(pattern in msg for pattern in ["Загружено", "истори", "сообщений", "диалог"]):
            count = "несколько"
            if "предыдущих сообщений" in msg:
                try:
                    count = msg.split("Загружено ")[1].split(" предыдущих")[0]
                except:
                    pass
            return f"📜 Анализ истории диалога ({count} сообщений)"
            
        if any(pattern in msg for pattern in ["API", "DeepSeek", "запрос к API"]):
            return "🧠 Формирование ответа (может занять до 2 минут)..."
            
        if any(pattern in msg for pattern in ["Успешное выполнение", "research", "завершен"]):
            return "✓ Анализ завершен успешно"
        
        # Добавляем специальную обработку всех логов для отладки
        if record.levelno >= logging.INFO:
            return f"ℹ️ {msg}"
            
        return None

# Функция для настройки обработчика логов
def setup_websocket_logging():
    """Настраивает обработчик логов для WebSocket."""
    websocket_handler = WebSocketLogHandler()
    
    # Добавляем обработчик в корневой логгер
    root_logger = logging.getLogger()
    root_logger.addHandler(websocket_handler)
    
    # Добавляем специально к важным логгерам
    critical_loggers = [
        "app",
        "app.handlers",
        "app.services",
        "app.handlers.deepresearch",
        "app.services.deepresearch_service",
        "app.handlers.es_law_search",
        "app.handlers.web_search"
    ]
    
    for logger_name in critical_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.addHandler(websocket_handler)
    
    return websocket_handler