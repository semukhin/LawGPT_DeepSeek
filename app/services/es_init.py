#!/usr/bin/env python
"""
Скрипт для инициализации и индексации данных в Elasticsearch.
Поддерживает инкрементальную индексацию, асинхронную обработку,
мониторинг процесса и детальную обработку ошибок.
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta
import json
import argparse
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import asyncio
import traceback

# Глобальные переменные для конфигурации
ELASTICSEARCH_URL = os.getenv('ES_HOST', 'http://147.45.145.136:9200')
ES_HOST = ELASTICSEARCH_URL
ES_USER = os.getenv('ES_USER', None)
ES_PASS = os.getenv('ES_PASS', None)
DB_CONFIG = {
    "host": os.getenv('PG_DB_HOST', os.getenv('DB_HOST')),
    "port": int(os.getenv('PG_DB_PORT', os.getenv('DB_PORT', 5432))),
    "database": os.getenv('PG_DB_NAME', os.getenv('DB_NAME')),
    "user": os.getenv('PG_DB_USER', os.getenv('DB_USER')),
    "password": os.getenv('PG_DB_PASSWORD', os.getenv('DB_PASSWORD'))
}
INDEXING_INTERVAL = int(os.getenv('INDEXING_INTERVAL', '24'))


# Индексы
ES_INDICES = {
    'court_decisions': 'court_decisions_index',
    'court_reviews': 'court_reviews_index',
    'legal_articles': 'legal_articles_index',
    'ruslawod_chunks': 'ruslawod_chunks_index',
    'procedural_forms': 'procedural_forms_index'
}

# Проверка наличия необходимых модулей
try:
    import psycopg2
    from psycopg2.extras import DictCursor
    from elasticsearch import Elasticsearch, helpers
    from elasticsearch.exceptions import ConnectionError, RequestError
except ImportError as e:
    print(f"Ошибка импорта: {e}. Убедитесь, что все зависимости установлены.")
    sys.exit(1)

# Настройка логирования - перенаправляем в stdout для работы в Docker
logging.basicConfig(
    level=logging.INFO, # Changed to INFO
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('indexing.log')
    ]
)

# Глобальные переменные для отслеживания прогресса
indexing_stats = {
    "start_time": None,
    "end_time": None,
    "duration": None,
    "tables_processed": 0,
    "total_tables": 0,
    "documents_indexed": 0,
    "errors": [],
    "table_stats": {}
}

# Блокировка для обновления статистики
stats_lock = threading.Lock()


def wait_for_elasticsearch(max_retries=30, delay=5):
    """Ожидает доступности Elasticsearch с повторными попытками"""
    global ELASTICSEARCH_URL
    logging.info(f"Ожидание запуска Elasticsearch (до {max_retries} попыток с интервалом {delay} сек)...")

    # Проверяем, нужна ли авторизация
    auth = None
    if ES_USER and ES_PASS and ES_USER.lower() != 'none' and ES_PASS.lower() != 'none':
        auth = (ES_USER, ES_PASS)
        logging.info("Будет использована авторизация для подключения к Elasticsearch")
    else:
        logging.info("Подключение к Elasticsearch без авторизации")

    # Основной URL должен содержать схему
    main_url = "http://elasticsearch:9200"

    for attempt in range(max_retries):
        try:
            # Используем основной URL
            es_client = Elasticsearch(
                hosts=main_url,
                basic_auth=auth,
                verify_certs=False,
                request_timeout=30
            )
            info = es_client.info()
            logging.info(f"Успешное подключение к Elasticsearch {info['version']['number']} (попытка {attempt+1})")
            return es_client
        except Exception as e:
            logging.warning(f"Попытка {attempt+1}/{max_retries}: не удалось подключиться к {main_url}: {e}")

            # Попробуем альтернативные адреса, если основной не работает
            if attempt == 5:
                alt_urls = [
                    "http://127.0.0.1:9200",
                    "http://172.28.0.2:9200",
                    "http://elasticsearch:9200"  # Повторяем основной URL
                ]
                for alt_url in alt_urls:
                    try:
                        logging.info(f"Пробуем альтернативный URL: {alt_url}")
                        es_alt = Elasticsearch(
                            hosts=alt_url,
                            basic_auth=auth,
                            request_timeout=5,
                            verify_certs=False
                        )
                        if es_alt.ping():
                            logging.info(f"Успешное подключение к альтернативному URL {alt_url}")
                            ELASTICSEARCH_URL = alt_url
                            return es_alt
                    except Exception as alt_e:
                        logging.warning(f"Альтернативный URL {alt_url} недоступен: {alt_e}")

            time.sleep(delay)

    raise ConnectionError(f"Не удалось подключиться к Elasticsearch после {max_retries} попыток")


# Определение маппингов для индексов в соответствии с фактической структурой БД
MAPPINGS = {
    "ruslawod_chunks_index": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "simple_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "text_chunk": {"type": "text", "analyzer": "simple_analyzer"},
                # Дополнительные поля для поддержки совместимости с es_law_search.py
                "text": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "text_chunk"},
                "content": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "text_chunk"},
                "full_text": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "text_chunk"},
                "indexed_at": {"type": "date"}
            }
        }
    },
    "court_decisions_index": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "simple_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "case_number": {"type": "keyword"},
                "court_name": {"type": "text", "analyzer": "simple_analyzer"},
                "vidpr": {"type": "keyword"},
                "etapd": {"type": "keyword"},
                "result": {"type": "text", "analyzer": "simple_analyzer"},
                "date": {"type": "date"},
                "vid_dokumenta": {"type": "keyword"},
                "instance": {"type": "keyword"},
                "region": {"type": "keyword"},
                "judges": {"type": "text", "analyzer": "simple_analyzer"},
                "claimant": {"type": "text", "analyzer": "simple_analyzer",
                             "fields": {"keyword": {"type": "keyword"}}},
                "defendant": {"type": "text", "analyzer": "simple_analyzer",
                              "fields": {"keyword": {"type": "keyword"}}},
                "subject": {"type": "text", "analyzer": "simple_analyzer"},
                "arguments": {"type": "text", "analyzer": "simple_analyzer"},
                "conclusion": {"type": "text", "analyzer": "simple_analyzer"},
                "full_text": {"type": "text", "analyzer": "simple_analyzer"},
                "laws": {"type": "text", "analyzer": "simple_analyzer"},
                "amount": {"type": "float"},
                # Поля для обратной совместимости
                "decision_date": {"type": "date", "copy_to": "date"},
                "indexed_at": {"type": "date"}
            }
        }
    },
    "court_reviews_index": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "simple_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "title": {"type": "text", "analyzer": "simple_analyzer"},
                "subject": {"type": "text", "analyzer": "simple_analyzer"},
                "conclusion": {"type": "text", "analyzer": "simple_analyzer"},
                "referenced_cases": {"type": "keyword"},
                "full_text": {"type": "text", "analyzer": "simple_analyzer"},
                # Поля для обратной совместимости
                "content": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "full_text"},
                "text": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "full_text"},
                "indexed_at": {"type": "date"}
            }
        }
    },
    "legal_articles_index": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "simple_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "title": {"type": "text", "analyzer": "simple_analyzer"},
                "author": {"type": "keyword"},
                "publication_date": {"type": "date"},
                "source": {"type": "keyword"},
                "subject": {"type": "text", "analyzer": "simple_analyzer"},
                "summary": {"type": "text", "analyzer": "simple_analyzer"},
                "full_text": {"type": "text", "analyzer": "simple_analyzer"},
                # Поля для обратной совместимости
                "content": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "full_text"},
                "text": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "full_text"},
                "body": {"type": "text", "analyzer": "simple_analyzer", "copy_to": "full_text"},
                "indexed_at": {"type": "date"}
            }
        }
    },

    "procedural_forms_index": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index.mapping.total_fields.limit": 5000,  # Увеличенный лимит полей
            "analysis": {
                "analyzer": {
                    "russian_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "russian_stop", "russian_stemmer"]
                    },
                    "simple_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase"]
                    }
                },
                "filter": {
                    "russian_stop": {
                        "type": "stop",
                        "stopwords": "_russian_"
                    },
                    "russian_stemmer": {
                        "type": "stemmer",
                        "language": "russian"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "russian_analyzer", 
                        "fields": {"keyword": {"type": "keyword"}}},
                "doc_type": {"type": "keyword"},
                "court_type": {"type": "keyword"},
                "target_court": {"type": "text", "analyzer": "simple_analyzer"},
                "jurisdiction": {"type": "keyword"},
                "category": {"type": "keyword"},
                "subcategory": {"type": "keyword"},
                "applicant_type": {"type": "keyword"},
                "respondent_type": {"type": "keyword"},
                "third_parties": {"type": "keyword"},
                "stage": {"type": "keyword"},
                "subject_matter": {"type": "text", "analyzer": "russian_analyzer"},
                "keywords": {"type": "keyword"},
                "legal_basis": {"type": "keyword"},
                "full_text": {"type": "text", "analyzer": "russian_analyzer"},
                "template_variables": {
                    "type": "object",
                    "enabled": False  # Отключаем строгое маппинг для этого поля
                },
                "source_file": {"type": "keyword"},
                "creation_date": {"type": "date"},
                "last_updated": {"type": "date"},
                "content": {"type": "text", "analyzer": "russian_analyzer", "copy_to": "full_text"},
                "text": {"type": "text", "analyzer": "russian_analyzer", "copy_to": "full_text"},
                "indexed_at": {"type": "date"}
            }
        }
    }
}

def update_stats(table=None, documents=0, error=None):
    """Обновляет статистику индексации"""
    with stats_lock:
        if table:
            if table not in indexing_stats["table_stats"]:
                indexing_stats["table_stats"][table] = {
                    "documents": 0,
                    "start_time": datetime.now(),
                    "end_time": None,
                    "status": "processing"
                }

            indexing_stats["table_stats"][table]["documents"] += documents

            if documents > 0:
                indexing_stats["documents_indexed"] += documents

            if error:
                if "errors" not in indexing_stats["table_stats"][table]:
                    indexing_stats["table_stats"][table]["errors"] = []
                indexing_stats["table_stats"][table]["errors"].append(str(error))
                indexing_stats["errors"].append({"table": table, "error": str(error)})
                indexing_stats["table_stats"][table]["status"] = "error"

            if documents < 0:  # Сигнал о завершении индексации таблицы
                indexing_stats["tables_processed"] += 1
                indexing_stats["table_stats"][table]["end_time"] = datetime.now()
                indexing_stats["table_stats"][table]["status"] = "completed"

def get_es_client():
    """Создает клиент Elasticsearch"""
    try:
        return wait_for_elasticsearch()
    except Exception as e:
        logging.error(f"Ошибка подключения к Elasticsearch: {e}")
        raise


def check_es_connection():
    """Проверяет подключение к Elasticsearch"""
    try:
        es = get_es_client()
        info = es.info()
        logging.info(f"Успешное подключение к Elasticsearch {info['version']['number']}")
        return True
    except Exception as e:
        logging.error(f"Ошибка при проверке подключения к Elasticsearch: {e}")
        return False


def get_db_connection():
    """Создает подключение к PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', '82.97.242.92'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ruslaw_db'),
            user=os.getenv('DB_USER', 'gen_user'),
            password=os.getenv('DB_PASSWORD', 'P?!ri#ag5%G1Si')
        )
        return conn
    except Exception as e:
        logging.error(f"Ошибка подключения к PostgreSQL: {e}")
        raise


