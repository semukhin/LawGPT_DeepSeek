from elasticsearch import Elasticsearch
import logging
from app.config import ES_HOST, ES_USER, ES_PASS, ES_INDICES, DB_CONFIG
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import threading
import queue
import concurrent.futures

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

# Глобальный словарь для хранения статуса индексации
indexing_status = {
    "is_running": False,
    "total_tables": 0,
    "completed_tables": 0,
    "current_progress": {},
    "errors": []
}

# Блокировка для безопасного обновления статуса
status_lock = threading.Lock()

def update_indexing_status(table_name=None, progress=None, error=None):
    """Обновляет статус индексации"""
    with status_lock:
        if error:
            indexing_status["errors"].append({"table": table_name, "error": str(error)})
        if progress is not None:
            indexing_status["current_progress"][table_name] = progress
        if table_name and progress == 100:
            indexing_status["completed_tables"] += 1

def get_indexing_status():
    """Возвращает текущий статус индексации"""
    with status_lock:
        return dict(indexing_status)

# Определение маппингов для индексов
MAPPINGS = {
    "ruslawod_chunks_index": {
        "mappings": {
            "properties": {
                "text": {"type": "text", "analyzer": "russian"},
                "metadata": {"type": "object"},
                "document_id": {"type": "keyword"},
                "chunk_number": {"type": "integer"},
                "created_at": {"type": "date"}
            }
        }
    },
    "court_decisions_index": {
        "mappings": {
            "properties": {
                "case_number": {"type": "keyword"},
                "court_name": {"type": "text", "analyzer": "russian"},
                "decision_date": {"type": "date"},
                "decision_text": {"type": "text", "analyzer": "russian"},
                "category": {"type": "keyword"},
                "judge": {"type": "text", "analyzer": "russian"},
                "parties": {"type": "text", "analyzer": "russian"},
                "created_at": {"type": "date"}
            }
        }
    },
    "court_reviews_index": {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "russian"},
                "content": {"type": "text", "analyzer": "russian"},
                "author": {"type": "keyword"},
                "publication_date": {"type": "date"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    },
    "legal_articles_index": {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "russian"},
                "content": {"type": "text", "analyzer": "russian"},
                "author": {"type": "keyword"},
                "publication_date": {"type": "date"},
                "category": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }
}

def get_es_client():
    """Создает и возвращает клиент Elasticsearch"""
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

def create_index(es, index_name, mapping):
    """Создает индекс с указанным маппингом"""
    try:
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=mapping)
            logging.info(f"Создан индекс {index_name}")
        else:
            logging.info(f"Индекс {index_name} уже существует")
    except Exception as e:
        logging.error(f"Ошибка при создании индекса {index_name}: {e}")
        raise

def get_db_connection():
    """Создает подключение к PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logging.error(f"Ошибка подключения к PostgreSQL: {e}")
        raise

def index_table_data_batch(es, conn, table_name, index_name, batch_size=1000):
    """Индексирует данные из таблицы PostgreSQL в Elasticsearch батчами"""
    try:
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Получаем общее количество записей
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]
        
        if total_rows == 0:
            logging.info(f"Таблица {table_name} пуста")
            update_indexing_status(table_name, 100)
            return
            
        logging.info(f"Начало индексации {total_rows} записей из таблицы {table_name}")
        
        # Обрабатываем данные батчами
        offset = 0
        while offset < total_rows:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
            rows = cursor.fetchall()
            
            if not rows:
                break
                
            # Подготавливаем батч для bulk индексации
            bulk_data = []
            for row in rows:
                doc = dict(row)
                doc['indexed_at'] = datetime.now().isoformat()
                doc_id = str(doc.get('id') or doc.get(f'{table_name}_id'))
                
                # Добавляем операцию индексации в батч
                bulk_data.extend([
                    {"index": {"_index": index_name, "_id": doc_id}},
                    doc
                ])
            
            # Выполняем bulk индексацию
            if bulk_data:
                es.bulk(operations=bulk_data)
            
            offset += batch_size
            progress = min(100, int(offset * 100 / total_rows))
            update_indexing_status(table_name, progress)
            logging.info(f"Проиндексировано {min(offset, total_rows)}/{total_rows} записей из таблицы {table_name}")
        
        update_indexing_status(table_name, 100)
        logging.info(f"Завершена индексация таблицы {table_name}")
        
    except Exception as e:
        logging.error(f"Ошибка при индексации таблицы {table_name}: {e}")
        update_indexing_status(table_name=table_name, error=e)
        raise
    finally:
        cursor.close()

def index_table_async(table_name, index_name):
    """Асинхронная индексация одной таблицы"""
    try:
        es = get_es_client()
        conn = get_db_connection()
        
        try:
            # Создаем индекс если не существует
            if not es.indices.exists(index=index_name):
                es.indices.create(index=index_name, body=MAPPINGS[index_name])
                logging.info(f"Создан индекс {index_name}")
            
            # Индексируем данные
            index_table_data_batch(es, conn, table_name, index_name)
            
        finally:
            conn.close()
            
    except Exception as e:
        logging.error(f"Ошибка при индексации таблицы {table_name}: {e}")

def init_elasticsearch_async():
    """Инициализирует индексы Elasticsearch и запускает асинхронную индексацию"""
    try:
        # Проверяем подключение к Elasticsearch
        es = get_es_client()
        if not es.ping():
            raise ConnectionError("Не удалось подключиться к Elasticsearch")
            
        # Проверяем подключение к PostgreSQL
        conn = get_db_connection()
        conn.close()
        
        # Инициализируем статус
        with status_lock:
            indexing_status["is_running"] = True
            indexing_status["total_tables"] = len(ES_INDICES)
            indexing_status["completed_tables"] = 0
            indexing_status["current_progress"] = {}
            indexing_status["errors"] = []
        
        # Создаем и запускаем поток для индексации
        def indexing_thread():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    for table_name, index_name in ES_INDICES.items():
                        future = executor.submit(index_table_async, table_name, index_name)
                        futures.append(future)
                    
                    # Ждем завершения всех задач
                    concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_EXCEPTION)
                    logging.info("Индексация всех таблиц завершена")
            finally:
                with status_lock:
                    indexing_status["is_running"] = False
        
        # Запускаем индексацию в отдельном потоке
        thread = threading.Thread(target=indexing_thread)
        thread.daemon = True
        thread.start()
        
        logging.info("Запущена асинхронная индексация всех таблиц")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при инициализации Elasticsearch: {e}")
        return False

if __name__ == "__main__":
    init_elasticsearch_async()
    # Держим главный поток живым для демонстрации
    import time
    time.sleep(3600) 