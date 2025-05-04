from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Настройки
ES_HOST = "http://localhost:9201"
INDICES = {
   #"court_decisions_index": "full_text",
   #"court_reviews_index": "full_text",
   #"legal_articles_index": "full_text",
   #"ruslawod_chunks_index": "text",
    "procedural_forms_index": "text"
}
EMBEDDING_DIM = 384
BATCH_SIZE = 100

# Инициализация
es = Elasticsearch(ES_HOST)
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

def get_embedding(text):
    if not text:
        return [0.0] * EMBEDDING_DIM
    return model.encode(text, show_progress_bar=False).tolist()

for index, text_field in INDICES.items():
    print(f"\nИндекс: {index} | Поле для эмбеддинга: {text_field}")
    # Получаем все id документов
    resp = es.search(index=index, body={"query": {"match_all": {}}}, scroll="5m", size=BATCH_SIZE)
    scroll_id = resp['_scroll_id']
    total = resp['hits']['total']['value']
    docs = resp['hits']['hits']

    pbar = tqdm(total=total, desc=f"Обработка {index}")

    while docs:
        actions = []
        for doc in docs:
            doc_id = doc['_id']
            text = doc['_source'].get(text_field, "")
            embedding = get_embedding(text)
            actions.append({
                "_op_type": "update",
                "_index": index,
                "_id": doc_id,
                "doc": {"embedding": embedding}
            })
        if actions:
            helpers.bulk(es, actions)
        pbar.update(len(docs))
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = resp['_scroll_id']
        docs = resp['hits']['hits']
    pbar.close()
    print(f"Индекс {index} обработан.")

print("Готово! Все эмбеддинги сгенерированы и записаны.")