def setup_es_index(es, index_name):
    """Создает или обновляет индекс в Elasticsearch"""
    try:
        # Проверяем существование индекса
        if not es.indices.exists(index=index_name):
            # Получаем маппинг из словаря MAPPINGS или используем дефолтный
            if index_name in MAPPINGS:
                index_body = MAPPINGS[index_name]
                logging.info(f"Используется предопределенный маппинг для индекса {index_name}")
            else:
                # Используем минимальный маппинг
                index_body = {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "simple_analyzer": {
                                    "tokenizer": "standard",
                                    "filter": ["lowercase"]
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "text": {"type": "text", "analyzer": "simple_analyzer"},
                            "content": {"type": "text", "analyzer": "simple_analyzer"},
                            "full_text": {"type": "text", "analyzer": "simple_analyzer"},
                            "indexed_at": {"type": "date"}
                        }
                    }
                }
                logging.info(f"Используется стандартный маппинг для индекса {index_name}")

            # Создаем индекс
            es.indices.create(index=index_name, body=index_body)
            logging.info(f"Создан индекс {index_name}")
        else:
            logging.info(f"Индекс {index_name} уже существует")

            # Обновляем маппинг для существующего индекса, если это court_decisions_index
            if index_name == 'court_decisions_index':
                try:
                    # Обновляем поля для поддержки умного поиска
                    mapping_update = {
                        "properties": {
                            "case_number": {
                                "type": "keyword"
                            },
                            "defendant": {
                                "type": "text",
                                "analyzer": "simple_analyzer",
                                "fields": {
                                    "keyword": { "type": "keyword" }
                                }
                            },
                            "claimant": {
                                "type": "text",
                                "analyzer": "simple_analyzer",
                                "fields": {
                                    "keyword": { "type": "keyword" }
                                }
                            }
                        }
                    }

                    es.indices.put_mapping(
                        index=index_name,
                        body=mapping_update
                    )
                    logging.info(f"Обновлен маппинг для индекса {index_name} для поддержки умного поиска")
                except Exception as e:
                    logging.warning(f"Не удалось обновить маппинг для индекса {index_name}: {e}")

    except Exception as e:
        logging.error(f"Ошибка при создании/проверке индекса {index_name}: {e}")
        raise

