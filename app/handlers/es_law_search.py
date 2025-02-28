# app/handlers/es_law_search.py

import logging
from typing import List
from elasticsearch import Elasticsearch

# Задайте свои параметры подключения
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "GIkb8BKzkXK7i2blnG2O"
ES_INDEX_NAME = "ruslawod_index"



def search_law_chunks(query: str, top_n: int = 10) -> List[str]:
    """
    Ищет релевантные чанки в Elasticsearch по полю text_chunk,
    возвращает список текстов (строк).
    """
    try:
        # Создаём клиент с аутентификацией
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS)
        )

        # Улучшенный запрос с использованием multi_match
        body = {
            "size": top_n,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text_chunk^3", "title^2", "document_number"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        }

        response = es.search(index=ES_INDEX_NAME, body=body)
        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            source = hit["_source"]
            chunk_text = source["text_chunk"]
            document_title = source.get("title", "")
            document_number = source.get("document_number", "")
            results.append(f"Документ: {document_title} ({document_number})\n{chunk_text}")

        logging.info(f"🔍 [ES] Найдено {len(results)} релевантных чанков по запросу '{query}'.")
        return results

    except Exception as e:
        logging.error(f"❌ Ошибка при поиске в Elasticsearch: {e}")
        return []
