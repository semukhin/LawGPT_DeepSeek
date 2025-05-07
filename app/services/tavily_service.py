"""
Единый сервис для работы с Tavily API.
Поддерживает как асинхронный, так и синхронный поиск и извлечение контента.
"""
import os
import logging
from typing import List, Dict, Optional, Any
from tavily import AsyncTavilyClient
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
from app.utils.logger import get_logger, LogLevel
from app.models.scraping import ScrapedContent

class TavilyCache:
    """Кэш для результатов Tavily API с поддержкой TTL."""
    
    def __init__(self, cache_dir: str = "cache/tavily", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.logger = get_logger()
        
    def _get_cache_path(self, key: str) -> Path:
        """Возвращает путь к кэш-файлу."""
        # Используем SHA-256 от ключа как имя файла
        from hashlib import sha256
        filename = sha256(key.encode()).hexdigest() + '.json'
        return self.cache_dir / filename
        
    def get(self, key: str) -> Optional[Dict]:
        """Получает данные из кэша."""
        try:
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                return None
                
            with cache_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Проверяем TTL
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                cache_path.unlink()
                return None
                
            self.logger.log(f"Cache hit for key: {key[:50]}...", LogLevel.DEBUG)
            return data['content']
        except Exception as e:
            self.logger.log(f"Cache error: {str(e)}", LogLevel.ERROR)
            return None
            
    def set(self, key: str, value: Dict) -> None:
        """Сохраняет данные в кэш."""
        try:
            cache_path = self._get_cache_path(key)
            data = {
                'timestamp': datetime.now().isoformat(),
                'content': value
            }
            with cache_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.log(f"Cached data for key: {key[:50]}...", LogLevel.DEBUG)
        except Exception as e:
            self.logger.log(f"Cache write error: {str(e)}", LogLevel.ERROR)

class TavilyService:
    """Сервис для работы с Tavily API."""
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.api_key = os.getenv("TAVILY_API_KEY", "tvly-YOUR_API_KEY")
            if not self.api_key:
                logging.error("❌ TAVILY_API_KEY не найден в переменных окружения")
            self.client = AsyncTavilyClient(self.api_key)
            self.logger = get_logger()
            self.cache = TavilyCache()
            self.max_retries = 3
            self.retry_delay = 1  # секунды
            self.initialized = True
            
    async def _execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Выполняет функцию с ретраями."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                    self.logger.log(
                        f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...",
                        LogLevel.WARNING
                    )
                    await asyncio.sleep(delay)
                    
        self.logger.log(f"All retry attempts failed: {str(last_error)}", LogLevel.ERROR)
        raise last_error
            
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Выполняет поиск через Tavily API с кэшированием."""
        cache_key = f"search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        try:
            self.logger.log(f"[TAVILY] Отправка запроса: '{query}' (max_results={max_results})", LogLevel.INFO)
            response = await self._execute_with_retry(
                self.client.search,
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
                include_images=False,
                include_image_descriptions=False,
            )
            
            if isinstance(response, dict) and "results" in response:
                results = response["results"]
                self.cache.set(cache_key, results)
                self.logger.log(f"[TAVILY] Получено {len(results)} результатов", LogLevel.INFO)
                if results:
                    self.logger.log(f"[TAVILY] Пример первого результата: {str(results[0])[:500]}...", LogLevel.DEBUG)
                return results
            else:
                self.logger.log(f"[TAVILY] неожиданный формат ответа: {str(response)[:500]}", LogLevel.WARNING)
                return []
        except Exception as e:
            self.logger.log(f"[TAVILY] ошибка при поиске: {e}", LogLevel.ERROR)
            return []
            
    async def extract_content(self, url: str, session: Optional[aiohttp.ClientSession] = None) -> ScrapedContent:
        """Извлекает контент из URL с помощью Tavily API."""
        cache_key = f"extract:{url}"
        cached = self.cache.get(cache_key)
        if cached:
            return ScrapedContent.from_dict(cached)
            
        try:
            response = await self._execute_with_retry(self.client.extract, urls=[url])
            if not isinstance(response, dict):
                self.logger.log(f"[TAVILY] Неожиданный формат ответа при извлечении: {response}", LogLevel.WARNING)
                return ScrapedContent(url=url, title="", text="", error="Неожиданный формат ответа")
                
            if response.get('failed_results'):
                return ScrapedContent(url=url, title="", text="", error="Ошибка извлечения контента")
                
            results = response.get('results', [])
            if not isinstance(results, list) or not results:
                self.logger.log(f"[TAVILY] Нет успешных результатов: {response}", LogLevel.WARNING)
                return ScrapedContent(url=url, title="", text="", error="Нет результатов")
                
            # Если нужен HTML, получаем его через aiohttp
            html_content = ""
            if session:
                try:
                    async with session.get(url, timeout=4) as response_bs:
                        html_content = await response_bs.text()
                        soup = BeautifulSoup(html_content, "lxml", from_encoding=response_bs.charset)
                        title = soup.title.string if soup.title else ""
                except Exception as e:
                    self.logger.log(f"[TAVILY] Ошибка при получении HTML: {e}", LogLevel.WARNING)
                    title = ""
            else:
                title = ""
                
            content = results[0].get('raw_content', '')
            result = ScrapedContent(
                url=url,
                title=title or url,
                text=content,
                html=html_content if html_content else None,
                metadata={"source": "tavily"}
            )
            
            # Кэшируем результат
            self.cache.set(cache_key, result.to_dict())
            return result
            
        except Exception as e:
            self.logger.log(f"[TAVILY] Ошибка при извлечении контента: {e}", LogLevel.ERROR)
            return ScrapedContent(url=url, title="", text="", error=str(e))
            
    async def extract_multiple(self, urls: List[str]) -> List[ScrapedContent]:
        """Извлекает контент из нескольких URL параллельно."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.extract_content(url, session) for url in urls]
            return await asyncio.gather(*tasks) 