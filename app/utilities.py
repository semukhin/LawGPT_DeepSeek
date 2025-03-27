import json
import os
import time
import logging
import asyncio
import requests
import urllib3
from datetime import timedelta
from fastapi import Depends
from redis import Redis
from functools import wraps, lru_cache
from app.config import VEXA_INTEGRATION_ENABLED
from vexa.vexa_api_client import VexaApiClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Отключение предупреждений SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Сессия HTTP-запросов
session = requests.Session()
session.verify = False  # Отключаем проверку SSL

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Redis подключение
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"), 
    port=int(os.getenv("REDIS_PORT", 6379)), 
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True
)

def get_url_content(url, headers=None, timeout=10):
    """Глобальная функция для запросов без проверки SSL."""
    if headers is None:
        headers = DEFAULT_HEADERS  # Добавляем User-Agent
    else:
        headers.update(DEFAULT_HEADERS)  # Объединяем заголовки

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP ошибка для {url}: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети при запросе {url}: {e}")
    return None

def measure_time(func):
    """Декоратор для измерения времени выполнения функции (async и sync)."""
    
    logging.debug(f"Декоратор применён к функции: {func.__name__}")

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logging.debug(f"Вызов async-функции: {func.__name__}")
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_message = f"Время выполнения {func.__name__} (async): {execution_time:.6f} секунд"
        logging.info(log_message)
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logging.debug(f"Вызов sync-функции: {func.__name__}")
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_message = f"Время выполнения {func.__name__}: {execution_time:.6f} секунд"
        logging.info(log_message)
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # Для async-функций
    return sync_wrapper  # Для sync-функций

def cache_response(prefix, expire=300):
    """Декоратор для кэширования ответов API"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Формируем ключ кэша
            cache_key = f"{prefix}:{hash(json.dumps(str(kwargs)))}"
            
            # Проверяем наличие в кэше
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Выполняем оригинальную функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем в кэш
            redis_client.setex(
                cache_key,
                expire,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator


import re
import numpy as np
from typing import List, Dict, Any

# ======= Классы для распознавания речи и фильтрации контента =======

class LegalSpeechRecognitionModel:
    def __init__(self, language='ru'):
        """
        Специализированная модель распознавания речи для юридической лексики
        
        :param language: Язык распознавания ('ru', 'en')
        """
        self.language = language
        self.model = None
        self.legal_vocabulary = self._load_legal_vocabulary()
    
    def _load_legal_vocabulary(self):
        """
        Загрузка юридической лексики для специализированного распознавания
        """
        vocabularies = {
            'ru': [
                'договор', 'право', 'закон', 'иск', 
                'судебное', 'решение', 'арбитраж', 
                'гражданский', 'уголовный', 'ответственность'
            ],
            'en': [
                'contract', 'law', 'legal', 'lawsuit', 
                'court', 'litigation', 'arbitration', 
                'civil', 'criminal', 'liability'
            ]
        }
        return vocabularies.get(self.language, [])
    
    def extract_features(self, audio_path):
        """
        Упрощенная имплементация извлечения акустических признаков из аудиофайла
        """
        logging.info(f"Извлечение признаков из аудиофайла: {audio_path}")
        # Заглушка для имитации функциональности
        return np.random.random((100, 128))
    
    def predict(self, audio_path):
        """
        Упрощенная имплементация распознавания речи
        
        :param audio_path: Путь к аудиофайлу
        :return: Распознанный текст
        """
        logging.info(f"Распознавание речи из файла: {audio_path}")
        # Возвращаем заглушку распознанного текста
        return self.legal_vocabulary[0] if self.legal_vocabulary else "договор"


class SpeechContentFilter:
    def __init__(self, language='ru'):
        """
        Фильтр содержимого речи с поддержкой цензуры и безопасности
        
        :param language: Язык фильтрации
        """
        self.language = language
        self.blacklists = self._load_blacklists()
        self.sensitive_patterns = self._load_sensitive_patterns()
    
    def _load_blacklists(self) -> List[str]:
        """
        Загрузка списков запрещенных слов
        """
        blacklists = {
            'ru': [
                # Нецензурная лексика
                'бля', 'хуй', 'пизд', 'еба', 'сука', 
                # Оскорбительные термины
                'дура', 'идиот', 'придурок'
            ],
            'en': [
                'fuck', 'shit', 'bitch', 'asshole', 
                'damn', 'cunt', 'dick'
            ]
        }
        return blacklists.get(self.language, [])
    
    def _load_sensitive_patterns(self) -> List[Dict]:
        """
        Загрузка шаблонов для обнаружения чувствительной информации
        """
        return [
            {
                'pattern': r'\b\d{10,}\b',  # Номера телефонов
                'replacement': '[НОМЕР СКРЫТ]'
            },
            {
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                'replacement': '[EMAIL СКРЫТ]'
            },
            {
                'pattern': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP-адреса
                'replacement': '[IP СКРЫТ]'
            }
        ]
    
    def censor_text(self, text: str) -> str:
        """
        Цензурирование текста
        
        :param text: Исходный текст
        :return: Отфильтрованный текст
        """
        # Преобразуем текст в нижний регистр для сравнения
        censored_text = text.lower()
        
        # Замена нецензурной лексики
        for bad_word in self.blacklists:
            # Регулярное выражение для поиска слова с учетом окончаний
            pattern = rf'\b{bad_word}\w*\b'
            censored_text = re.sub(pattern, '[ЦЕНЗУРА]', censored_text)
        
        return censored_text
    
    def anonymize_text(self, text: str) -> str:
        """
        Анонимизация чувствительной информации
        
        :param text: Исходный текст
        :return: Анонимизированный текст
        """
        anonymized_text = text
        
        for sensitive_pattern in self.sensitive_patterns:
            anonymized_text = re.sub(
                sensitive_pattern['pattern'], 
                sensitive_pattern['replacement'], 
                anonymized_text
            )
        
        return anonymized_text
    
    def detect_intent(self, text: str) -> Dict[str, float]:
        """
        Определение намерения пользователя
        
        :param text: Распознанный текст
        :return: Словарь с вероятностями намерений
        """
        # Простая эвристика определения намерения
        intents = {
            'question': 0.0,
            'statement': 0.0,
            'request': 0.0,
            'complaint': 0.0
        }
        
        # Определение вопроса
        if '?' in text:
            intents['question'] = 0.8
        
        # Определение жалобы
        complaint_keywords = ['жалоб', 'недовол', 'пробл', 'наруш']
        if any(keyword in text.lower() for keyword in complaint_keywords):
            intents['complaint'] = 0.7
        
        # Определение запроса
        request_keywords = ['помо', 'нужн', 'хочу', 'треб']
        if any(keyword in text.lower() for keyword in request_keywords):
            intents['request'] = 0.7
        
        # Для остальных устанавливаем значение statement
        if intents['question'] < 0.5 and intents['complaint'] < 0.5 and intents['request'] < 0.5:
            intents['statement'] = 0.6
            
        return intents


# ======= Фабричные функции для ленивой инициализации =======

@lru_cache(maxsize=1)
def get_vexa_client():
    """Ленивая инициализация клиента Vexa"""
    if not VEXA_INTEGRATION_ENABLED:
        return None
    return VexaApiClient()

@lru_cache(maxsize=1)
def get_speech_recognition_model():
    """Ленивая инициализация модели распознавания речи"""
    return LegalSpeechRecognitionModel(language='ru')

@lru_cache(maxsize=1)
def get_speech_content_filter():
    """Ленивая инициализация фильтра содержимого речи"""
    return SpeechContentFilter(language='ru')