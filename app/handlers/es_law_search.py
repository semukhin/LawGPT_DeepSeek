# app/handlers/es_law_search.py

import logging
from typing import List
from elasticsearch import Elasticsearch
import psycopg2
from psycopg2.extras import DictCursor

import psycopg2
from psycopg2.extras import DictCursor
from elasticsearch import Elasticsearch
import logging

ES_HOST = "http://localhost:9200"
ES_USER = "elastic"
ES_PASS = "GIkb8BKzkXK7i2blnG2O"
ES_INDEX = "court_decisions_index"

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ruslaw0d"
DB_USER = "postgres"
DB_PASS = "postgres"

def index_court_decisions():
    """
    Индексация данных из таблицы court_decisions в Elasticsearch.
    """
    es = Elasticsearch(
        [ES_HOST],
        basic_auth=(ES_USER, ES_PASS),
        retry_on_timeout=True,
        max_retries=3,
        request_timeout=30
    )

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cursor = conn.cursor(cursor_factory=DictCursor)

        cursor.execute("SELECT * FROM court_decisions")
        rows = cursor.fetchall()

        for row in rows:
            doc = dict(row)
            es.index(index=ES_INDEX, id=doc['id'], document=doc)

        cursor.close()
        conn.close()
        logging.info("✅ Данные успешно проиндексированы в Elasticsearch")

    except Exception as e:
        logging.error(f"❌ Ошибка индексации данных: {e}")



def search_law_chunks(query: str, top_n: int = 7) -> List[str]:
    """
    Поиск в Elasticsearch по индексу court_decisions_index.
    """
    es = Elasticsearch(
        [ES_HOST],
        basic_auth=(ES_USER, ES_PASS),
        retry_on_timeout=True,
        max_retries=3,
        request_timeout=30
    )

    body = {
        "size": top_n,
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

    try:
        response = es.search(index=ES_INDEX, body=body)
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

        logging.info(f"🔍 [ES] Найдено {len(results)} релевантных результатов.")
        return results

    except Exception as e:
        logging.error(f"❌ Ошибка поиска в Elasticsearch: {e}")
        return []

if __name__ == "__main__":
    index_court_decisions()  # Индексация данных в Elasticsearch
    print(search_law_chunks("А65-28469/2012"))
