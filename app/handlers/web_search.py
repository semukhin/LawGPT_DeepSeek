"""
Модуль для поиска информации в интернете.
Выполняет поиск через Google Custom Search API и извлекает содержимое найденных страниц.
"""
import requests
import urllib3
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse
import os
import sys
from dotenv import load_dotenv

# Добавляем путь к third_party для корректного импорта shandu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
   sys.path.insert(0, THIRD_PARTY_DIR)

from app.utils import get_url_content
from third_party.shandu.scraper import WebScraper, ScrapedContent

# Отключаем предупреждения SSL для совместимости
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ключи Google Custom Search
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")

# Константы для ограничения количества ссылок
MAX_SEARCH_RESULTS = 10  # Максимальное количество ссылок для поиска
MAX_SCRAPE_RESULTS = 5   # Максимальное количество ссылок для скрейпинга (ТОП-5)

# В начале файла
logging.info(f"Google API Key настроен: {'Да' if len(GOOGLE_API_KEY) > 0 else 'Нет'}")
logging.info(f"Google CX настроен: {'Да' if len(GOOGLE_CX) > 0 else 'Нет'}")

# Создаем единственный экземпляр WebScraper
_scraper = None


def get_scraper() -> WebScraper:
   """
   Получает или создает экземпляр WebScraper из Shandu.
   
   Returns:
       WebScraper: Экземпляр скрапера Shandu
   """
   global _scraper
   if _scraper is None:
       # Создаем экземпляр WebScraper и присваиваем его глобальной переменной
       _scraper = WebScraper(
           user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
           respect_robots=False)
       logger.info("Инициализирован WebScraper из Shandu")
   return _scraper


def google_search(query: str, logs: list, max_results: int = MAX_SEARCH_RESULTS) -> list:
   """
   Выполняет поиск по запросу через Google Custom Search API и возвращает список найденных веб-ссылок.
   
   Args:
       query (str): поисковый запрос.
       logs (list): список для логирования хода выполнения.
       max_results (int): максимальное количество результатов.
       
   Returns:
       list: Список URL, найденных по запросу.
   """
   # Убираем любые добавления к запросу типа "закон судебная практика" или "последние изменения"
   clean_query = query.replace(" закон судебная практика", "").replace(" последние изменения", "")
   
   url = "https://www.googleapis.com/customsearch/v1"
   params = {
       "key": GOOGLE_API_KEY,
       "cx": GOOGLE_CX,
       "q": clean_query,  # Используем очищенный запрос
       "num": min(max_results, 10),  # Google API ограничивает результаты
       "safe": "active"
   }
   
   logs.append(f"🔍 Выполнение поиска Google Custom Search API для запроса: '{clean_query}'")
   logging.info(f"🔍 google_search: Начинаем поиск для '{clean_query}'")
   start_time = time.time()

   # Проверка наличия ключей
   if not GOOGLE_API_KEY or not GOOGLE_CX:
       logging.warning("❌ google_search: API ключи Google не настроены!")
       logs.append("❌ API ключи Google не настроены!")
       return []

   
   try:
       logging.info(f"🔍 google_search: Отправка запроса к API")
       response = requests.get(url, params=params, timeout=15)
       status_code = response.status_code
       logging.info(f"🔍 google_search: Статус ответа: {status_code}")
       
       response.raise_for_status()
       data = response.json()
       
       # Проверка наличия результатов
       if "items" not in data:
           logging.warning(f"⚠️ google_search: API не вернул результаты")
           logs.append(f"⚠️ Google не вернул результаты для запроса '{clean_query}'")
           return []
       
       items = data.get("items", [])
       logging.info(f"🔍 google_search: Найдено {len(items)} элементов")
       links = [item.get("link") for item in items if item.get("link")]
       
       # Фильтруем недопустимые URL
       valid_links = [link for link in links if is_valid_url(link)]
       
       elapsed_time = time.time() - start_time
       logging.info(f"✅ google_search: Найдено {len(valid_links)} валидных ссылок за {elapsed_time:.2f} сек")
       logs.append(f"✅ Найдено {len(valid_links)} ссылок по запросу '{clean_query}' за {elapsed_time:.2f} секунд")
       
       # Выводим первые результаты для отладки
       for i, link in enumerate(valid_links[:3]):
           logging.info(f"URL {i+1}: {link}")
           logs.append(f"URL {i+1}: {link}")
       
       return valid_links
       
   except requests.exceptions.RequestException as e:
       logs.append(f"❌ Ошибка при поиске в Google: {str(e)}")
       logger.error(f"Ошибка Google API: {str(e)}")
       return []

def is_valid_url(url: str) -> bool:
   """
   Проверяет, является ли URL допустимым.
   
   Args:
       url (str): URL для проверки
       
   Returns:
       bool: True, если URL допустим, иначе False
   """
   try:
       result = urlparse(url)
       return all([result.scheme, result.netloc])
   except:
       return False

