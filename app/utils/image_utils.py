from bs4 import BeautifulSoup
from typing import List

def get_relevant_images(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Извлекает релевантные изображения из HTML-контента.
    
    Args:
        soup: BeautifulSoup объект с HTML-контентом
        base_url: Базовый URL для разрешения относительных путей
        
    Returns:
        List[str]: Список URL изображений
    """
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            if src.startswith('http'):
                images.append(src)
            else:
                # Преобразуем относительный путь в абсолютный
                if src.startswith('/'):
                    images.append(f"{base_url.rstrip('/')}{src}")
                else:
                    images.append(f"{base_url.rstrip('/')}/{src}")
    return images

def extract_title(soup: BeautifulSoup) -> str:
    """
    Извлекает заголовок из HTML-контента.
    
    Args:
        soup: BeautifulSoup объект с HTML-контентом
        
    Returns:
        str: Заголовок страницы
    """
    title = soup.find('title')
    if title:
        return title.text.strip()
    return "" 