def get_last_indexed_time(es, index_name, id_field="id"):
    """Получает время последней индексации документов"""
    try:
        # Проверяем существование индекса
        if not es.indices.exists(index=index_name):
            return None

        # Запрос для получения времени последней индексации
        query = {
            "size": 1,
            "sort": [{"indexed_at": {"order": "desc"}}],
            "query": {"match_all": {}}
        }

        result = es.search(index=index_name, body=query)

        if result["hits"]["total"]["value"] > 0:
            # Получаем время последней индексации
            last_indexed = result["hits"]["hits"][0]["_source"].get("indexed_at")
            if last_indexed:
                return datetime.fromisoformat(last_indexed.replace('Z', '+00:00'))

        return None
    except Exception as e:
        logging.error(f"Ошибка при получении времени последней индексации для {index_name}: {e}")
        return None

def get_table_schema(conn, table_name):
    """Получает схему таблицы из базы данных"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
            """, (table_name,))

            columns = {row[0]: row[1] for row in cursor.fetchall()}
            return columns
    except Exception as e:
        logging.error(f"Ошибка при получении схемы таблицы {table_name}: {e}")
        raise

def index_table_data(es, conn, table_name, index_name, batch_size=1000, id_field="id", last_indexed=None):
    """Индексирует данные из таблицы в Elasticsearch"""
    try:
        # Получаем схему таблицы
        schema = get_table_schema(conn, table_name)

        # Проверяем наличие поля id или table_id
        if id_field not in schema:
            # Пытаемся найти первичный ключ
            alternative_id = f"{table_name}_id"
            if alternative_id in schema:
                id_field = alternative_id
            else:
                logging.error(f"В таблице {table_name} не найдено поле {id_field} или {alternative_id}")
                update_stats(table=table_name, error=f"Не найдено поле ID: {id_field} или {alternative_id}")
                return 0

        # Формируем SQL запрос с учетом последней индексации
        base_query = f"SELECT * FROM {table_name}"
        params = []

        # Проверяем поля для инкрементальной индексации
        if last_indexed:
            if table_name == 'procedural_forms' and 'last_updated' in schema:
                base_query += " WHERE last_updated > %s"
                params.append(last_indexed)
            elif "updated_at" in schema:
                base_query += " WHERE updated_at > %s"
                params.append(last_indexed)
            elif "created_at" in schema:
                base_query += " WHERE created_at > %s"
                params.append(last_indexed)

        # Добавляем пагинацию для обработки данных батчами
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS count_query"

        with conn.cursor() as cursor:
            cursor.execute(count_query, params)
            total_rows = cursor.fetchone()[0]

            if total_rows == 0:
                logging.info(f"В таблице {table_name} нет новых данных для индексации")
                update_stats(table=table_name, documents=-1)  # Сигнал о завершении
                return 0

            logging.info(f"Начало индексации {total_rows} записей из таблицы {table_name}")

            # Обрабатываем данные батчами
            offset = 0
            total_indexed = 0

            while offset < total_rows:
                batch_query = f"{base_query} LIMIT {batch_size} OFFSET {offset}"
                cursor.execute(batch_query, params)

                rows = cursor.fetchall()
                if not rows:
                    break

                # Подготавливаем батч для bulk индексации
                batch_actions = []
                column_names = [desc[0] for desc in cursor.description]

                for row in rows:
                    doc = dict(zip(column_names, row))

                    # Добавляем метку времени индексации
                    doc['indexed_at'] = datetime.now().isoformat()

                    # Специальная обработка для разных таблиц
                    if table_name == 'ruslawod_chunks' and 'text_chunk' in doc:
                        # Скопируем text_chunk в поля, которые ищет es_law_search.py
                        doc['text'] = doc['text_chunk']
                        doc['content'] = doc['text_chunk']
                        doc['full_text'] = doc['text_chunk']

                    # Преобразуем дату для elasticsearch
                    if table_name == 'court_decisions' and 'date' in doc and doc['date']:
                        doc['decision_date'] = doc['date']

                    if table_name == 'legal_articles' and 'summary' in doc:
                        doc['content'] = doc['summary']

                    # Специальная обработка для procedural_forms
                    if table_name == 'procedural_forms':
                        # Копируем full_text в content и text для обратной совместимости
                        if 'full_text' in doc and doc['full_text']:
                            doc['content'] = doc['full_text']
                            doc['text'] = doc['full_text']

                        # Преобразуем массивы PostgreSQL в списки Python
                        for array_field in ['third_parties', 'keywords', 'legal_basis']:
                            if array_field in doc and doc[array_field] is not None:
                                # Если поле уже является списком, оставляем как есть
                                if not isinstance(doc[array_field], list):
                                    # Преобразуем строку массива PostgreSQL в список Python
                                    try:
                                        # Для массивов в формате {item1,item2,...}
                                        if isinstance(doc[array_field], str) and doc[array_field].startswith('{') and doc[array_field].endswith('}'):
                                            doc[array_field] = doc[array_field][1:-1].split(',') if doc[array_field] != '{}' else []
                                    except Exception as e:
                                        logging.warning(f"Ошибка при преобразовании массива {array_field} в таблице {table_name}: {e}")

                        # Обработка поля template_variables
                        if 'template_variables' in doc:
                            if doc['template_variables'] is None:
                                # Если template_variables равно None, заменяем его пустым объектом
                                doc['template_variables'] = {}
                            elif isinstance(doc['template_variables'], str):
                                try:
                                    doc['template_variables'] = json.loads(doc['template_variables'])
                                except Exception as e:
                                    logging.warning(f"Ошибка при преобразовании JSONB template_variables в таблице {table_name}: {e}")
                                    doc['template_variables'] = {}

                    # Обработка массива для referenced_cases
                    if table_name == 'court_reviews' and 'referenced_cases' in doc and isinstance(doc['referenced_cases'], list):
                        doc['referenced_cases'] = ','.join(doc['referenced_cases'])

                    # Преобразуем datetime объекты в строки
                    for key, value in doc.items():
                        if isinstance(value, datetime):
                            doc[key] = value.isoformat()

                    # Добавляем операцию в батч
                    doc_id = str(doc.get(id_field))
                    action = {
                        "_index": index_name,
                        "_id": doc_id,
                        "_source": doc
                    }
                    batch_actions.append(action)

                # Выполняем bulk индексацию
                if batch_actions:
                    success, failed = helpers.bulk(
                        es,
                        batch_actions,
                        stats_only=True,
                        raise_on_error=False
                    )

                    if failed:
                        logging.warning(f"При индексации таблицы {table_name} не удалось индексировать {failed} документов")
                        update_stats(table=table_name, error=f"Не удалось индексировать {failed} документов")

                    total_indexed += success
                    update_stats(table=table_name, documents=success)

                    logging.info(f"Индексировано {total_indexed}/{total_rows} записей из таблицы {table_name}")

                offset += batch_size

            update_stats(table=table_name, documents=-1)  # Сигнал о завершении
            logging.info(f"Завершена индексация таблицы {table_name}, всего индексировано {total_indexed} записей")
            return total_indexed
    except Exception as e:
        error_stack = traceback.format_exc()
        logging.error(f"Ошибка при индексации таблицы {table_name}: {e}\n{error_stack}")
        update_stats(table=table_name, error=str(e))
        return 0

def index_table_async(table_name, index_name, batch_size=1000):
    """Асинхронная индексация одной таблицы"""
    try:
        es = get_es_client()
        conn = get_db_connection()

        try:
            # Создаем или проверяем индекс
            setup_es_index(es, index_name)

            # Получаем время последней индексации
            last_indexed = get_last_indexed_time(es, index_name)

            # Логируем информацию о последней индексации
            if last_indexed:
                logging.info(f"Последняя индексация таблицы {table_name}: {last_indexed}")
            else:
                logging.info(f"Первая индексация таблицы {table_name}")

            # Индексируем данные
            indexed_count = index_table_data(
                es, conn, table_name, index_name,
                batch_size=batch_size,
                last_indexed=last_indexed
            )

            return indexed_count
        finally:
            conn.close()
    except Exception as e:
        error_stack = traceback.format_exc()
        logging.error(f"Ошибка при индексации таблицы {table_name}: {e}\n{error_stack}")
        update_stats(table=table_name, error=str(e))
        return 0

async def index_all_tables_async(batch_size=1000, max_workers=4):
    """Индексирует все таблицы асинхронно используя пул потоков"""
    # Проверяем подключение к Elasticsearch
    if not check_es_connection():
        logging.error("Не удалось подключиться к Elasticsearch, индексация отменена")
        return False

    # Инициализируем статистику
    global indexing_stats
    indexing_stats = {
        "start_time": datetime.now(),
        "tables_processed": 0,
        "total_tables": len(ES_INDICES),
        "documents_indexed": 0,
        "errors": [],
        "table_stats": {}
    }

    logging.info(f"Начало индексации {len(ES_INDICES)} таблиц")

    # Создаем пул потоков
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем задачи индексации в пуле потоков
        futures = {}
        for table_name, index_name in ES_INDICES.items():
            future = executor.submit(index_table_async, table_name, index_name, batch_size)
            futures[future] = table_name

        # Ожидаем завершения всех задач
        for future in futures:
            table_name = futures[future]
            try:
                indexed_count = future.result()
                logging.info(f"Индексация таблицы {table_name} завершена, индексировано {indexed_count} записей")
            except Exception as e:
                logging.error(f"Ошибка при индексации таблицы {table_name}: {e}")

    # Записываем общую статистику
    indexing_stats["end_time"] = datetime.now()
    indexing_stats["duration"] = (indexing_stats["end_time"] - indexing_stats["start_time"]).total_seconds()

    logging.info(f"Индексация всех таблиц завершена за {indexing_stats['duration']:.2f} секунд")
    logging.info(f"Всего индексировано {indexing_stats['documents_indexed']} документов")

    if indexing_stats["errors"]:
        logging.warning(f"При индексации возникло {len(indexing_stats['errors'])} ошибок")
        for error in indexing_stats["errors"]:
            logging.warning(f"Ошибка в таблице {error['table']}: {error['error']}")

    # Сохраняем статистику в файл
    stats_file = os.path.join(os.path.dirname(__file__), "indexing_stats.json")
    with open(stats_file, "w") as f:
        json.dump(indexing_stats, f, default=str, indent=2)

    logging.info(f"Статистика индексации сохранена в {stats_file}")

    return len(indexing_stats["errors"]) == 0

async def schedule_indexing(interval_hours=None):
    """Планирование регулярной индексации"""
    if interval_hours is None:
        interval_hours = INDEXING_INTERVAL

    logging.info(f"Запущено планирование индексации с интервалом {interval_hours} часов")

    while True:
        logging.info("Запуск индексации всех таблиц")
        success = await index_all_tables_async()

        if success:
            logging.info(f"Индексация успешно завершена. Следующая индексация через {interval_hours} часов")
        else:
            logging.error("Индексация завершена с ошибками. Проверьте логи")

        # Ждем указанное время перед следующей индексацией
        next_run = datetime.now() + timedelta(hours=interval_hours)
        logging.info(f"Следующая индексация: {next_run}")
        await asyncio.sleep(interval_hours * 3600)

def get_indexing_status():
    """Получение статуса индексации"""
    return {
        "status": "initialized",
        "message": "Elasticsearch готов к работе"
    }

async def init_elasticsearch_async():
    """Асинхронная инициализация Elasticsearch"""
    try:
        # Здесь будет код инициализации Elasticsearch
        return True
    except Exception as e:
        logging.error(f"Ошибка инициализации Elasticsearch: {str(e)}")
        return False

def start_scheduled_indexing():
    """Запуск потока для периодической индексации"""
    logging.info("Запуск сервиса периодической индексации")

    # Создаем цикл событий для асинхронных функций
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Запускаем индексацию сразу при старте
        loop.run_until_complete(index_all_tables_async())

        # Запускаем периодическую индексацию
        loop.run_until_complete(schedule_indexing())
    except KeyboardInterrupt:
        logging.info("Сервис индексации остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка в сервисе индексации: {e}")
    finally:
        loop.close()

