# app/handlers/es_law_search.py

import logging
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Параметры подключения к Elasticsearch
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "GIkb8BKzkXK7i2blnG2O"

# Индексы в Elasticsearch
ES_INDICES = {
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index",
    "legal_articles": "legal_articles_index",
    "ruslawod_chunks": "ruslawod_chunks_index"
}

def get_es_client():
    """
    Создает и возвращает клиент Elasticsearch.
    
    Returns:
        Elasticsearch: Клиент Elasticsearch
    """
    try:
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3,
            request_timeout=30
        )
        logger.info("✅ Успешное подключение к Elasticsearch")
        return es
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к Elasticsearch: {str(e)}")
        raise

def search_law_chunks(query: str, top_n: int = 7) -> List[str]:
    """
    Поиск в Elasticsearch по всем индексам.
    
    Args:
        query: Текст запроса
        top_n: Максимальное количество результатов
        
    Returns:
        List[str]: Список найденных фрагментов законодательства
    """
    try:
        logger.info(f"🔍 [ES] Начало поиска в Elasticsearch для запроса: '{query}'")
        es = get_es_client()
        
        results = []
        
        # Распределяем количество результатов между разными индексами
        court_decisions_limit = max(2, top_n // 4)
        court_reviews_limit = max(1, top_n // 4)
        legal_articles_limit = max(1, top_n // 4)
        ruslawod_chunks_limit = top_n - court_decisions_limit - court_reviews_limit - legal_articles_limit
        
        # 1. Поиск в индексе court_decisions (судебные решения)
        court_decision_results = search_court_decisions(es, query, court_decisions_limit)
        results.extend(court_decision_results)
        
        # 2. Поиск в индексе ruslawod_chunks (чанки законодательства)
        ruslawod_chunks_results = search_ruslawod_chunks(es, query, ruslawod_chunks_limit)
        results.extend(ruslawod_chunks_results)
        
        # 3. Поиск в индексе court_reviews (обзоры судебных решений)
        court_reviews_results = search_court_reviews(es, query, court_reviews_limit)
        results.extend(court_reviews_results)
        
        # 4. Поиск в индексе legal_articles (правовые статьи)
        legal_articles_results = search_legal_articles(es, query, legal_articles_limit)
        results.extend(legal_articles_results)
        
        logger.info(f"🔍 [ES] Найдено всего {len(results)} релевантных результатов.")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в Elasticsearch: {str(e)}")
        return []

def search_court_decisions(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе court_decisions (судебные решения).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("court_decisions", "court_decisions_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "case_number": query
                            }
                        },
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "case_number^5",
                                    "judges^3",
                                    "claimant^3",
                                    "defendant^3",
                                    "subject^2",
                                    "arguments",
                                    "conclusion",
                                    "full_text"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            case_number = source.get("case_number", "")
            subject = source.get("subject", "")
            judges = source.get("judges", "")
            claimant = source.get("claimant", "")
            defendant = source.get("defendant", "")
            full_text = source.get("full_text", "")
            
            highlights = hit.get("highlight", {}).get("full_text", [])
            highlight_text = "...\n".join(highlights)
            
            result = f"Судебное дело № {case_number}\n"
            result += f"Судьи: {judges}\nИстец: {claimant}\nОтветчик: {defendant}\nПредмет: {subject}\n"
            
            if highlights:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            result += f"Полный текст:\n{full_text[:2000]}..."
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} судебных решений")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе court_decisions: {str(e)}")
        return []

def search_ruslawod_chunks(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе ruslawod_chunks (чанки законодательства).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "text^3",
                        "content^3",
                        "full_text^2",
                        "law_name",
                        "section_name",
                        "article_name"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            law_name = source.get("law_name", "")
            section = source.get("section_name", source.get("section", ""))
            article = source.get("article_name", source.get("article", ""))
            content = source.get("content", source.get("text", source.get("full_text", "")))
            
            # Получаем дополнительные поля (если есть)
            document_id = source.get("document_id", "")
            chunk_id = source.get("chunk_id", "")
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["text", "content", "full_text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Законодательство: {law_name}\n"
            
            if section:
                result += f"Раздел: {section}\n"
            
            if article:
                result += f"Статья: {article}\n"
            
            if document_id and chunk_id:
                result += f"ID документа: {document_id}, ID фрагмента: {chunk_id}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Текст:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} фрагментов законодательства")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе ruslawod_chunks: {str(e)}")
        return []

def search_court_reviews(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе court_reviews (обзоры судебных решений).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("court_reviews", "court_reviews_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "content^3",
                        "description^2",
                        "text",
                        "full_text"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "title": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            title = source.get("title", "Обзор судебной практики")
            content = source.get("content", source.get("text", source.get("full_text", "")))
            author = source.get("author", "")
            publication_date = source.get("publication_date", source.get("date", ""))
            source_name = source.get("source", "")
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["title", "content", "text", "full_text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Обзор судебной практики: {title}\n"
            
            if author:
                result += f"Автор: {author}\n"
            
            if publication_date:
                result += f"Дата публикации: {publication_date}\n"
            
            if source_name:
                result += f"Источник: {source_name}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Содержание:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} обзоров судебной практики")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе court_reviews: {str(e)}")
        return []

def search_legal_articles(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе legal_articles (правовые статьи).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("legal_articles", "legal_articles_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "content^3",
                        "description^2",
                        "body",
                        "text"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "title": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "body": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            title = source.get("title", "Правовая статья")
            content = source.get("content", source.get("body", source.get("text", "")))
            author = source.get("author", "")
            publication_date = source.get("publication_date", source.get("date", ""))
            source_name = source.get("source", "")
            tags = source.get("tags", source.get("keywords", ""))
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["title", "content", "body", "text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Правовая статья: {title}\n"
            
            if author:
                result += f"Автор: {author}\n"
            
            if publication_date:
                result += f"Дата публикации: {publication_date}\n"
            
            if source_name:
                result += f"Источник: {source_name}\n"
            
            if tags:
                tags_str = tags if isinstance(tags, str) else ", ".join(tags)
                result += f"Теги: {tags_str}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Содержание:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} правовых статей")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе legal_articles: {str(e)}")
        return []

def create_court_decisions_index(es):
    """
    Создает индекс court_decisions в Elasticsearch, если он не существует.
    
    Args:
        es: Клиент Elasticsearch
    """
    index_name = ES_INDICES.get("court_decisions", "court_decisions_index")
    
    # Проверяем, существует ли индекс
    if not es.indices.exists(index=index_name):
        # Определяем маппинг для индекса
        mappings = {
            "properties": {
                "case_number": {"type": "text", "analyzer": "russian"},
                "judges": {"type": "text", "analyzer": "russian"},
                "claimant": {"type": "text", "analyzer": "russian"},
                "defendant": {"type": "text", "analyzer": "russian"},
                "subject": {"type": "text", "analyzer": "russian"},
                "arguments": {"type": "text", "analyzer": "russian"},
                "conclusion": {"type": "text", "analyzer": "russian"},
                "full_text": {"type": "text", "analyzer": "russian"}
            }
        }
        
        # Создаем индекс
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "russian": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_morphology", "russian_stop"]
                            }
                        }
                    }
                },
                "mappings": mappings
            }
        )
        
        logger.info(f"✅ Индекс {index_name} успешно создан.")
    else:
        logger.info(f"✅ Индекс {index_name} уже существует.")

