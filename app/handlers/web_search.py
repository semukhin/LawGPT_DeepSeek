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


def google_search(query: str, logs: list, max_results: int = 10) -> list:
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
       "num": min(max_results, 5),  # Google API ограничивает до 5 результатов
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
       "zakon.ru", "ksrf.ru", "vsrf.ru", "arbitr.ru"
   ]
   
   # Оценка каждой ссылки
   scored_links = []
   
   for url in links:
       score = 0
       parsed_url = urlparse(url)
       domain = parsed_url.netloc.lower()
       
       # Повышаем приоритет для высококачественных доменов
       if any(good_domain in domain for good_domain in high_quality_domains):
           score += 10
       
       # Повышаем приоритет для правовых доменов
       if any(term in domain for term in ["garant", "consultant", "pravorub", "pravo", "sudact", "zakon"]):
           score += 5
       
       # Оцениваем по наличию ключевых слов запроса в URL
       query_terms = query.lower().split()
       for term in query_terms:
           if len(term) > 3 and term in url.lower():
               score += 2
       
       # Предпочитаем документы PDF, DOCX и т.д. для правовых запросов
       if url.lower().endswith(('.pdf', '.doc', '.docx')):
           score += 3
       
       # Русскоязычные сайты получают приоритет для русскоязычных запросов
       if ".ru" in domain or "рф" in domain:
           score += 5
       
       scored_links.append((url, score))
   
   # Сортируем ссылки по убыванию оценки
   scored_links.sort(key=lambda x: x[1], reverse=True)
   
   # Возвращаем только URL, отсортированные по приоритету
   return [url for url, _ in scored_links]


async def search_and_scrape(query: str, logs: list, max_results: int = 3, force_refresh: bool = False) -> list:
    """
    Выполняет поиск в Google, получает список веб-ссылок и передаёт их в модуль скрейпера 
    для извлечения содержимого страниц. Ограничивает количество результатов.
    
    Args:
        query (str): поисковый запрос.
        logs (list): список для логирования.
        max_results (int): максимальное количество результатов (по умолчанию 3).
        force_refresh (bool): флаг принудительного обновления кэша.
        
    Returns:
        list: Список объектов ScrapedContent, полученных после скрейпинга найденных страниц.
    """
    start_time = time.time()
    logs.append(f"🔍 Начало поиска и извлечения данных по запросу: '{query}'")
    
    # Выполняем поиск и получаем ссылки (не более чем нам нужно)
    links = google_search(query, logs, max_results=max_results) 
    
    if not links:
        logs.append("⚠️ Не найдено ссылок для скрейпинга")
        return []
    
    try:
        # Приоритизируем ссылки
        prioritized_links = prioritize_links(links, query)
        
        # Берем только необходимое количество ссылок
        links_to_scrape = prioritized_links[:max_results]
        logs.append(f"📥 Извлечение содержимого из {len(links_to_scrape)} ссылок...")

        if not links:
            logging.warning(f"⚠️ search_and_scrape: Ссылки не найдены для '{query}'")
            return []
        
        successful_results = []
        for url in links_to_scrape:
            try:
                # Check if the URL points to a binary file
                is_binary = url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'))
                
                if is_binary:
                    # Handle binary files differently
                    logs.append(f"📄 Detected binary file: {url}")
                    
                    # For PDFs, create a placeholder ScrapedContent with metadata
                    if url.lower().endswith('.pdf'):
                        # Create placeholder with file info but don't try to decode content
                        result = ScrapedContent(
                            url=url,
                            title=f"PDF Document: {url.split('/')[-1]}",
                            text=f"Binary PDF file available at: {url}",
                            html="",
                            metadata={"binary_type": "pdf", "scraped": False},
                            content_type="application/pdf"
                        )
                        successful_results.append(result)
                        logs.append(f"✅ Created placeholder for binary PDF: {url}")
                    else:
                        # For other binary types, create appropriate placeholders
                        file_type = url.split('.')[-1].upper()
                        result = ScrapedContent(
                            url=url,
                            title=f"{file_type} Document: {url.split('/')[-1]}",
                            text=f"Binary {file_type} file available at: {url}",
                            html="",
                            metadata={"binary_type": file_type.lower(), "scraped": False},
                            content_type=f"application/{file_type.lower()}"
                        )
                        successful_results.append(result)
                        logs.append(f"✅ Created placeholder for binary {file_type}: {url}")
                else:
                    # Use existing scraper for HTML content
                    scraper = get_scraper()
                    result = await scraper.scrape_url(url, dynamic=False)
                    
                    if result.is_successful():
                        successful_results.append(result)
                        logs.append(f"✅ Successfully scraped: {url}")
                    else:
                        logs.append(f"❌ Failed to scrape: {url} - {result.error}")
            except Exception as e:
                logs.append(f"❌ Error processing URL {url}: {str(e)}")
                logger.error(f"Error processing URL {url}: {str(e)}")
        
        return successful_results
        
    except Exception as e:
        logs.append(f"❌ Ошибка при скрейпинге: {str(e)}")
        logger.error(f"Ошибка при скрейпинге для запроса '{query}': {str(e)}")
        return []


async def run_multiple_searches(query: str, logs: list, force_refresh: bool = False) -> Dict[str, List]:
    """
    Выполняет только один поиск вместо нескольких, ограничивая количество результатов до 3.
    """
    logs.append(f"🔄 Запуск поиска для запроса: '{query}'")
    
    # Выполняем только один поиск
    try:
        general_results = await search_and_scrape(query, logs, max_results=3, force_refresh=force_refresh)
        
        # Объединяем результаты в словарь 
        results = {
            "general": general_results,
            # Для обратной совместимости оставляем пустые списки
            "legal": [],
            "recent": []
        }
        
        total_results = len(general_results)
        logs.append(f"📊 Получено всего {total_results} результатов из поиска")
        
        return results
    
    except Exception as e:
        logs.append(f"❌ Ошибка при выполнении поиска: {str(e)}")
        logging.error(f"Ошибка при выполнении поиска: {str(e)}")
        return {"legal": [], "recent": [], "general": []}