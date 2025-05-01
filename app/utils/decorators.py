import time
import logging
from functools import wraps
import asyncio

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
        log_message = f"⚡ Время выполнения {func.__name__} (sync): {execution_time:.6f} секунд"
        logging.info(log_message)
        print(log_message)  # Вывод в терминал
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper 