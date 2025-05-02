"""
Модуль для поиска информации в интернете.
Выполняет поиск через Google Custom Search API и извлекает содержимое найденных страниц.
"""
import requests
import urllib3
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse, urljoin
import os
import sys
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import aiohttp
from bs4 import Comment
from app.utils import ensure_correct_encoding, sanitize_search_results, validate_messages, validate_context
from app.search_result import SearchResult
import ssl
import random
from app.utils.text_utils import extract_keywords_ru

# Добавляем путь к third_party для корректного импорта shandu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
   sys.path.insert(0, THIRD_PARTY_DIR)

from third_party.shandu.scraper import ScrapedContent
from app.services.web_scraper import WebScraper

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
MAX_SCRAPE_RESULTS = 10   # Максимальное количество ссылок для скрейпинга (ТОП-7)
MAX_CONTENT_LENGTH = 30000  # Максимальная длина текста из одного источника

# В начале файла
logging.info(f"Google API Key настроен: {'Да' if len(GOOGLE_API_KEY) > 0 else 'Нет'}")
logging.info(f"Google CX настроен: {'Да' if len(GOOGLE_CX) > 0 else 'Нет'}")

# Создаем единственный экземпляр WebScraper
_scraper = None

def get_scraper() -> WebScraper:
   """
   Получает или создает экземпляр WebScraper.
   
   Returns:
       WebScraper: Экземпляр скрапера
   """
   global _scraper
   if _scraper is None:
       _scraper = WebScraper(
           timeout=20,
           max_retries=2,
           max_concurrent=8
       )
       logger.info("Инициализирован WebScraper")
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
    # Проверяем, включен ли поиск в Google в настройках
    google_search_enabled = os.environ.get("GOOGLE_SEARCH_ENABLED", "True").lower() == "true"
    if not google_search_enabled:
        logging.info("🔍 google_search: Поиск в Google отключен в настройках")
        logs.append("⚠️ Поиск в Google отключен в настройках")
        return []

    # --- Новый блок: автоматическое извлечение ключевых фраз ---
    orig_query = query.strip()
    if len(orig_query) > 200:
        keywords_query = extract_keywords_ru(orig_query)
        logs.append(f"🔑 Извлечены ключевые слова для поиска: {keywords_query}")
        logging.info(f"🔑 Исходный запрос: {orig_query}")
        logging.info(f"🔑 Ключевые слова для поиска: {keywords_query}")
        clean_query = keywords_query
    else:
        clean_query = ensure_correct_encoding(orig_query)
        logging.info(f"🔍 google_search: Начинаем поиск для '{clean_query}'")
    
    # Очищаем ключи API от кавычек
    api_key = GOOGLE_API_KEY.replace('"', '') if GOOGLE_API_KEY else ""
    cx_id = GOOGLE_CX.replace('"', '') if GOOGLE_CX else ""
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx_id,
        "q": clean_query,
        "num": min(max_results, 10),  # Google API ограничивает результаты
        "safe": "active",
        "hl": "ru",  # Язык интерфейса
        "gl": "ru",  # Геолокация для поиска
        "lr": "lang_ru"  # Ограничение по языку
    }
    
    logs.append(f"🔍 Выполнение поиска Google Custom Search API для запроса: '{clean_query}'")
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
        
        if status_code == 403:
            error_msg = "Доступ запрещен (403). Возможно, API ключ недействителен или превышена квота запросов."
            logging.error(f"❌ google_search: {error_msg}")
            logs.append(f"❌ Ошибка Google API: {error_msg}")
            try:
                error_details = response.json()
                if 'error' in error_details:
                    logging.error(f"Детали ошибки Google API: {error_details['error']}")
                    logs.append(f"Детали ошибки: {error_details['error'].get('message', 'Нет дополнительной информации')}")
            except:
                pass
            return []
        
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
        for i, link in enumerate(valid_links[:10]):
            logging.info(f"URL {i+1}: {link}")
            logs.append(f"URL {i+1}: {link}")
        
        return valid_links
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logs.append(f"❌ Ошибка при поиске в Google: {error_msg}")
        logger.error(f"Ошибка Google API: {error_msg}")
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

