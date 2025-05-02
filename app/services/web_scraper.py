"""
Модуль для скрейпинга веб-страниц с поддержкой кэширования и обработки ошибок.
"""
import ssl
import time
import random
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from third_party.shandu.scraper import ScrapedContent
from functools import lru_cache
from playwright.async_api import async_playwright
from collections import defaultdict
import chardet

# Добавим конфигурацию для доступных источников
DOMAIN_HANDLERS = {
    # Публичные источники
    'consultant.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.document-page',
        'rate_limits': {
            'requests_per_minute': 20,
            'pause_between_requests': 3.0
        }
    },
    'garant.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.document-content',
        'rate_limits': {
            'requests_per_minute': 20,
            'pause_between_requests': 3.0
        }
    },
    'sudact.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.result-text',
        'rate_limits': {
            'requests_per_minute': 15,
            'pause_between_requests': 4.0
        }
    },
    'kad.arbitr.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.b-case-header',
        'rate_limits': {
            'requests_per_minute': 10,
            'pause_between_requests': 6.0
        }
    },
    'pravo.gov.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.document-content',
        'rate_limits': {
            'requests_per_minute': 20,
            'pause_between_requests': 3.0
        }
    },
    
    # Платные источники (оставляем конфигурацию на будущее)
    'zakon.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.article-content',
        'public_only': True  # Флаг для работы только с публичным контентом
    },
    'e.law.ru': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        'use_javascript': True,
        'wait_for': '.article__content',
        'public_only': True  # Флаг для работы только с публичным контентом
    }
}

# Список альтернативных источников для замены платного контента
ALTERNATIVE_SOURCES = {
    'zakon.ru': ['consultant.ru', 'garant.ru'],
    'e.law.ru': ['consultant.ru', 'garant.ru'],
    'estatut.ru': ['consultant.ru', 'garant.ru']
}

