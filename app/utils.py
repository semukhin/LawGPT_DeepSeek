import requests
import urllib3
import time
import logging
import asyncio
from functools import wraps


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False  # Отключаем проверку SSL

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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
        print(f"[ERROR]: HTTP ошибка для {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR]: Ошибка сети при запросе {url}: {e}")
    return None




logging.basicConfig(level=logging.DEBUG)

def measure_time(func):
    """Декоратор для измерения времени выполнения функции (async и sync)."""
    
    print(f"🔍 Декоратор применён к функции: {func.__name__}")  # Проверяем, применяется ли декоратор

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        print(f"🚀 Вызов async-функции: {func.__name__}")  # Проверка вызова
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_message = f"⚡ Время выполнения {func.__name__} (async): {execution_time:.6f} секунд"
        logging.info(log_message)
        print(log_message)  # Вывод в терминал
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        print(f"🚀 Вызов sync-функции: {func.__name__}")  # Проверка вызова
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        log_message = f"⚡ Время выполнения {func.__name__}: {execution_time:.6f} секунд"
        logging.info(log_message)
        print(log_message)  # Вывод в терминал
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # Для async-функций
    return sync_wrapper  # Для sync-функций
