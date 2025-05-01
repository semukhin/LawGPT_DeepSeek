"""
Сервис для поиска информации через Google Custom Search API.
"""
import os
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from app.search_result import SearchResult
from app.config import GOOGLE_API_KEY, GOOGLE_CX

class SearchService:
    """Сервис для поиска информации."""
    
    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None):
        self.api_key = api_key or GOOGLE_API_KEY
        self.cx = cx or GOOGLE_CX
        
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Выполняет поиск через Google Custom Search API.
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            List[SearchResult]: Список результатов поиска
        """
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": max_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logging.error(f"Ошибка Google API: {response.status}")
                        return []
                        
                    data = await response.json()
                    if "items" not in data:
                        return []
                        
                    results = []
                    for item in data["items"]:
                        result = SearchResult(
                            url=item.get("link", ""),
                            title=item.get("title", ""),
                            snippet=item.get("snippet", ""),
                            source="google",
                            date=item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time"),
                            metadata=item.get("pagemap", {})
                        )
                        results.append(result)
                        
                    return results
                    
        except Exception as e:
            logging.error(f"Ошибка при поиске: {e}")
            return [] 