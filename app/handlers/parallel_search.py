import logging
from typing import Dict, Any
from app.handlers.es_law_search import search_law_chunks
from app.handlers.garant_process import process_garant_request
from app.handlers.web_search import search_and_scrape
import asyncio
import time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.garant_process import process_garant_request
from app.handlers.web_search import search_and_scrape


async def run_parallel_search(query: str) -> Dict[str, Any]:
    """
    Запускает параллельный поиск во всех доступных источниках.
    
    Args:
        query: Текст запроса пользователя
        
    Returns:
        Словарь с результатами всех поисковых функций
    """
    logging.info(f"🚀 Запуск параллельного поиска для запроса: '{query}'")
    start_time = time.time()
    
    # Функция для логирования результатов
    def rag_module(level, message):
        logging_level = getattr(logging, level.upper(), logging.INFO)
        logging.log(logging_level, message)
        return f"[{level.upper()}] {message}"
    
    logs = []
    
    # Запуск всех поисковых функций параллельно
    async def search_elastic_task():
        try:
            logging.info("⏳ Поиск в Elasticsearch...")
            es_results = search_law_chunks(query, top_n=10)
            return {"type": "elasticsearch", "results": es_results}
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в Elasticsearch: {str(e)}")
            return {"type": "elasticsearch", "results": [], "error": str(e)}
    
    async def search_garant_task():
        try:
            logging.info("⏳ Поиск в Гаранте...")
            garant_results = process_garant_request(query, logs=logs, rag_module=rag_module)
            if garant_results and "docx_file_path" in garant_results:
                # Извлекаем текст из docx
                from app.handlers.user_doc_request import extract_text_from_any_document
                docx_path = garant_results.get("docx_file_path")
                docx_text = extract_text_from_any_document(docx_path)
                return {
                    "type": "garant", 
                    "results": {"text": docx_text, "path": docx_path}
                }
            return {"type": "garant", "results": {}}
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в Гаранте: {str(e)}")
            return {"type": "garant", "results": {}, "error": str(e)}
    
    async def search_web_task():
        try:
            logging.info("⏳ Поиск в интернете...")
            scraped_results = await search_and_scrape(query, logs=logs)
            
            extracted_texts = []
            for result in scraped_results:
                if result.is_successful():
                    extracted_texts.append({
                        "url": result.url,
                        "title": result.title,
                        "text": result.text[:5000]  # Берем первые 5000 символов для каждой страницы
                    })
                    
            return {"type": "web", "results": extracted_texts}
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в интернете: {str(e)}")
            return {"type": "web", "results": [], "error": str(e)}
    
    # Запускаем все задачи параллельно
    tasks = [
        search_elastic_task(),
        search_garant_task(),
        search_web_task()
    ]
    
    # Ждем завершения всех задач
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Формируем итоговый результат
    combined_results = {}
    
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"❌ Ошибка в одном из поисковых запросов: {str(result)}")
            continue
            
        combined_results[result["type"]] = result["results"]
    
    elapsed_time = time.time() - start_time
    logging.info(f"✅ Параллельный поиск завершен за {elapsed_time:.2f} секунд")
    
    return combined_results