class WebScraper:
    """Advanced web scraper with support for both static and dynamic pages."""
    
    def __init__(
        self,
        timeout: int = 20,
        max_retries: int = 2,
        max_concurrent: int = 8
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        
        # Список User-Agent для ротации
        self.user_agents = [
            # Десктоп
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Мобильные
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.234 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
            # Боты и редкие
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
        ]
        
        # Базовые заголовки для всех запросов
        self.base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # SSL-контекст без проверки
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Кэш для результатов скрейпинга
        self._cache = {}
        
        # Для отслеживания запросов
        self._domain_request_times = {}
        
        self.last_request_time = defaultdict(float)
        self.domain_min_interval = {
            "consultant.ru": 2.0,
            "garant.ru": 2.0,
            "default": 1.0
        }
        logging.basicConfig(
            filename='logs/scraper_errors.log',
            level=logging.WARNING,
            format='%(asctime)s %(levelname)s %(message)s'
        )
        
    async def scrape_url(self, url: str) -> Optional[ScrapedContent]:
        """Скрейпит контент с URL с учетом особенностей страницы"""
        domain = urlparse(url).netloc
        
        # Проверяем кэш
        if url in self._cache:
            return self._cache[url]
        
        # Применяем базовые ограничения по частоте запросов
        await self._apply_rate_limits(domain)
        
        for attempt in range(self.max_retries):
            try:
                # Подготавливаем заголовки для запроса
                headers = self._prepare_headers(url)
                
                # Пробуем сначала обычный скрейпинг
                content = await self._try_simple_scraping(url, headers)
                if content and self._is_valid_content(content):
                    return self._process_and_cache(content, url)
                
                # Если не получилось, пробуем через Playwright
                content = await self._try_playwright_scraping(url, headers)
                if content:
                    return self._process_and_cache(content, url)
                
                # Если обе попытки не удались, ждем перед следующей
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                logging.error(f"Ошибка при скрейпинге {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
        
        return None
    
    def _prepare_headers(self, url: str) -> Dict[str, str]:
        """Подготавливает заголовки для запроса"""
        headers = self.base_headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        
        domain = urlparse(url).netloc
        headers['Host'] = domain
        headers['Origin'] = f"https://{domain}"
        headers['Referer'] = f"https://{domain}/"
        
        return headers
    
    async def _try_simple_scraping(self, url: str, headers: dict) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    'headers': headers,
                    'ssl': self.ssl_context,
                    'timeout': self.timeout
                }
                async with session.get(url, **kwargs) as response:
                    if response.status != 200:
                        logging.warning(f"HTTP error {response.status} for {url}")
                        return None
                    try:
                        # Пробуем как utf-8
                        html_text = await response.text()
                        return html_text
                    except UnicodeDecodeError:
                        content = await response.read()
                        # Пробуем windows-1251
                        try:
                            html_text = content.decode('windows-1251')
                            return html_text
                        except UnicodeDecodeError:
                            # Автоопределение через chardet
                            detected = chardet.detect(content)
                            encoding = detected['encoding'] or 'utf-8'
                            html_text = content.decode(encoding, errors='replace')
                            logging.info(f"Использована кодировка {encoding} для {url}")
                            return html_text
        except Exception as e:
            logging.warning(f"Ошибка при скрейпинге {url} | User-Agent: {headers['User-Agent']} | Ошибка: {e}")
            return None
    
    async def _try_playwright_scraping(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Пытается получить контент с помощью Playwright"""
        try:
            async with async_playwright() as p:
                browser_args = ["--disable-dev-shm-usage", "--no-sandbox", "--disable-setuid-sandbox"]
                browser = await p.chromium.launch(headless=True, args=browser_args)
                context_args = {'user_agent': headers['User-Agent']}
                context = await browser.new_context(**context_args)
                page = await context.new_page()
                await page.set_extra_http_headers(headers)
                response = await page.goto(url, wait_until='networkidle')
                if not response or response.status != 200:
                    logging.warning(f"Playwright HTTP error {response.status if response else 'no response'} for {url}")
                    return None
                # Эмуляция поведения пользователя
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(random.uniform(1, 3))
                return await page.content()
        except Exception as e:
            logging.warning(f"Playwright ошибка для {url} | Ошибка: {e}")
            return None
    
    def _is_valid_content(self, html: str) -> bool:
        """Проверяет, является ли полученный контент валидным"""
        if not html:
            return False
            
        # Проверяем наличие основных HTML-тегов
        return all(tag in html.lower() for tag in ['<html', '<body'])
    
    def _process_and_cache(self, html: str, url: str) -> ScrapedContent:
        """Обрабатывает HTML и кэширует результат"""
        content = self._process_html(html, url)
        if content and content.is_successful():
            self._cache[url] = content
        return content
    
    def _process_html(self, html: str, url: str) -> Optional[ScrapedContent]:
        """Обрабатывает HTML и создает ScrapedContent"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Удаляем ненужные элементы
            for tag in ['script', 'style', 'iframe', 'noscript']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Извлекаем основной контент
            main_content = None
            for selector in ['main', 'article', '.content', '#content', '.article', '.post', '.entry']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.body if soup.body else soup
            
            # Извлекаем текст с сохранением структуры
            text_parts = []
            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(text)
            
            text = '\n\n'.join(text_parts)
            
            return ScrapedContent(
                url=url,
                title=soup.title.string if soup.title else '',
                text=text,
                html=str(soup),
                metadata={
                    'domain': urlparse(url).netloc,
                    'length': len(text)
                }
            )
            
        except Exception as e:
            logging.error(f"Ошибка при обработке HTML {url}: {e}")
            return None
    
    async def _apply_rate_limits(self, domain: str):
        """Применяет базовые ограничения на частоту запросов"""
        min_interval = self.domain_min_interval.get(domain, self.domain_min_interval["default"])
        now = time.time()
        elapsed = now - self.last_request_time[domain]
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self.last_request_time[domain] = time.time()
        
        if domain not in self._domain_request_times:
            self._domain_request_times[domain] = []
        
        current_time = time.time()
        
        # Очищаем старые запросы
        self._domain_request_times[domain] = [
            t for t in self._domain_request_times[domain]
            if current_time - t < 60
        ]
        
        # Базовое ограничение - не более 20 запросов в минуту
        if len(self._domain_request_times[domain]) >= 20:
            await asyncio.sleep(3)
        
        self._domain_request_times[domain].append(current_time) 

# Для сохранения промптов и респондов:
def save_prompt(prompt_text, prompt_id=None):
    fname = f"prompts/prompt_{prompt_id or int(time.time())}.txt"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(prompt_text)

def save_response(response_text, response_id=None):
    fname = f"responses/response_{response_id or int(time.time())}.txt"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(response_text) 