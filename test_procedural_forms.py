import logging
import sys
import os
import json

# Настраиваем пути для импорта модулей из app
sys.path.append('/opt/lawgpt')

# Импортируем обновленный модуль для поиска
from app.handlers.es_law_search import get_smart_search_service, search_law_chunks

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_procedural_forms_search(query):
    """
    Тестирование поиска форм процессуальных документов
    
    Args:
        query: Текст запроса
    """
    logger.info(f"Запрос: '{query}'")
    
    # Используем SmartSearchService для поиска
    smart_search = get_smart_search_service()
    
    # Проверяем, определяется ли тип документа
    doc_type = smart_search.extract_document_type(query)
    if doc_type:
        logger.info(f"Определен тип документа: {doc_type}")
    
    # Выполняем умный поиск
    search_results = smart_search.smart_search(query, limit=5)
    
    if search_results["type"] == "procedural_form":
        logger.info(f"Найдены процессуальные формы для запроса!")
        results = search_results["results"]
        
        for i, form in enumerate(results, 1):
            title = form.get("title", "")
            doc_type = form.get("doc_type", "")
            category = form.get("category", "")
            
            logger.info(f"Форма #{i}: {title} (тип: {doc_type}, категория: {category})")
    else:
        logger.info(f"Умный поиск определил тип результатов: {search_results['type']}")
    
    # Используем прямой поиск по всем индексам
    logger.info("Используем прямой поиск по всем индексам:")
    chunks = search_law_chunks(query, top_n=3)
    
    logger.info(f"Найдено {len(chunks)} результатов в прямом поиске")
    
    # Выводим только заголовки найденных документов
    for i, chunk in enumerate(chunks, 1):
        if chunk.startswith("ПРОЦЕССУАЛЬНАЯ ФОРМА:"):
            # Извлекаем название процессуальной формы
            title_line = chunk.split("\n")[0]
            logger.info(f"Результат #{i}: {title_line}")
        else:
            # Для других результатов выводим только первую строку
            first_line = chunk.split("\n")[0]
            logger.info(f"Результат #{i}: {first_line}")

if __name__ == "__main__":
    # Тестовый запрос
    query = "Исковое заявление о взыскании задолженности по арендной плате и неустойки"
    test_procedural_forms_search(query)
    
    # Можно также протестировать ещё несколько запросов
    other_queries = [
        "претензия о взыскании неустойки за нарушение сроков",
        "ходатайство о проведении экспертизы",
        "жалоба на действия судебного пристава"
    ]
    
    for q in other_queries:
        print("\n" + "="*50 + "\n")
        test_procedural_forms_search(q)