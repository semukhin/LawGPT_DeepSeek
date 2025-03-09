import sys
import os

# Добавляем корень проекта в sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Теперь импортируем
try:
    from elasticsearch import Elasticsearch
except ImportError:
    import sys
    import subprocess
    
    # Устанавливаем пакет, если он отсутствует
    subprocess.check_call([sys.executable, "-m", "pip", "install", "elasticsearch==8.5.0"])
    from elasticsearch import Elasticsearch

from app.database import get_court_decisions  # Правильный путь импорта с префиксом app

ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "GIkb8BKzkXK7i2blnG2O"
ES_INDEX_NAME = "court_decisions_index"

def index_court_decisions():
    es = Elasticsearch([ES_HOST], basic_auth=(ES_USER, ES_PASS))
    court_decisions = get_court_decisions()  # Предполагается, что возвращает список словарей
    
    if not court_decisions:
        print("❌ Нет данных для индексации!")
        return

    for decision in court_decisions:
        print(f"📄 Индексация дела {decision['case_number']} в Elasticsearch...")
        response = es.index(index=ES_INDEX_NAME, document=decision)
        print(response)

if __name__ == "__main__":
    index_court_decisions()