def create_indices():
    """Создает все необходимые индексы в Elasticsearch"""
    try:
        es = get_es_client()

        # Создаем индексы для всех определенных маппингов
        for index_name in MAPPINGS:
            setup_es_index(es, index_name)

        logging.info("Все необходимые индексы проверены или созданы")
        return True

    except Exception as e:
        logging.error(f"Ошибка при создании индексов: {e}")
        return False

def update_mappings():
    """Обновляет маппинги для всех индексов с учетом изменений для умного поиска"""
    try:
        es = get_es_client()

        # Обновляем маппинг для индекса court_decisions_index
        court_decisions_index = ES_INDICES.get("court_decisions", "court_decisions_index")

        if es.indices.exists(index=court_decisions_index):
            # Определяем обновление маппинга
            mapping_update = {
                "properties": {
                    "case_number": {
                        "type": "keyword"
                    },
                    "defendant": {
                        "type": "text",
                        "analyzer": "simple_analyzer",
                        "fields": {
                            "keyword": { "type": "keyword" }
                        }
                    },
                    "claimant": {
                        "type": "text",
                        "analyzer": "simple_analyzer",
                        "fields": {
                            "keyword": { "type": "keyword" }
                        }
                    },
                    "doc_id": { "type": "keyword" },
                    "chunk_id": { "type": "integer" }
                }
            }

            try:
                es.indices.put_mapping(
                    index=court_decisions_index,
                    body=mapping_update
                )
                logging.info(f"✅ Маппинг для индекса {court_decisions_index} успешно обновлен.")
            except Exception as e:
                logging.error(f"❌ Ошибка при обновлении маппинга для индекса {court_decisions_index}: {str(e)}")

        # Обновляем маппинг для индекса procedural_forms_index
        procedural_forms_index = ES_INDICES.get("procedural_forms", "procedural_forms_index")

        if es.indices.exists(index=procedural_forms_index):
            # Определяем обновление маппинга
            mapping_update = {
                "properties": {
                    "title": {
                        "type": "text",
                        "analyzer": "russian_analyzer",
                        "fields": {
                            "keyword": { "type": "keyword" }
                        }
                    },
                    "doc_type": { "type": "keyword" },
                    "category": { "type": "keyword" },
                    "subcategory": { "type": "keyword" },
                    "doc_id": { "type": "keyword" },
                    "full_text": { 
                        "type": "text", 
                        "analyzer": "russian_analyzer"
                    }
                }
            }

            try:
                es.indices.put_mapping(
                    index=procedural_forms_index,
                    body=mapping_update
                )
                logging.info(f"✅ Маппинг для индекса {procedural_forms_index} успешно обновлен.")
            except Exception as e:
                logging.error(f"❌ Ошибка при обновлении маппинга для индекса {procedural_forms_index}: {str(e)}")

        logging.info("✅ Все необходимые маппинги обновлены.")
        return True

    except Exception as e:
        logging.error(f"❌ Ошибка при обновлении маппингов: {str(e)}")
        return False

