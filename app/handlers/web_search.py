import requests
from bs4 import BeautifulSoup
from app.utils import get_url_content
import sys
import asyncio
from app.config import MAIL_SETTINGS, DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, oauth2_scheme
from third_party.shandu.scraper import WebScraper


# Ваши ключи Google Custom Search
API_KEY = "AIzaSyAIEt6AC2rHfLb8W90R0Gp_lcFN3RnKQak"
CX = "31a742e3d78ce478c"  # Ваш Custom Search Engine ID



def google_search(query: str, logs: list) -> list:
    """
    Выполняет поиск по запросу через Google Custom Search API и возвращает список найденных веб-ссылок.
    
    Args:
        query (str): поисковый запрос.
        logs (list): список для логирования хода выполнения.
        
    Returns:
        list: Список URL, найденных по запросу.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CX,
        "q": query,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        links = [item.get("link") for item in items if item.get("link")]
        logs.append(f"Найдено {len(links)} ссылок по запросу '{query}'.")
        return links
    except Exception as e:
        logs.append(f"Ошибка при поиске в Google: {str(e)}")
        return []

async def search_and_scrape(query: str, logs: list) -> list:
    """
    Выполняет поиск в Google, получает список веб-ссылок и передаёт их в модуль скрейпера для извлечения содержимого страниц.
    
    Args:
        query (str): поисковый запрос.
        logs (list): список для логирования.
        
    Returns:
        list: Список объектов ScrapedContent, полученных после скрейпинга найденных страниц.
    """
    # Выполняем поиск и получаем ссылки
    links = google_search(query, logs)
    
    # Создаем экземпляр WebScraper из модуля shandu/scraper/
    scraper = WebScraper()
    
    # Асинхронно скрейпим все найденные ссылки
    scraped_results = await scraper.scrape_urls(links, dynamic=False)
    
    return scraped_results

if __name__ == "__main__":
    # Простой CLI для тестирования
    if len(sys.argv) < 2:
        print("Usage: python web_search.py 'your search query'")
        sys.exit(1)
    
    query = sys.argv[1]
    logs = []
    results = asyncio.run(search_and_scrape(query, logs))
    
    for res in results:
        if res.is_successful():
            print(f"URL: {res.url}\nTitle: {res.title}\nExtracted Text (first 200 chars):\n{res.text[:200]}\n{'-'*80}\n")
        else:
            print(f"Не удалось обработать {res.url}: {res.error}")
    
    print("\nЛоги выполнения:")
    for log in logs:
        print(log)
