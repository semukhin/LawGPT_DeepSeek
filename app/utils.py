import requests
import urllib3
import time
import logging
import asyncio
from functools import wraps
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def filter_binary_for_logs(text):
    """
    Фильтрует бинарные и непечатаемые символы из текста для безопасного логирования.
    Обрабатывает специфические ошибки Gemini API для лучшей диагностики.

    Args:
        text: Исходный текст, который может содержать бинарные данные

    Returns:
        str: Отфильтрованный текст, содержащий только печатаемые ASCII символы
    """
    if not isinstance(text, str):
        text = str(text)

    # Специальная обработка ошибок Gemini API
    if "finish_reason" in text and "requires the response to contain a valid" in text:
        # Выделяем и возвращаем информативную часть сообщения об ошибке
        if "finish_reason](https://ai.google.dev/api/generate-content#finishreason) is 4" in text:
            return "Ошибка Gemini API: finish_reason=4 (авторские права). Gemini считает, что документ содержит защищенный материал."
        elif "finish_reason](https://ai.google.dev/api/generate-content#finishreason) is 5" in text:
            return "Ошибка Gemini API: finish_reason=5 (безопасность). Gemini считает, что документ содержит небезопасный контент."
        elif "finish_reason" in text:
            try:
                # Пытаемся извлечь код finish_reason
                import re
                match = re.search(r"finish_reason.*?is\s+(\d+)", text)
                if match:
                    code = match.group(1)
                    return f"Ошибка Gemini API: finish_reason={code}. Ответ не содержит текста из-за ограничений API."
            except Exception:
                pass

    # Заменяем непечатаемые символы на '?'
    filtered = ''.join(c if c.isascii() and c.isprintable() else '?' for c in text)

    # Если строка слишком длинная, обрезаем её
    max_log_length = 500
    if len(filtered) > max_log_length:
        filtered = filtered[:max_log_length] + "... [обрезано]"

    return filtered

session = requests.Session()
session.verify = False  # Отключаем проверку SSL

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_url_content(url, headers=None, timeout=10):
    """Глобальная функция для запросов без проверки SSL."""
    if headers is None:
        headers = DEFAULT_HEADERS  # Добавляем User-Agent
    else:
        headers.update(DEFAULT_HEADERS)  # Объединяем заголовки

    try:
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR]: HTTP ошибка для {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR]: Ошибка сети при запросе {url}: {e}")
    return None

logging.basicConfig(level=logging.INFO)

def save_text_to_file(text, output_file_path):
    """Сохраняет текст в файл."""
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении файла {output_file_path}: {e}")
        return False

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
            # Пробуем перекодировать через bytes для исправления возможных проблем
            return text.encode('utf-8', errors='ignore').decode('utf-8')
        except UnicodeError:
            try:
                # Пробуем определить кодировку и перекодировать
                import chardet
                encoding = chardet.detect(text.encode())['encoding'] or 'utf-8'
                return text.encode(encoding, errors='ignore').decode('utf-8')
            except Exception:
                # В крайнем случае просто игнорируем проблемные символы
                return text.encode('ascii', errors='ignore').decode('ascii')
    
    # Если текст в bytes
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8', errors='ignore')
        except UnicodeError:
            try:
                # Определяем кодировку
                import chardet
                encoding = chardet.detect(text)['encoding'] or 'utf-8'
                return text.decode(encoding, errors='ignore')
            except Exception:
                return text.decode('ascii', errors='ignore')
    
    # Для других типов данных
    return str(text)

def get_relevant_images(soup: BeautifulSoup, base_url: str):
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            full_url = urljoin(base_url, src)
            if not any(x in full_url.lower() for x in ['avatar', 'logo', 'banner', 'ad', 'icon']):
                images.append(full_url)
    return images

def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
        if title:
            return title
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text(strip=True)
    return "Без заголовка"