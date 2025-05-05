"""
Единый сервис для работы с Tavily API.
Поддерживает как асинхронный, так и синхронный поиск.
"""
import os
import logging
from typing import List, Dict, Optional
from tavily import AsyncTavilyClient
import app.utils.logger

class TavilyService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TavilyService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.api_key = os.getenv("TAVILY_API_KEY", "tvly-YOUR_API_KEY")
            if not self.api_key:
                logging.error("❌ TAVILY_API_KEY не найден в переменных окружения")
            self.client = AsyncTavilyClient(self.api_key)
            self.initialized = True

    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        logger = app.utils.logger.get_logger()
        try:
            logger.log(f"[TAVILY] Отправка запроса: '{query}' (max_results={max_results})", app.utils.logger.LogLevel.INFO)
            response = await self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
                include_images=False,
                include_image_descriptions=False,
            )
            if isinstance(response, dict) and "results" in response:
                logger.log(f"[TAVILY] Получено {len(response['results'])} результатов", app.utils.logger.LogLevel.INFO)
                if response['results']:
                    logger.log(f"[TAVILY] Пример первого результата: {str(response['results'][0])[:500]}...", app.utils.logger.LogLevel.DEBUG)
                return response["results"]
            else:
                logger.log(f"[TAVILY] неожиданный формат ответа: {str(response)[:500]}", app.utils.logger.LogLevel.WARNING)
                return []
        except Exception as e:
            logger.log(f"[TAVILY] ошибка при поиске: {e}", app.utils.logger.LogLevel.ERROR)
            return [] 