# app/handlers/index_court_decisions.py
import sys
import os
import time
import schedule
import threading
import logging
from datetime import datetime, timedelta

# Добавляем корень проекта в sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg2
from psycopg2.extras import DictCursor
from elasticsearch import Elasticsearch

from app.config import (
    ES_HOST, ES_USER, ES_PASS, 
    DB_CONFIG, ES_INDICES, 
    INDEXING_INTERVAL
)


# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    filename='indexing.log'
)

def get_es_client():
    """Создает клиент Elasticsearch"""
    try:
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3
        )
        return es
    except Exception as e:
        logging.error(f"Ошибка подключения к Elasticsearch: {e}")
        raise

def index_data(table_name):
    """Индексирует данные из указанной таблицы"""
    try:
        # Подключение к PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Подключение к Elasticsearch  
        es = get_es_client()
        
        # Выбираем индекс для таблицы
        index_name = ES_INDICES.get(table_name, f"{table_name}_index")
        
        # Получаем данные из таблицы
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        logging.info(f"Индексация {len(rows)} записей из таблицы {table_name}")
        
        # Индексируем каждую запись
        for row in rows:
            doc = dict(row)
            
            # Используем первичный ключ в качестве ID документа
            doc_id = doc.get('id') or doc.get(f'{table_name}_id')
            
            es.index(index=index_name, id=doc_id, document=doc)
        
        cursor.close()
        conn.close()
        
        logging.info(f"Индексация {table_name} завершена успешно")
        
    except Exception as e:
        logging.error(f"Ошибка индексации {table_name}: {e}")

def index_all_tables():
    """Индексирует все таблицы"""
    logging.info("Начало полной индексации")
    for table in ES_INDICES.keys():
        index_data(table)
    logging.info("Полная индексация завершена")

def schedule_indexing():
    """Планирование регулярной индексации"""
    # Индексация каждые 48 часов
    schedule.every(48).hours.do(index_all_tables)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduled_indexing():
    """Запуск потока для периодической индексации"""
    indexing_thread = threading.Thread(target=schedule_indexing)
    indexing_thread.start()
    
    # Первый запуск сразу после старта
    index_all_tables()

if __name__ == "__main__":
    start_scheduled_indexing()