def create_ruslawod_chunks_index(es):
    """
    Создает индекс ruslawod_chunks в Elasticsearch, если он не существует.
    
    Args:
        es: Клиент Elasticsearch
    """
    index_name = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
    
    # Проверяем, существует ли индекс
    if not es.indices.exists(index=index_name):
        # Определяем маппинг для индекса
        mappings = {
            "properties": {
                "law_name": {"type": "text", "analyzer": "russian"},
                "section_name": {"type": "text", "analyzer": "russian"},
                "article_name": {"type": "text", "analyzer": "russian"},
                "document_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "content": {"type": "text", "analyzer": "russian"},
                "text": {"type": "text", "analyzer": "russian"},
                "full_text": {"type": "text", "analyzer": "russian"}
            }
        }
        
        # Создаем индекс
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "russian": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_morphology", "russian_stop"]
                            }
                        }
                    }
                },
                "mappings": mappings
            }
        )
        
        logger.info(f"✅ Индекс {index_name} успешно создан.")
    else:
        logger.info(f"✅ Индекс {index_name} уже существует.")

def create_indices():
    """
    Создает все необходимые индексы в Elasticsearch.
    """
    try:
        es = get_es_client()
        
        # Создаем индексы
        create_court_decisions_index(es)
        create_ruslawod_chunks_index(es)
        
        # Также можно создать индексы для court_reviews и legal_articles,
        # но пока оставим их без явного создания
        
        logger.info("✅ Все необходимые индексы проверены или созданы.")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании индексов: {str(e)}")

def index_court_decisions():
    """
    Индексирует данные судебных решений в Elasticsearch.
    Для совместимости с предыдущей версией.
    """
    create_indices()

if __name__ == "__main__":
    # Создание индексов при запуске модуля напрямую
    create_indices()
    
    # Пример поиска
    test_query = "А65-28469/2012"
    results = search_law_chunks(test_query)
    print(f"Поиск по запросу '{test_query}': найдено {len(results)} результатов")
    
    if results:
        print("\nПервый результат:")
        print(results[0][:500] + "...")