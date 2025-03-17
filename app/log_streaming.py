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
        
        # Идентификаторы ключевых событий для отображения
        if "Начинаем исследование. Длина запроса:" in msg:
            # Извлекаем количество символов из сообщения
            symbols_count = msg.split("Длина запроса: ")[1].split(" символов")[0]
            return f"📋 Подготовка запроса ({symbols_count} символов)"
        elif "Выполнение поиска в ElasticSearch" in msg:
            return "🔍 Поиск в законодательстве..."
        elif "google_search: Начинаем поиск" in msg:
            return "🌐 Поиск в интернете..."
        elif "Найдено" in msg and "релевантных чанков" in msg:
            count = msg.split("Найдено ")[1].split(" релевантных")[0]
            return f"✅ Найдено {count} релевантных документов"
        elif "Загружено" in msg and "предыдущих сообщений" in msg:
            count = msg.split("Загружено ")[1].split(" предыдущих")[0]
            return f"📜 Анализ истории диалога ({count} сообщений)"
        elif "Отправка запроса к DeepSeek API" in msg:
            return "🧠 Формирование ответа (может занять до 2 минут)..."
        elif "Успешное выполнение app.services.deepresearch_service.research" in msg:
            seconds = msg.split("за ")[1].split(" сек")[0]
            return f"✓ Анализ завершен за {seconds} сек"
        
        # По умолчанию не отображаем лог
        return None
    
    async def _send_to_clients(self, log_entry: str):
        """Отправляет лог всем подключенным клиентам."""
        # Подготавливаем данные для отправки
        message = {
            "type": "log",
            "content": log_entry,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        
        # Отправляем каждому подключенному клиенту
        for client in connected_clients:
            try:
                if client.client_state == WebSocketState.CONNECTED:
                    await client.send_json(message)
            except Exception:
                # Игнорируем ошибки отправки
                pass

# Функция для настройки обработчика логов
def setup_websocket_logging():
    """Настраивает обработчик логов для WebSocket."""
    websocket_handler = WebSocketLogHandler()
    
    # Добавляем обработчик в корневой логгер
    root_logger = logging.getLogger()
    root_logger.addHandler(websocket_handler)
    
    # Также добавляем в основные логгеры приложения
    app_loggers = [
        logging.getLogger("app"),
        logging.getLogger("app.handlers"),
        logging.getLogger("app.services"),
        logging.getLogger("deepresearch"),
    ]
    
    for logger in app_loggers:
        logger.addHandler(websocket_handler)
    
    return websocket_handler