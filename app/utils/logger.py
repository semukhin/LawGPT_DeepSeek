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

class EnhancedLogger:
    def __init__(self, base_dir: str, app_name: str = 'lawgpt'):
        self.base_dir = base_dir
        self.app_name = app_name
        self.log_level = LogLevel.INFO
        self.debug_mode = False
        
        # Создаем директории для логов
        self.logs_dir = os.path.join(base_dir, 'logs')
        self.prompts_dir = os.path.join(base_dir, 'prompts')
        self.responses_dir = os.path.join(base_dir, 'responses')
        
        for dir_path in [self.logs_dir, self.prompts_dir, self.responses_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Настраиваем основной логгер
        self.setup_logger()
        
        # Кэш для дедупликации сообщений
        self.message_cache: Set[str] = set()
        self.max_cache_size = 1000
    
    def setup_logger(self):
        """Настраивает основной логгер"""
        logger = logging.getLogger(self.app_name)
        logger.setLevel(logging.DEBUG)
        
        # Файловый обработчик для всех логов
        log_file = os.path.join(self.logs_dir, f'log_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Форматтер с подробной информацией
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Добавляем обработчик к логгеру
        logger.addHandler(file_handler)
        self.logger = logger
    
    def _is_duplicate(self, message: str, window: int = 60) -> bool:
        """Проверяет, является ли сообщение дубликатом"""
        # Очищаем старые сообщения из кэша
        if len(self.message_cache) > self.max_cache_size:
            self.message_cache.clear()
        
        # Создаем хэш сообщения
        message_hash = hash(message)
        
        if message_hash in self.message_cache:
            return True
            
        self.message_cache.add(message_hash)
        return False
    
    @lru_cache(maxsize=100)
    def _get_common_response(self, query: str) -> Optional[str]:
        """Кэширует частые ответы"""
        common_responses = {
            'привет': 'Привет! Как могу помочь?',
            'здравствуйте': 'Здравствуйте! Чем могу помочь?',
            'пока': 'До свидания! Буду рад помочь снова.',
            'спасибо': 'Пожалуйста! Обращайтесь, если понадобится помощь.'
        }
        return common_responses.get(query.lower())
    
    def log(self, message: str, level: str = LogLevel.INFO):
        """Основной метод логирования"""
        if level == LogLevel.DEBUG and not self.debug_mode:
            return
            
        # Проверяем на дубликаты
        if self._is_duplicate(message):
            return
            
        # Логируем сообщение
        if level == LogLevel.ERROR:
            self.logger.error(message)
        elif level == LogLevel.WARNING:
            self.logger.warning(message)
        elif level == LogLevel.DEBUG:
            self.logger.debug(message)
        else:
            self.logger.info(message)
    
    def save_prompt(self, messages: List[Dict], query: str, parameters: Dict):
        """Сохраняет промпт в JSON файл"""
        try:
            # Создаем директорию, если её нет
            os.makedirs(self.prompts_dir, exist_ok=True)
            
            # Используем текущую дату и время для имени файла
            current_time = datetime.now()
            filename = f"prompt_{current_time.strftime('%Y%m%d_%H%M%S')}.json"
            
            data = {
                'messages': messages,
                'query': query,
                'parameters': parameters,
                'timestamp': current_time.isoformat()
            }
            
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.log(f"Промпт сохранен в {filepath}")
            return filepath
        except Exception as e:
            self.log(f"Ошибка при сохранении промпта: {str(e)}", LogLevel.ERROR)
            return None
    
    def save_response(self, response: Dict, query: str):
        """Сохраняет ответ в JSON файл"""
        try:
            # Создаем директорию, если её нет
            os.makedirs(self.responses_dir, exist_ok=True)
            
            # Используем текущую дату и время для имени файла
            current_time = datetime.now()
            filename = f"response_{current_time.strftime('%Y%m%d_%H%M%S')}.json"
            
            data = {
                'response': response,
                'query': query,
                'timestamp': current_time.isoformat()
            }
            
            filepath = os.path.join(self.responses_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.log(f"Ответ сохранен в {filepath}")
            return filepath
        except Exception as e:
            self.log(f"Ошибка при сохранении ответа: {str(e)}", LogLevel.ERROR)
            return None
    
    def set_debug_mode(self, enabled: bool):
        """Включает/выключает режим отладки"""
        self.debug_mode = enabled
        if enabled:
            self.log("Режим отладки включен", LogLevel.DEBUG)
        else:
            self.log("Режим отладки выключен", LogLevel.INFO) 