def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Очищает BeautifulSoup объект от ненужных элементов.
    
    Args:
        soup: BeautifulSoup объект для очистки
        
    Returns:
        BeautifulSoup: Очищенный объект
    """
    # Удаляем все скрипты и стили
    for script in soup(["script", "style", "meta", "link", "noscript", "iframe", "header", "footer", "nav"]):
        script.decompose()

    # Удаляем все комментарии
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    return soup

def get_text_from_soup(soup: BeautifulSoup) -> str:
    """
    Извлекает текст из BeautifulSoup объекта с сохранением структуры.
    
    Args:
        soup: BeautifulSoup объект
        
    Returns:
        str: Извлеченный текст
    """
    # Находим основной контент
    main_content = None
    
    # Пробуем найти основной контент по популярным классам и ID
    content_identifiers = [
        {"class_": ["content", "article", "post", "entry", "main", "text"]},
        {"id": ["content", "article", "post", "entry", "main", "text"]}
    ]
    
    for identifier in content_identifiers:
        main_content = soup.find(**identifier)
        if main_content:
            break
    
    # Если не нашли по классам/ID, берем весь body
    if not main_content:
        main_content = soup.body if soup.body else soup
    
    # Извлекаем текст с сохранением структуры
    text_parts = []
    
    for element in main_content.descendants:
        if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = element.get_text(strip=True)
            if text:
                text_parts.append(text + '\n')
        elif element.name == 'br':
            text_parts.append('\n')
        elif element.name in ['ul', 'ol']:
            for li in element.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    text_parts.append(f"• {text}\n")
    
    return ''.join(text_parts)

def extract_title(soup: BeautifulSoup) -> str:
    """
    Извлекает заголовок страницы.
    
    Args:
        soup: BeautifulSoup объект
        
    Returns:
        str: Заголовок страницы
    """
    # Сначала ищем h1
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        if title:
            return title
    
    # Если h1 не найден или пустой, ищем title
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text(strip=True)
    
    return "Без заголовка"

def get_relevant_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Извлекает URL релевантных изображений.
    
    Args:
        soup: BeautifulSoup объект
        base_url: Базовый URL страницы
        
    Returns:
        List[str]: Список URL изображений
    """
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Преобразуем относительные URL в абсолютные
            full_url = urljoin(base_url, src)
            # Фильтруем рекламные и технические изображения
            if not any(x in full_url.lower() for x in ['avatar', 'logo', 'banner', 'ad', 'icon']):
                images.append(full_url)
    return images

