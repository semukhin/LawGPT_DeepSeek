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
import os
from playwright.async_api import async_playwright

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
        proxy: Optional[str] = None,
        timeout: int = 20,
        max_retries: int = 2,
        max_concurrent: int = 8
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        
        # Список User-Agent для ротации
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
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
    
    async def _try_simple_scraping(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Пытается получить контент обычным GET-запросом"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    ssl=self.ssl_context,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.text()
        except:
            return None
    
    async def _try_playwright_scraping(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Пытается получить контент с помощью Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                await page.set_extra_http_headers(headers)
                
                response = await page.goto(url, wait_until='networkidle')
                if not response or response.status != 200:
                    return None
                
                # Ждем загрузку динамического контента
                try:
                    await page.wait_for_selector('main, article, .content, #content', timeout=5000)
                except:
                    pass  # Игнорируем ошибку, если селекторы не найдены
                
                return await page.content()
                
        except Exception as e:
            logging.error(f"Ошибка при использовании Playwright для {url}: {e}")
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