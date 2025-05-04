from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9201")

indices = [
    "court_decisions_index",
    "court_reviews_index",
    "legal_articles_index",
    "ruslawod_chunks_index",
    "procedural_forms_index"
]

for index in indices:
    mapping = {
        "properties": {
            "embedding": {
                "type": "dense_vector",
                "dims": 384
            }
        }
    }
    es.indices.put_mapping(index=index, body=mapping)
    print(f"Поле embedding добавлено в {index}")