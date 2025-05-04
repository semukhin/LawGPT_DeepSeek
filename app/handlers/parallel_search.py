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
import json
import os
import hashlib
from app.handlers.es_law_search import search_law_chunks_multi

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

async def run_parallel_search(query: str) -> Dict[str, Any]:
    """
    Выполняет параллельный поиск в разных источниках: ElasticSearch и Tavily (по двум уточнённым запросам).
    Включает дедупликацию результатов и улучшенную обработку ошибок.
    Теперь: сначала ждет уточнённые запросы DeepSeek (таймаут 20 сек), только после этого ищет.
    """
    logging.info(f"🚀 Запуск параллельного поиска для запроса: '{query}'")
    search_results = {
        "es_results": [],
        "es_case_refs": [],
        "tavily_queries": [],
        "tavily_results": [],
        "tavily_case_refs": [],
        "metadata": {
            "start_time": time.time(),
            "query": query,
            "success": False,
            "error": None
        }
    }
    try:
        # 1. Получаем два уточнённых запроса через DeepSeek с таймаутом
        optimizer = QueryOptimizer()
        try:
            tavily_queries = await asyncio.wait_for(optimizer.get_two_search_queries(query), timeout=20)
            if not tavily_queries or not any(tavily_queries):
                tavily_queries = [query]
                logging.warning("⏳ DeepSeek не вернул уточнённые запросы, используем исходный запрос пользователя.")
        except asyncio.TimeoutError:
            tavily_queries = [query]
            logging.warning("⏳ Таймаут DeepSeek (20 сек). Используем исходный запрос пользователя.")
        except Exception as e:
            tavily_queries = [query]
            logging.error(f"❌ Ошибка при получении уточнённых запросов: {e}. Используем исходный запрос пользователя.")
        search_results["tavily_queries"] = tavily_queries
        logging.info(f"✅ Используем для поиска запросы: {tavily_queries}")

        # 2. Поиск в Tavily по каждому уточнённому запросу
        async def search_tavily(tq: str) -> List[Dict]:
            try:
                tavily_service = TavilyService()
                results = await tavily_service.search(tq, max_results=7)
                if results:
                    logging.info(f"📝 Получены результаты Tavily для запроса '{tq}': {len(results)} результатов")
                    seen_urls = set()
                    unique_results = []
                    for r in results:
                        url = r.get('href', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            r['query'] = tq
                            r['timestamp'] = time.time()
                            unique_results.append(r)
                    return unique_results
                return []
            except Exception as e:
                logging.error(f"❌ Ошибка при поиске в Tavily для запроса '{tq}': {str(e)}")
                return []
        tavily_tasks = [search_tavily(tq) for tq in tavily_queries]
        tavily_results = await asyncio.gather(*tavily_tasks)
        all_tavily_results = []
        seen_urls = set()
        for results in tavily_results:
            for r in results:
                url = r.get('href', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_tavily_results.append(r)
        search_results["tavily_results"] = all_tavily_results
        search_results["tavily_results_raw"] = tavily_results
        logging.info(f"✅ Всего найдено {len(all_tavily_results)} уникальных результатов в Tavily")

        # 3. Поиск в Elasticsearch по уточнённым запросам
        es_results_by_tavily = []
        if tavily_queries:
            es_results_by_tavily = await asyncio.gather(*[
                asyncio.create_task(search_law_chunks(q)) for q in tavily_queries
            ])
            # Объединяем все результаты для расширенного блока
            all_es_results = search_law_chunks_multi(tavily_queries, size=5)
            all_texts = set(hashlib.md5(r.get("text", "").strip().encode()).hexdigest() 
                          for r in search_results["es_results"])
            for r in all_es_results:
                text = r.get("text", "").strip()
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash not in all_texts:
                    search_results["es_results"].append(r)
                    all_texts.add(text_hash)
        search_results["es_results_by_tavily"] = es_results_by_tavily

        # 4. Извлекаем номера дел и реквизиты из ElasticSearch (по основным результатам)
        es_case_refs = []
        for res in search_results["es_results"]:
            text = res.get("text", "")
            case_numbers = set()
            patterns = [
                r'\b\d{2,}-[А-Яа-яA-Za-z0-9\-]+\b',
                r'№\s*\d+[\-\w]*',
                r'дело\s*№\s*\d+[\-\w]*',
                r'[А-Я]\d{2,}-\d+/\d{4}',
            ]
            for pattern in patterns:
                found = re.findall(pattern, text)
                case_numbers.update(found)
            if case_numbers:
                es_case_refs.append({
                    "case_numbers": list(case_numbers),
                    "title": res.get("title", ""),
                    "metadata": res.get("metadata", {})
                })
        search_results["es_case_refs"] = es_case_refs

        # 5. Обновляем метаданные
        search_results["metadata"].update({
            "success": True,
            "execution_time": time.time() - search_results["metadata"]["start_time"],
            "es_results_count": len(search_results["es_results"]),
            "tavily_results_count": len(all_tavily_results),
            "es_by_tavily_count": sum(len(res) for res in es_results_by_tavily)
        })
        logging.info(f"✅ Параллельный поиск завершен за {search_results['metadata']['execution_time']:.2f} секунд")
        return search_results
    except Exception as e:
        error_msg = f"❌ Ошибка при параллельном поиске: {e}"
        logging.error(error_msg)
        search_results["metadata"]["error"] = str(e)
        search_results["metadata"]["execution_time"] = time.time() - search_results["metadata"]["start_time"]
        return search_results

async def search_tavily(query: str) -> List[Dict[str, Any]]:
    """
    Выполняет поиск в интернете через Tavily API.
    """
    logging.info(f"🔍 Начало поиска в Tavily по запросу: '{query}'")
    try:
        tavily_service = TavilyService()
        results = await tavily_service.search(query, max_results=5)
        
        if not results:
            logging.warning("❌ Tavily вернул пустой ответ или отсутствуют результаты")
            return []
            
        logging.info(f"✅ Успешно получено {len(results)} результатов от Tavily")
        return results
    except Exception as e:
        logging.error(f"❌ Ошибка при поиске в Tavily: {str(e)}")
        return []