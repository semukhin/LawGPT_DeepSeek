"""
Модуль для улучшенного логирования с поддержкой дедупликации и уровней логирования.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from functools import lru_cache

class LogLevel:
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

# Глобальный экземпляр логгера
_global_logger = None

class EnhancedLogger:
    """Расширенный логгер с поддержкой сохранения в файл и дедупликацией."""
    
    def __init__(self, app_name: str = "app"):
        self.app_name = app_name
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Создаем директории для логов, промптов и ответов
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.prompts_dir = os.path.join(self.base_dir, 'prompts')
        self.responses_dir = os.path.join(self.base_dir, 'responses')
        
        for dir_path in [self.logs_dir, self.prompts_dir, self.responses_dir]:
            os.makedirs(dir_path, exist_ok=True)
            
        # Настраиваем логгер
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.INFO)
        
        # Хендлер для файла
        log_file = os.path.join(self.logs_dir, f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Добавляем хендлер
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
        
        self.seen_messages: Set[str] = set()
        self._setup_logging_methods()

    def _setup_logging_methods(self):
        """Настраивает методы логирования для совместимости со стандартным логгером."""
        self.debug = lambda msg, *args, **kwargs: self.log(msg, LogLevel.DEBUG, *args, **kwargs)
        self.info = lambda msg, *args, **kwargs: self.log(msg, LogLevel.INFO, *args, **kwargs)
        self.warning = lambda msg, *args, **kwargs: self.log(msg, LogLevel.WARNING, *args, **kwargs)
        self.error = lambda msg, *args, **kwargs: self.log(msg, LogLevel.ERROR, *args, **kwargs)
        self.critical = self.error

    def log(self, message: str, level: str = LogLevel.INFO, deduplicate: bool = True) -> None:
        """
        Логирует сообщение с указанным уровнем.
        
        Args:
            message: Сообщение для логирования
            level: Уровень логирования
            deduplicate: Убирать ли дубликаты
        """
        if deduplicate:
            message_hash = f"{level}:{message}"
            if message_hash in self.seen_messages:
                return
            self.seen_messages.add(message_hash)
        
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, message)

    def save_prompt(self, messages: List[Dict], query: str, parameters: Dict):
        """Сохраняет промпт в JSON файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.prompts_dir, f"prompt_{timestamp}.json")
        
        data = {
            "timestamp": timestamp,
            "query": query,
            "messages": messages,
            "parameters": parameters
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.log(f"Сохранен промпт: {filename}")

    def save_response(self, response: Dict, query: str):
        """Сохраняет ответ в JSON файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.responses_dir, f"response_{timestamp}.json")
        
        data = {
            "timestamp": timestamp,
            "query": query,
            "response": response
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.log(f"Сохранен ответ: {filename}")

def get_logger(base_dir: Optional[str] = None, app_name: str = 'lawgpt') -> EnhancedLogger:
    """
    Получает глобальный экземпляр логгера.
    Создает новый, если еще не создан.
    
    Args:
        base_dir: Базовая директория для логов
        app_name: Имя приложения для логгера
        
    Returns:
        EnhancedLogger: Экземпляр логгера
    """
    global _global_logger
    if _global_logger is None:
        if base_dir is None:
            # Получаем путь к корневой директории приложения
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _global_logger = EnhancedLogger(app_name)
    return _global_logger

# Создаем глобальный логгер при импорте модуля
logger = get_logger() 