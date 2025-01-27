import requests

# Базовый URL вашего API
BASE_URL = "http://127.0.0.1:8000"

# Токен для авторизации
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuaWtpdGFzZW11a2hpbi5uc0BnbWFpbC5jb20iLCJ1c2VyX2lkIjozOSwiZXhwIjoxNzM4NTI4MTkyfQ.Ll95G97hSQZP694Glq1_lyfPn_Xwc2-PBmcpVQHbFII"

# ID треда для тестирования
THREAD_ID = "thread_4666bde0f25d4ee1a6da54b1ce94e7d0"

# Заголовки для авторизации
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_upload_file():
    """Тестирует загрузку файла."""
    url = f"{BASE_URL}/api/upload_file"
    try:
        files = {"file": open("test.docx", "rb")}  # Укажите путь к тестовому файлу
        response = requests.post(url, headers={"Authorization": f"Bearer {TOKEN}"}, files=files)
        response.raise_for_status()  # Проверка на ошибки
        print("Upload File Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Upload File Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_remove_file():
    """Тестирует удаление файла."""
    url = f"{BASE_URL}/api/remove_file"
    try:
        response = requests.post(url, headers=HEADERS)
        response.raise_for_status()
        print("Remove File Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Remove File Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_new_chat():
    """Тестирует создание нового чата."""
    url = f"{BASE_URL}/api/new_chat"
    try:
        response = requests.post(url, headers=HEADERS)
        response.raise_for_status()
        print("New Chat Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("New Chat Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_send_message():
    """Тестирует отправку сообщения в тред."""
    url = f"{BASE_URL}/api/chat/{THREAD_ID}/send_message?token={TOKEN}"
    try:
        data = {"message": "Как физлицу вернуть товар продавцу по причине брака?"}
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=data)
        response.raise_for_status()
        print("Send Message Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Send Message Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_get_thread_messages():
    """Тестирует получение истории сообщений для треда."""
    url = f"{BASE_URL}/api/thread/{THREAD_ID}/messages"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        print("Get Thread Messages Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Get Thread Messages Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_get_threads():
    """Тестирует получение списка тредов."""
    url = f"{BASE_URL}/api/threads"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        print("Get Threads Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Get Threads Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

def test_download_file():
    """Тестирует скачивание файла."""
    filename = "test.docx"  # Укажите имя файла, который был загружен
    url = f"{BASE_URL}/download/{filename}"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        with open(filename, "wb") as file:
            file.write(response.content)
        print(f"File {filename} downloaded successfully.")
    except requests.exceptions.RequestException as e:
        print("Download File Error:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response Content:", e.response.json())  # Вывод деталей ошибки

if __name__ == "__main__":
    # Запуск всех тестов
    test_upload_file()
    test_remove_file()
    test_upload_file()  # Загружаем файл заново
    test_new_chat()
    test_send_message()
    test_get_thread_messages()
    test_get_threads()
    test_download_file()