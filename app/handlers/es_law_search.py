# app/handlers/es_law_search.py

import logging
from typing import List
from elasticsearch import Elasticsearch

# Задайте свои параметры подключения
ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "GIkb8BKzkXK7i2blnG2O"
ES_INDEX_NAME = "ruslawod_index"


def search_law_chunks(query: str, top_n: int = 15) -> List[str]:
    """
    Ищет релевантные чанки в Elasticsearch.
    """
    try:
        # Создаём клиент с аутентификацией и настройками сессии
        es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            retry_on_timeout=True,
            max_retries=3,
            request_timeout=30
        )

        # Улучшенный запрос для поиска разных типов документов
        body = {
            "size": top_n,
            "query": {
                "bool": {
                    "should": [
                        # Точное совпадение с высоким весом
                        {
                            "match_phrase": {
                                "text_chunk": {
                                    "query": query,
                                    "boost": 5
                                }
                            }
                        },
                        # Многополевой поиск
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["text_chunk^3", "title^2", "document_number", "document_type"],
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
                    "text_chunk": {
                        "pre_tags": ["<b>"],
                        "post_tags": ["</b>"],
                        "fragment_size": 300,
                        "number_of_fragments": 3
                    }
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
            
            # Добавляем подсветку, если есть
            highlights = hit.get("highlight", {}).get("text_chunk", [])
            if highlights:
                highlight_text = "...\n".join(highlights)
                results.append(f"Документ: {document_title} ({document_number})\nРелевантные фрагменты:\n{highlight_text}\n\nПолный контекст:\n{chunk_text[:1000]}...")
            else:
                results.append(f"Документ: {document_title} ({document_number})\n{chunk_text[:1500]}...")

        logging.info(f"🔍 [ES] Найдено {len(results)} релевантных чанков.")
        return results

    except Exception as e:
        logging.error(f"❌ Ошибка при поиске в Elasticsearch: {e}")
        return []