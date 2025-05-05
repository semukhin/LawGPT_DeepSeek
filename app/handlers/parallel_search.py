import logging
from typing import Dict, Any, List
from app.handlers.es_law_search import search_law_chunks
from app.handlers.web_search import WebSearchHandler
import asyncio
import time
import re
import chardet
from app.handlers.web_search import run_multiple_searches
from app.services.query_optimizer import QueryOptimizer
from app.services.tavily_service import TavilyService
from app.utils.logger import get_logger, LogLevel
import json
import os
import hashlib
from app.handlers.es_law_search import search_law_chunks_multi

# Инициализируем logger
logger = get_logger()

def ensure_correct_encoding(text: str) -> str:
    """
    Проверяет и исправляет кодировку текста, обеспечивая UTF-8.
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Текст в корректной кодировке UTF-8
    """
    if not text:
        return ""

    # Если текст уже в виде строки
    if isinstance(text, str):
        try:
            # Пробуем сначала исправить кириллицу в URL-кодировке
            text = re.sub(r'%D0%[89AB][0-9A-F]%D0%[89AB][0-9A-F]', 
                         lambda m: bytes.fromhex(m.group(0).replace('%', '')).decode('utf-8'), 
                         text)
            text = re.sub(r'%D0%[89AB][0-9A-F]', 
                         lambda m: bytes.fromhex(m.group(0).replace('%', '')).decode('utf-8'), 
                         text)
            
            # Исправляем неправильно декодированные символы
            replacements = {
                'Ð°': 'а', 'Ð±': 'б', 'Ð²': 'в', 'Ð³': 'г', 'Ð´': 'д',
                'Ðµ': 'е', 'Ñ': 'ё', 'Ð¶': 'ж', 'Ð·': 'з', 'Ð¸': 'и',
                'Ð¹': 'й', 'Ðº': 'к', 'Ð»': 'л', 'Ð¼': 'м', 'Ð½': 'н',
                'Ð¾': 'о', 'Ð¿': 'п', 'Ñ€': 'р', 'Ñ': 'с', 'Ñ‚': 'т',
                'Ñƒ': 'у', 'Ñ„': 'ф', 'Ñ…': 'х', 'Ñ†': 'ц', 'Ñ‡': 'ч',
                'Ñˆ': 'ш', 'Ñ‰': 'щ', 'ÑŠ': 'ъ', 'Ñ‹': 'ы', 'ÑŒ': 'ь',
                'Ñ': 'э', 'Ñž': 'ю', 'Ñ': 'я'
            }
            
            # Применяем все замены
            for wrong, correct in replacements.items():
                text = text.replace(wrong, correct)
            
            # Пробуем перекодировать через bytes для исправления возможных проблем
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            
            # Удаляем оставшиеся проблемные символы и нормализуем пробелы
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
        except Exception as e:
            logging.error(f"Ошибка при обработке кодировки: {e}")
            return text
            
    # Если текст в bytes
    if isinstance(text, bytes):
        try:
            # Определяем кодировку
            detected = chardet.detect(text)
            if detected and detected['encoding']:
                # Пробуем декодировать с обнаруженной кодировкой
                return text.decode(detected['encoding'], errors='ignore')
        except Exception as e:
            logging.error(f"Ошибка при определении кодировки bytes: {e}")
            pass
            
        # Если не удалось определить кодировку, пробуем UTF-8
        try:
            return text.decode('utf-8', errors='ignore')
        except UnicodeError:
            # В крайнем случае используем Latin-1
            return text.decode('latin1', errors='ignore')
            
    # Если текст другого типа, преобразуем в строку
    return str(text)

async def run_parallel_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Выполняет параллельный поиск по всем источникам и возвращает словарь с результатами."""
    try:
        tavily_service = TavilyService()
        es_results, tavily_results = await asyncio.gather(
            search_law_chunks(query, limit),
            tavily_service.search(query, limit)
        )
        return {
            "es_results": es_results if isinstance(es_results, list) else [],
            "tavily_results": tavily_results if isinstance(tavily_results, list) else []
        }
    except Exception as e:
        logger.log(f"❌ Ошибка при параллельном поиске: {str(e)}", LogLevel.ERROR)
        return {
            "es_results": [],
            "tavily_results": []
        }

async def search_tavily(query: str) -> List[Dict[str, Any]]:
    """
    Выполняет поиск в интернете через Tavily API.
    """
    logging.info(f"🔍 Начало поиска в Tavily по запросу: '{query}'")
    try:
        tavily_service = TavilyService()
        results = await tavily_service.search(query, max_results=5)
        if not isinstance(results, list):
            logging.warning(f"Tavily: неожиданный тип результата: {type(results)}")
            return []
        if not results:
            logging.warning("❌ Tavily вернул пустой ответ или отсутствуют результаты")
            return []
        logging.info(f"✅ Успешно получено {len(results)} результатов от Tavily")
        return results
    except Exception as e:
        logging.error(f"❌ Ошибка при поиске в Tavily: {str(e)}")
        return []