async def scrape_with_beautifulsoup(url: str) -> Optional[ScrapedContent]:
    """
    Скрейпит веб-страницу с помощью BeautifulSoup.
    
    Args:
        url (str): URL для скрейпинга
        
    Returns:
        Optional[ScrapedContent]: Результат скрейпинга или None в случае ошибки
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Специальные заголовки для e.law.ru
        if 'e.law.ru' in url:
            headers.update({
                'Referer': 'https://e.law.ru/',
                'Origin': 'https://e.law.ru',
                'Host': 'e.law.ru'
            })
            
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, ssl=False, timeout=30) as response:
                if response.status != 200:
                    logging.error(f"Ошибка при скрейпинге {url}: статус {response.status}")
                    return None
                    
                # Определяем кодировку из заголовков или meta-тегов
                content_type = response.headers.get('Content-Type', '')
                charset = None
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].strip()
                
                content = await response.read()
                
                # Пробуем разные кодировки
                for encoding in [charset, 'utf-8', 'windows-1251', 'cp1251', 'latin1']:
                    if encoding:
                        try:
                            html_content = content.decode(encoding)
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue
                else:
                    # Если ни одна кодировка не подошла, используем utf-8 с игнорированием ошибок
                    html_content = content.decode('utf-8', errors='ignore')
                
                # Для e.law.ru пробуем извлечь контент после выполнения JavaScript
                if 'e.law.ru' in url and 'window.__INITIAL_STATE__' in html_content:
                    try:
                        # Извлекаем данные из JavaScript
                        start_idx = html_content.find('window.__INITIAL_STATE__ = ') + len('window.__INITIAL_STATE__ = ')
                        end_idx = html_content.find('</script>', start_idx)
                        json_data = html_content[start_idx:end_idx].strip().rstrip(';')
                        # Здесь можно распарсить JSON и извлечь нужный контент
                        # ...
                    except Exception as e:
                        logging.error(f"Ошибка при извлечении данных из JavaScript на e.law.ru: {e}")
                
                soup = BeautifulSoup(html_content, 'html.parser')
                soup = clean_soup(soup)
                
                title = extract_title(soup)
                text = get_text_from_soup(soup)
                
                if not text:
                    logging.warning(f"Не удалось извлечь текст из {url}")
                    return None
                    
                return ScrapedContent(
                    url=url,
                    title=title,
                    text=text,
                    html=html_content,
                    metadata={},
                    content_type="text/html"
                )
                
    except asyncio.TimeoutError:
        logging.error(f"Таймаут при скрейпинге {url}")
        return None
    except Exception as e:
        logging.error(f"Ошибка при скрейпинге {url} с BeautifulSoup: {e}, message='{str(e)}', url='{url}'")
        return None

async def filter_urls(urls: List[str], excluded_domains: List[str] = None) -> List[str]:
    """
    Фильтрует URL на основе списка исключаемых доменов.
    
    Args:
        urls (List[str]): Список URL для фильтрации
        excluded_domains (List[str], optional): Список доменов для исключения
        
    Returns:
        List[str]: Отфильтрованный список URL
    """
    if excluded_domains is None:
        excluded_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
            'linkedin.com', 'pinterest.com', 'tiktok.com', 'reddit.com',
            'vk.com', 'ok.ru', 'mail.ru', 'yandex.ru'
        ]
    
    filtered_urls = []
    for url in urls:
        if not any(excluded in url.lower() for excluded in excluded_domains):
            filtered_urls.append(url)
    return filtered_urls

async def extract_main_content(html_content: str, url: str) -> Tuple[str, List[str]]:
    """
    Извлекает основной контент из HTML с сохранением структуры.
    
    Args:
        html_content (str): HTML контент
        url (str): URL страницы
        
    Returns:
        Tuple[str, List[str]]: (основной контент, список URL изображений)
    """
    try:
        soup = BeautifulSoup(html_content, "lxml")
        soup = clean_soup(soup)
        
        # Извлекаем основной контент
        main_content = None
        content_identifiers = [
            {"class_": ["content", "article", "post", "entry", "main", "text"]},
            {"id": ["content", "article", "post", "entry", "main", "text"]}
        ]
        
        for identifier in content_identifiers:
            main_content = soup.find(**identifier)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Извлекаем текст с сохранением структуры
        text_parts = []
        for element in main_content.descendants:
            if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(text + '\n')
            elif element.name == 'br':
                text_parts.append('\n')
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if text:
                        text_parts.append(f"• {text}\n")
        
        # Извлекаем изображения
        images = get_relevant_images(soup, url)
        
        return ''.join(text_parts), images
    except Exception as e:
        logging.error(f"Ошибка при извлечении контента: {str(e)}")
        return "", []

async def process_scraped_data(scraped_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Обрабатывает и форматирует результаты скрейпинга.
    
    Args:
        scraped_data: Список результатов скрейпинга
        
    Returns:
        List[Dict[str, Any]]: Обработанные результаты
    """
    processed_data = []
    
    for item in scraped_data:
        try:
            # Проверяем и исправляем кодировку текста
            if isinstance(item.get('text'), str):
                item['text'] = ensure_correct_encoding(item['text'])
            
            # Проверяем и исправляем кодировку заголовка
            if isinstance(item.get('title'), str):
                item['title'] = ensure_correct_encoding(item['title'])
                
            # Проверяем и исправляем кодировку URL
            if isinstance(item.get('url'), str):
                item['url'] = ensure_correct_encoding(item['url'])
                
            processed_data.append(item)
            
        except Exception as e:
            logging.error(f"Ошибка при обработке результата скрейпинга: {str(e)}")
            continue
            
    return processed_data