def prioritize_links(links: List[str], query: str) -> List[str]:
    """
    Приоритизирует ссылки для скрейпинга на основе релевантности запросу.
    
    Args:
        links: Список URL
        query: Поисковый запрос
        
    Returns:
        Отсортированный список URL с приоритетом
    """
    # Высококачественные домены для правовых запросов
    high_quality_domains = [
        "consultant.ru", "garant.ru", "sudact.ru", "pravo.gov.ru", 
        "zakon.ru", "ksrf.ru", "vsrf.ru", "arbitr.ru", "rg.ru", "supcourt.ru",
        "advgazeta.ru", "kodeks.ru", "pravoved.ru", "pravorub.ru", "rostrud.gov.ru"
    ]
    
    # Информационные порталы
    info_portals = [
        "tass.ru", "rbc.ru", "kommersant.ru", "vedomosti.ru", "interfax.ru", 
        "pravo.ru", "rapsinews.ru"
    ]
    
    # Оценка каждой ссылки
    scored_links = []
    
    for url in links:
        score = 0
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # Исключаем социальные сети и нерелевантные ресурсы
        bad_domains = ["pinterest", "instagram", "facebook", "twitter", "youtube", "tiktok", 
                       "reddit", "quora", "linkedin", "amazon", "ebay", "avito", "aliexpress"]
        if any(bad_domain in domain for bad_domain in bad_domains):
            continue
        
        # Повышаем приоритет для высококачественных доменов
        if any(good_domain in domain for good_domain in high_quality_domains):
            score += 15
        
        # Повышаем приоритет для информационных порталов
        if any(portal in domain for portal in info_portals):
            score += 8
        
        # Повышаем приоритет для правовых доменов
        if any(term in domain for term in ["garant", "consultant", "pravorub", "pravo", "sudact", "zakon", "advgazeta", "kodeks", "pravoved"]):
            score += 10
            
        # Проверяем пути URL на релевантность юридической тематике
        legal_path_terms = ["sud", "zakon", "kodeks", "pravo", "jurist", "advokat", "urist", "legal", "law"]
        if any(term in path for term in legal_path_terms):
            score += 5
        
        # Оцениваем по наличию ключевых слов запроса в URL
        query_terms = query.lower().split()
        for term in query_terms:
            if len(term) > 3 and term in url.lower():
                score += 3
        
        # Предпочитаем документы PDF, DOCX и т.д. для правовых запросов (особенно на официальных сайтах)
        if url.lower().endswith(('.pdf', '.doc', '.docx')):
            score += 5
            # Дополнительный бонус, если PDF на официальном сайте
            if any(good_domain in domain for good_domain in high_quality_domains):
                score += 5
        
        # Русскоязычные сайты получают приоритет для русскоязычных запросов
        if ".ru" in domain or ".рф" in domain:
            score += 7
        
        # Понижаем рейтинг для сайтов, которые могут содержать устаревшую информацию
        if any(old_term in domain for old_term in ["narod.ru", "ucoz.ru", "boom.ru", "by.ru"]):
            score -= 5
            
        # Избегаем страниц с параметрами запросов в URL, которые могут быть динамическими
        if "?" in url and ("search" in url.lower() or "query" in url.lower()):
            score -= 3
        
        scored_links.append((url, score))
    
    # Сортируем ссылки по убыванию оценки
    scored_links.sort(key=lambda x: x[1], reverse=True)
    
    # Возвращаем только URL, отсортированные по приоритету
    return [url for url, _ in scored_links]