def parse_arguments():
    """Обработка аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Инструмент для индексации таблиц в Elasticsearch')

    parser.add_argument('--run-once', action='store_true',
                        help='Запустить индексацию один раз без планирования')

    parser.add_argument('--table', type=str,
                        help='Индексировать только указанную таблицу')

    parser.add_argument('--interval', type=int, default=INDEXING_INTERVAL,
                        help=f'Интервал индексации в часах (по умолчанию: {INDEXING_INTERVAL})')

    parser.add_argument('--batch-size', type=int, default=1000,
                        help='Размер батча для индексации (по умолчанию: 1000)')

    parser.add_argument('--max-workers', type=int, default=4,
                        help='Максимальное количество параллельных потоков (по умолчанию: 4)')

    parser.add_argument('--create-indices', action='store_true',
                        help='Только создать индексы без индексации данных')

    parser.add_argument('--update-mappings', action='store_true',
                        help='Обновить маппинги индексов для умного поиска')

    parser.add_argument('--status', action='store_true',
                        help='Получить статус последней индексации')

    return parser.parse_args()

async def main_async():
    """Основная асинхронная функция"""
    args = parse_arguments()

    logging.info("Запуск создания индексов...")
    connection_ok = check_es_connection()
    logging.info(f"Результат проверки подключения: {connection_ok}")
    if not connection_ok:
        logging.error("Не удалось подключиться к Elasticsearch, индексация отменена")
        return 1
    logging.info("Продолжаем выполнение...")

    # Если запрошен только статус
    if args.status:
        stats = get_indexing_status()
        if stats["start_time"]:
            print(f"Последняя индексация: {stats['start_time']}")
            print(f"Обработано таблиц: {stats['tables_processed']}/{stats['total_tables']}")
            print(f"Проиндексировано документов: {stats['documents_indexed']}")
            if stats["errors"]:
                print(f"Ошибки ({len(stats['errors'])}): ")
                for error in stats["errors"]:
                    print(f"  Таблица {error['table']}: {error['error']}")
        else:
            print("Индексация еще не запускалась")
        return 0

    # Если запрошено только создание индексов
    if args.create_indices:
        success = create_indices()
        return 0 if success else 1

    # Если запрошено только обновление маппингов
    if args.update_mappings:
        success = update_mappings()
        return 0 if success else 1

    try:
        conn = get_db_connection()
        conn.close()
    except Exception as e:
        logging.error(f"Не удалось подключиться к PostgreSQL: {e}")
        return 1

    # Если указана конкретная таблица, индексируем только её
    if args.table:
        if args.table not in ES_INDICES:
            logging.error(f"Таблица {args.table} не найдена в конфигурации индексов")
            return 1

        logging.info(f"Запуск индексации только для таблицы {args.table}")

        # Инициализируем статистику
        global indexing_stats
        indexing_stats = {
            "start_time": datetime.now(),
            "tables_processed": 0,
            "total_tables": 1,
            "documents_indexed": 0,
            "errors": [],
            "table_stats": {}
        }

        indexed_count = await asyncio.to_thread(
            index_table_async,
            args.table,
            ES_INDICES[args.table],
            args.batch_size
        )

        logging.info(f"Индексация таблицы {args.table} завершена, индексировано {indexed_count} документов")
        return 0

    # Запускаем полную индексацию
    if args.run_once:
        # Запускаем разовую индексацию
        logging.info("Запуск разовой индексации всех таблиц")
        await index_all_tables_async(
            batch_size=args.batch_size,
            max_workers=args.max_workers
        )
        return 0
    else:
        # Запускаем периодическую индексацию
        logging.info(f"Запуск периодической индексации с интервалом {args.interval} часов")
        await schedule_indexing(args.interval)
        return 0

if __name__ == "__main__":
    try:
        # Запускаем асинхронную главную функцию
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logging.info("Программа остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Необработанная ошибка: {e}")