"""
Модуль для поиска информации в интернете.
Выполняет поиск через Tavily API с оптимизацией через DeepSeek.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from bs4 import BeautifulSoup
import aiohttp
from app.utils import ensure_correct_encoding, sanitize_search_results
from app.search_result import SearchResult
from app.services.tavily_service import TavilyService
from app.services.query_optimizer import QueryOptimizer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Константы для ограничения количества ссылок
MAX_SEARCH_RESULTS = 10  # Максимальное количество ссылок для поиска
MAX_SCRAPE_RESULTS = 10   # Максимальное количество ссылок для скрейпинга

async def run_multiple_searches(query: str, logs: List[str]) -> Dict[str, List[Dict]]:
    """
    Выполняет поиск с использованием Tavily API.
    
    Args:
        query: Поисковый запрос
        logs: Список для логирования
        
    Returns:
        Dict[str, List[Dict]]: Результаты поиска
    """
    try:
        tavily_service = TavilyService()
        
        # Выполняем поиск через Tavily
        results = await tavily_service.search(query, max_results=MAX_SEARCH_RESULTS)
        
        if results:
            logs.append(f"✅ Найдено {len(results)} результатов через Tavily")
            return {"general": results}
        else:
            logs.append("❌ Результаты поиска не найдены")
            return {}
            
    except Exception as e:
        logging.error(f"Ошибка при выполнении поиска: {str(e)}")
        logs.append(f"❌ Ошибка при поиске: {str(e)}")
        return {}

class WebSearchHandler:
    """
    Обработчик для выполнения поисковых запросов с оптимизацией.
    """
    def __init__(self):
        self.tavily_service = TavilyService()
        self.query_optimizer = QueryOptimizer()
        
    async def search_and_scrape(self, query: str, logs: list, max_results: int = MAX_SCRAPE_RESULTS) -> list:
        """
        Выполняет поиск и скрейпинг информации по запросу с оптимизацией.
        
        Args:
            query: Поисковый запрос
            logs: Список для логирования
            max_results: Максимальное количество результатов
            
        Returns:
            list: Список найденных и обработанных результатов
        """
        try:
            # Проверяем кодировку запроса
            query = ensure_correct_encoding(query)
            
            # Выполняем улучшенный поиск
            results = await self.tavily_service.search(query, max_results=max_results)
            
            if not results:
                logs.append("❌ Результаты поиска не найдены")
                return []
                
            # Обрабатываем результаты
            processed_results = []
            for result in results:
                try:
                    processed_results.append({
                        'url': result.get('href', ''),
                        'text': result.get('body', ''),
                        'title': result.get('title', '') or result.get('body', '')[:100]
                    })
                except Exception as e:
                    logging.error(f"Ошибка при обработке результата: {str(e)}")
                    continue
                    
            logs.append(f"✅ Найдено {len(processed_results)} результатов")
            return processed_results
            
        except Exception as e:
            logging.error(f"Ошибка в search_and_scrape: {str(e)}")
            logs.append(f"❌ Ошибка при поиске: {str(e)}")
            return []
            
    async def search_internet(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Выполняет поиск в интернете с оптимизацией запроса.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            List[SearchResult]: Список результатов поиска
        """
        try:
            # Выполняем улучшенный поиск
            results = await self.tavily_service.search(query, max_results=max_results)
            
            # Преобразуем результаты в формат SearchResult
            search_results = []
            for result in results:
                try:
                    search_results.append(
                        SearchResult(
                            url=result.get('href', ''),
                            title=result.get('title', '') or result.get('body', '')[:80],
                            snippet=result.get('body', ''),
                            source="tavily"
                        )
                    )
                except Exception as e:
                    logging.error(f"Ошибка при создании SearchResult: {str(e)}")
                    continue
                    
            return search_results
            
        except Exception as e:
            logging.error(f"Ошибка в search_internet: {str(e)}")
            return []