async def search_and_scrape(query: str, logs: list, max_results: int = MAX_SCRAPE_RESULTS, force_refresh: bool = False) -> list:
    """
    Выполняет поиск в Google, получает список веб-ссылок и передаёт их в модуль скрейпера 
    для извлечения содержимого страниц. Ограничивает количество результатов до MAX_SCRAPE_RESULTS (ТОП-5).
    
    Args:
        query (str): поисковый запрос.
        logs (list): список для логирования.
        max_results (int): максимальное количество результатов (по умолчанию 5).
        force_refresh (bool): флаг принудительного обновления кэша.
        
    Returns:
        list: Список объектов ScrapedContent, полученных после скрейпинга найденных страниц.
    """
    start_time = time.time()
    logs.append(f"🔍 Начало поиска и извлечения данных по запросу: '{query}'")
    
    # Убеждаемся, что max_results не превышает MAX_SCRAPE_RESULTS (5)
    max_results = min(max_results, MAX_SCRAPE_RESULTS)
    
    # Выполняем поиск и получаем ссылки (получаем больше, чтобы потом приоритизировать)
    links = google_search(query, logs, max_results=max_results * 2) 
    
    if not links:
        logs.append("⚠️ Не найдено ссылок для скрейпинга")
        return []
    
    try:
        # Приоритизируем ссылки
        prioritized_links = prioritize_links(links, query)
        
        # Берем только необходимое количество ссылок (ТОП-5 или меньше)
        links_to_scrape = prioritized_links[:max_results]
        
        # Логируем информацию о количестве ссылок для скрейпинга
        logs.append(f"📥 Отправка на скрейпинг ТОП-{len(links_to_scrape)} ссылок из {len(links)} найденных")
        logging.info(f"📥 Отправка на скрейпинг ТОП-{len(links_to_scrape)} ссылок из {len(links)} найденных")

        if not links_to_scrape:
            logging.warning(f"⚠️ search_and_scrape: Ссылки не найдены для '{query}'")
            return []
        
        # Создаем задачи для параллельного скрапинга
        scrape_tasks = []
        for url in links_to_scrape:
            # Проверяем, является ли URL бинарным файлом
            is_binary = url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'))
            
            if is_binary:
                # Создаем placeholder для бинарных файлов
                file_type = url.split('.')[-1].upper()
                result = ScrapedContent(
                    url=url,
                    title=f"{file_type} Document: {url.split('/')[-1]}",
                    text=f"Binary {file_type} file available at: {url}",
                    html="",
                    metadata={"binary_type": file_type.lower(), "scraped": False},
                    content_type=f"application/{file_type.lower()}"
                )
                scrape_tasks.append(asyncio.create_task(asyncio.sleep(0, result)))
                logs.append(f"✅ Created placeholder for binary {file_type}: {url}")
            else:
                # Используем scraper для HTML-контента
                scraper = get_scraper()
                task = scraper.scrape_url(url, dynamic=False)
                scrape_tasks.append(task)
        
        # Дожидаемся выполнения всех задач с таймаутом для каждой
        # Это гарантирует, что мы не будем ждать слишком долго
        completed_tasks = []
        timeout = 15  # 15 секунд максимум на одну страницу
        
        for task in scrape_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=timeout)
                completed_tasks.append(result)
            except asyncio.TimeoutError:
                logs.append(f"⚠️ Скрапинг занял слишком много времени и был прерван")
                logging.warning("Скрапинг URL превысил таймаут и был прерван")
            except Exception as e:
                logs.append(f"❌ Ошибка при скрапинге: {str(e)}")
                logging.error(f"Ошибка при скрапинге: {str(e)}")
        
        # Фильтруем успешные результаты и применяем ограничение на длину текста
        successful_results = []
        max_content_length = 5000  # максимальная длина текста из одного источника
        
        for result in completed_tasks:
            if result.is_successful():
                # Ограничиваем размер текста для экономии места в промте
                if len(result.text) > max_content_length:
                    truncated_text = result.text[:max_content_length] + "... [текст обрезан из-за ограничений размера]"
                    result = ScrapedContent(
                        url=result.url,
                        title=result.title,
                        text=truncated_text,
                        html=result.html,
                        metadata=result.metadata,
                        content_type=result.content_type,
                        error=None
                    )
                
                successful_results.append(result)
                logs.append(f"✅ Successfully scraped: {result.url}")
        
        elapsed_time = time.time() - start_time
        logging.info(f"✅ search_and_scrape: Получено {len(successful_results)} успешных результатов из {len(links_to_scrape)} ссылок за {elapsed_time:.2f} сек")
        logs.append(f"✅ Получено {len(successful_results)} успешных результатов из {len(links_to_scrape)} ссылок за {elapsed_time:.2f} секунд")
        
        return successful_results
        
    except Exception as e:
        logs.append(f"❌ Ошибка при скрейпинге: {str(e)}")
        logger.error(f"Ошибка при скрейпинге для запроса '{query}': {str(e)}")
        return []


async def run_multiple_searches(query: str, logs: list, force_refresh: bool = False) -> Dict[str, List]:
    """
    Выполняет только один поиск вместо нескольких, ограничивая количество результатов до MAX_SCRAPE_RESULTS (ТОП-5).
    """
    logs.append(f"🔄 Запуск поиска для запроса: '{query}'")
    
    # Выполняем только один поиск с ограничением до MAX_SCRAPE_RESULTS (5) ссылок
    try:
        general_results = await search_and_scrape(query, logs, max_results=MAX_SCRAPE_RESULTS, force_refresh=force_refresh)
        
        # Объединяем результаты в словарь 
        results = {
            "general": general_results,
            # Для обратной совместимости оставляем пустые списки
            "legal": [],
            "recent": []
        }
        
        total_results = len(general_results)
        logs.append(f"📊 Получено всего {total_results} результатов из поиска (максимум {MAX_SCRAPE_RESULTS})")
        
        return results
    
    except Exception as e:
        logs.append(f"❌ Ошибка при выполнении поиска: {str(e)}")
        logging.error(f"Ошибка при выполнении поиска: {str(e)}")
        return {"legal": [], "recent": [], "general": []}