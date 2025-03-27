# Новый файл app/cache.py
import json
from datetime import timedelta
from fastapi import Depends
from redis import Redis
from functools import wraps

# Подключение к Redis (можно заменить на другой механизм кэширования)
redis_client = Redis(host=os.getenv("REDIS_HOST", "localhost"), 
                   port=int(os.getenv("REDIS_PORT", 6379)), 
                   password=os.getenv("REDIS_PASSWORD", None),
                   decode_responses=True)

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