async def search_and_scrape(query: str, logs: list, max_results: int = MAX_SCRAPE_RESULTS, force_refresh: bool = False) -> list:
    """
    Выполняет поиск и скрейпинг информации по запросу.
    
    Args:
        query: Поисковый запрос
        logs: Список для логирования
        max_results: Максимальное количество результатов
        force_refresh: Принудительное обновление кэша
        
    Returns:
        list: Список найденных и обработанных результатов
    """
    session = None
    try:
        # Создаем одну сессию для всех запросов
        session = aiohttp.ClientSession()
        
        # Проверяем кодировку запроса
        query = ensure_correct_encoding(query)
        
        # Получаем ссылки через Google API
        links = google_search(query, logs, max_results)
        if not links:
            return []
            
        # Фильтруем ссылки
        filtered_links = await filter_urls(links)
        if not filtered_links:
            return []
            
        # Скрейпим контент
        scraped_results = []
        for url in filtered_links[:max_results]:
            try:
                content = await scrape_with_beautifulsoup(url)
                if content and content.text.strip():
                    scraped_results.append({
                        'url': url,
                        'text': content.text,
                        'title': content.title
                    })
            except Exception as e:
                logging.error(f"Ошибка при скрейпинге {url}: {str(e)}")
                continue
                
        # Обрабатываем результаты
        processed_results = await process_scraped_data(scraped_results)
        
        return processed_results
        
    except Exception as e:
        logging.error(f"Ошибка в search_and_scrape: {str(e)}")
        return []
    finally:
        # Закрываем сессию в блоке finally
        if session:
            await session.close()


async def run_multiple_searches(query: str, logs: list, force_refresh: bool = False) -> Dict[str, List]:
    """
    Выполняет только один поиск вместо нескольких, ограничивая количество результатов до MAX_SCRAPE_RESULTS (ТОП-7).
    """
    logs.append(f"🔄 Запуск поиска для запроса: '{query}'")
    
    # Выполняем только один поиск с ограничением до MAX_SCRAPE_RESULTS (7) ссылок
    try:
        # Получаем ссылки через Google API
        links = google_search(query, logs, max_results=MAX_SCRAPE_RESULTS)
        if not links:
            return {"general": [], "legal": [], "recent": []}
            
        # Скрейпим контент
        scraped_results = []
        for url in links[:MAX_SCRAPE_RESULTS]:
            try:
                content = await scrape_with_beautifulsoup(url)
                if content and content.text.strip():
                    scraped_results.append({
                        'url': url,
                        'title': content.title,
                        'text': content.text[:2000],  # Берем до 2000 символов из каждого источника
                        'source': 'google'
                    })
            except Exception as e:
                logging.error(f"Ошибка при скрейпинге {url}: {str(e)}")
                continue
                
        # Обрабатываем результаты
        processed_results = await process_scraped_data(scraped_results)
        
        # Объединяем результаты в словарь 
        results = {
            "general": processed_results,
            # Для обратной совместимости оставляем пустые списки
            "legal": [],
            "recent": []
        }
        
        total_results = len(processed_results)
        logs.append(f"📊 Получено всего {total_results} результатов из поиска (максимум {MAX_SCRAPE_RESULTS})")
        
        return results
    
    except Exception as e:
        logs.append(f"❌ Ошибка при выполнении поиска: {str(e)}")
        logging.error(f"Ошибка при выполнении поиска: {str(e)}")
        return {"legal": [], "recent": [], "general": []}

async def search_internet(query: str, max_results: int = 5) -> List[SearchResult]:
    """
    Выполняет поиск в интернете с помощью Google.
    
    Args:
        query: Поисковый запрос
        max_results: Максимальное количество результатов
        
    Returns:
        List[SearchResult]: Список результатов поиска
    """
    try:
        # Получаем ссылки через Google API
        links = google_search(query, [], max_results)
        if not links:
            return []
            
        # Скрейпим контент
        scraper = get_scraper()
        results = []
        
        for url in links[:max_results]:
            try:
                content = await scraper.scrape_url(url)
                if content and content.is_successful():
                    result = SearchResult(
                        url=url,
                        title=content.title,
                        snippet=content.text[:200] + "...",
                        source="google"
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Ошибка при скрейпинге {url}: {e}")
                continue
                
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при поиске в интернете: {e}")
        return []

async def _async_google_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Асинхронный поиск через Google Custom Search API.
    
    Args:
        query: Поисковый запрос
        max_results: Максимальное количество результатов
        
    Returns:
        Список результатов поиска
    """
    try:
        # Получаем ключи API из переменных окружения
        api_key = os.getenv("GOOGLE_API_KEY")
        cx = os.getenv("GOOGLE_CX")
        
        if not api_key or not cx:
            logger.error("Отсутствуют ключи Google API")
            return []
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "num": max_results
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка Google API: {response.status}")
                    return []
                    
                data = await response.json()
                if "items" not in data:
                    return []
                    
                return [{
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google",
                    "date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time"),
                    "metadata": item.get("pagemap", {})
                } for item in data["items"]]
                
    except Exception as e:
        logger.error(f"Ошибка при поиске в Google: {e}")
        return []