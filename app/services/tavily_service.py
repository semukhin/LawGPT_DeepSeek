"""
Единый сервис для работы с Tavily API.
Поддерживает как асинхронный, так и синхронный поиск.
"""
import os
import logging
import aiohttp
import json
import requests
from typing import List, Dict, Optional, Literal
from app.config import TAVILY_API_KEY
from app.services.query_optimizer import QueryOptimizer
from app.utils import ensure_correct_encoding
from app.utils.logger import get_logger, LogLevel

logger = get_logger()

class TavilyService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TavilyService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.api_key = TAVILY_API_KEY
            self.api_base = "https://api.tavily.com/v1/search"
            self.query_optimizer = QueryOptimizer()
            self.default_domains = [
                "consultant.ru",
                "garant.ru",
                "sudact.ru",
                "kad.arbitr.ru",
                "ras.arbitr.ru",
                "vsrf.ru",
                "pravo.gov.ru"
            ]
            self.initialized = True
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        optimize: bool = True,
        search_depth: Literal["basic", "advanced"] = "advanced",
        include_domains: Optional[List[str]] = None,
        include_raw_content: bool = True
    ) -> List[Dict]:
        """
        Асинхронный поиск через Tavily API с опциональной оптимизацией запроса.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            optimize: Использовать ли оптимизацию запроса через DeepSeek
            search_depth: Глубина поиска ("basic" или "advanced")
            include_domains: Список разрешенных доменов
            include_raw_content: Включать ли полный текст контента
            
        Returns:
            List[Dict]: Список результатов поиска
        """
        try:
            # Проверяем кодировку запроса
            query = ensure_correct_encoding(query)
            
            # Оптимизируем запрос, если нужно
            if optimize:
                query = await self.query_optimizer.optimize_query(query)
                logger.log(f"🔄 Оптимизированный запрос: {query}", LogLevel.INFO)
            
            # Формируем payload
            payload = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_domains": include_domains or self.default_domains,
                "include_raw_content": include_raw_content,
                "api_key": self.api_key
            }
            
            # Выполняем запрос
            async with aiohttp.ClientSession() as session:
                headers = {"Content-Type": "application/json"}
                
                async with session.post(
                    self.api_base,
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.log(f"❌ Ошибка Tavily API ({response.status}): {error_text}", LogLevel.ERROR)
                        return []
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    # Форматируем результаты
                    formatted_results = []
                    for result in results:
                        if not result.get("url") or not result.get("content"):
                            continue
                        
                        formatted_result = {
                            "title": result.get("title", ""),
                            "href": result.get("url"),
                            "body": result.get("content"),
                            "score": result.get("score", 0),
                            "source": result.get("domain"),
                            "metadata": {
                                "published_date": result.get("published_date"),
                                "word_count": len(result.get("content", "").split()),
                                "domain": result.get("domain"),
                                "optimized_query": query if optimize else None
                            }
                        }
                        formatted_results.append(formatted_result)
                    
                    # Сортируем по релевантности
                    formatted_results.sort(key=lambda x: x.get("score", 0), reverse=True)
                    
                    logger.log(f"✅ Найдено {len(formatted_results)} результатов через Tavily API", LogLevel.INFO)
                    return formatted_results[:max_results]
                    
        except Exception as e:
            logger.log(f"❌ Ошибка при поиске в Tavily: {str(e)}", LogLevel.ERROR)
            return []
    
    def sync_search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: Literal["basic", "advanced"] = "basic",
        include_domains: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Синхронная версия поиска для обратной совместимости.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            search_depth: Глубина поиска
            include_domains: Список разрешенных доменов
            
        Returns:
            List[Dict]: Список результатов поиска
        """
        try:
            # Формируем payload
            payload = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_domains": include_domains or self.default_domains,
                "api_key": self.api_key
            }
            
            # Выполняем запрос
            response = requests.post(
                self.api_base,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.log(f"❌ Ошибка Tavily API ({response.status_code}): {response.text}", LogLevel.ERROR)
                return []
            
            results = response.json().get("results", [])
            
            # Форматируем результаты в старом формате для совместимости
            formatted_results = [
                {"href": obj["url"], "body": obj["content"]}
                for obj in results
                if obj.get("url") and obj.get("content")
            ]
            
            logger.log(f"✅ Найдено {len(formatted_results)} результатов", LogLevel.INFO)
            return formatted_results
            
        except Exception as e:
            logger.log(f"❌ Ошибка при синхронном поиске в Tavily: {str(e)}", LogLevel.ERROR)
            return [] 