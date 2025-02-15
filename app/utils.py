import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
