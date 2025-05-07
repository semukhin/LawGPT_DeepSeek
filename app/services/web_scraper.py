"""
Сервис для скрапинга веб-страниц с поддержкой различных источников.
"""
import aiohttp
import asyncio
from typing import List, Tuple
from bs4 import BeautifulSoup
from bs4.element import Comment
from app.models.scraping import ScrapedContent
from app.services.tavily_service import TavilyService
from app.utils.logger import get_logger, LogLevel
from playwright.async_api import async_playwright
from urllib.parse import urlparse
import re

class ContentExtractor:
    """Класс для извлечения контента из HTML."""
    
    def __init__(self):
        self.logger = get_logger()
        
    async def extract_content(self, soup: BeautifulSoup, url: str) -> Tuple[str, str, List[str]]:
        """
        Извлекает контент из HTML с учетом структуры страницы.
        
        Returns:
            Tuple[str, str, List[str]]: (title, text, images)
        """
        # Извлекаем заголовок
        title = self._extract_title(soup)
        
        # Определяем тип страницы
        page_type = self._detect_page_type(soup, url)
        
        # Удаляем ненужные элементы
        self._clean_soup(soup)
        
        # Извлекаем основной контент
        text = self._extract_main_content(soup, page_type)
        
        # Извлекаем изображения
        images = self._extract_images(soup)
        
        return title, text, images
        
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Извлекает заголовок страницы."""
        title = ""
        if soup.title:
            title = soup.title.string
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        return title or ""
        
    def _detect_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """Определяет тип страницы для оптимизации извлечения."""
        domain = urlparse(url).netloc
        
        # Проверяем наличие характерных элементов
        if soup.find('article'):
            return 'article'
        elif soup.find(class_=re.compile(r'.*article.*|.*post.*|.*content.*')):
            return 'article'
        elif soup.find(class_=re.compile(r'.*product.*|.*item.*')):
            return 'product'
        elif soup.find(class_=re.compile(r'.*forum.*|.*comment.*')):
            return 'forum'
            
        # Проверяем домен
        if 'blog' in domain or 'news' in domain:
            return 'article'
        elif 'forum' in domain:
            return 'forum'
        elif 'shop' in domain or 'store' in domain:
            return 'product'
            
        return 'general'
        
    def _clean_soup(self, soup: BeautifulSoup) -> None:
        """Удаляет ненужные элементы."""
        # Удаляем скрипты, стили и другие технические элементы
        for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg']):
            tag.decompose()
            
        # Удаляем навигацию, хедер, футер
        for tag in soup.find_all(['nav', 'header', 'footer']):
            tag.decompose()
            
        # Удаляем комментарии
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        # Удаляем пустые элементы
        for tag in soup.find_all():
            if not tag.get_text(strip=True) and not tag.find_all(['img', 'video']):
                tag.decompose()
                
    def _extract_main_content(self, soup: BeautifulSoup, page_type: str) -> str:
        """Извлекает основной контент с учетом типа страницы."""
        content = None
        
        if page_type == 'article':
            # Ищем основной контент статьи
            content = (
                soup.find('article') or
                soup.find(class_=re.compile(r'.*article.*|.*post.*|.*content.*')) or
                soup.find(['main', 'article']) or
                soup.find(class_=re.compile(r'.*main.*|.*content.*'))
            )
        elif page_type == 'product':
            # Ищем описание продукта
            content = (
                soup.find(class_=re.compile(r'.*product.*description.*')) or
                soup.find(class_=re.compile(r'.*description.*')) or
                soup.find(class_=re.compile(r'.*product.*detail.*'))
            )
        elif page_type == 'forum':
            # Ищем сообщения форума
            content = (
                soup.find(class_=re.compile(r'.*forum.*content.*|.*message.*content.*')) or
                soup.find_all(class_=re.compile(r'.*post.*|.*message.*'))
            )
            
        if not content:
            content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            
        if not content:
            content = soup
            
        # Извлекаем текст с сохранением структуры
        text_parts = []
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
            text = element.get_text(strip=True)
            if text:
                text_parts.append(text)
                
        return '\n\n'.join(text_parts)
        
    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Извлекает URL изображений."""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and not src.startswith('data:'):
                images.append(src)
        return images

class WebScraper:
    """Сервис для скрапинга веб-страниц."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 2, max_concurrent: int = 5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self.logger = get_logger()
        self.tavily_service = TavilyService()
        self.content_extractor = ContentExtractor()
        
    async def scrape_url(self, url: str, dynamic: bool = False) -> ScrapedContent:
        """
        Скрапит контент с URL. Если dynamic=True, использует Playwright.
        
        Args:
            url: URL для скрапинга
            dynamic: Использовать ли Playwright для JavaScript-рендеринга
            
        Returns:
            ScrapedContent с результатами скрапинга
        """
        if not dynamic:
            return await self._scrape_static(url)
        else:
            return await self._scrape_dynamic(url)
            
    async def _scrape_static(self, url: str) -> ScrapedContent:
        """Скрапит статический контент."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status != 200:
                        return ScrapedContent(
                            url=url,
                            title="",
                            text="",
                            error=f"HTTP Error: {response.status}"
                        )
                    
                    html = await response.text()
                    return await self._process_html(html, url)
                    
        except Exception as e:
            self.logger.log(f"Ошибка при скрапинге {url}: {str(e)}", LogLevel.ERROR)
            return ScrapedContent(
                url=url,
                title="",
                text="",
                error=str(e)
            )
            
    async def _scrape_dynamic(self, url: str) -> ScrapedContent:
        """Скрапит динамический контент с помощью Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                await page.goto(url, wait_until='networkidle')
                
                # Прокручиваем страницу для загрузки ленивого контента
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)  # Ждем загрузки
                
                html = await page.content()
                await browser.close()
                
                return await self._process_html(html, url)
                
        except Exception as e:
            self.logger.log(f"Ошибка при динамическом скрапинге {url}: {str(e)}", LogLevel.ERROR)
            return ScrapedContent(
                url=url,
                title="",
                text="",
                error=str(e)
            )
            
    async def _process_html(self, html: str, url: str) -> ScrapedContent:
        """Обрабатывает HTML и создает ScrapedContent."""
        soup = BeautifulSoup(html, 'lxml')
        title, text, images = await self.content_extractor.extract_content(soup, url)
        
        return ScrapedContent(
            url=url,
            title=title,
            text=text,
            html=html,
            images=images,
            metadata={
                "domain": urlparse(url).netloc,
                "content_length": len(text),
                "images_count": len(images)
            }
        )
        
    async def scrape_urls(self, urls: List[str], dynamic: bool = False) -> List[ScrapedContent]:
        """
        Скрапит контент с нескольких URL параллельно.
        
        Args:
            urls: Список URL для скрапинга
            dynamic: Использовать ли Playwright для JavaScript-рендеринга
            
        Returns:
            Список ScrapedContent с результатами
        """
        if dynamic:
            # Для динамического контента ограничиваем параллельность
            semaphore = asyncio.Semaphore(min(self.max_concurrent, 3))
            
            async def scrape_with_semaphore(url: str) -> ScrapedContent:
                async with semaphore:
                    return await self._scrape_dynamic(url)
                    
            tasks = [scrape_with_semaphore(url) for url in urls]
        else:
            # Для статического контента используем больше параллельных запросов
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def scrape_with_semaphore(url: str) -> ScrapedContent:
                async with semaphore:
                    return await self._scrape_static(url)
                    
            tasks = [scrape_with_semaphore(url) for url in urls]
            
        return await asyncio.gather(*tasks) 