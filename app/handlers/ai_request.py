"""
Модуль для работы с Vertex AI API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
"""
import json
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session 
from app.handlers.parallel_search import run_parallel_search
from app.utils import measure_time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.garant_process import process_garant_request
from app.handlers.web_search import google_search, search_and_scrape
from app.services.deepresearch_service import DeepResearchService
from app.services.vertexai_service import VertexAIService
from app.context_manager import ContextManager
from app.models import Message 
from app.config import VERTEX_AI_SETTINGS

# Инициализация DeepResearchService
deep_research_service = DeepResearchService()

# Конфигурация Vertex AI
vertex_service = VertexAIService(
    project_id=VERTEX_AI_SETTINGS["project_id"],
    location=VERTEX_AI_SETTINGS["location"],
    model_name=VERTEX_AI_SETTINGS["model_name"],
    temperature=VERTEX_AI_SETTINGS["temperature"],
    max_output_tokens=VERTEX_AI_SETTINGS["max_output_tokens"],
    credentials_path=VERTEX_AI_SETTINGS["credentials_path"]
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_function_call(function_name: str, arguments: Dict) -> None:
    """Логирует вызов функции с аргументами для отладки."""
    logging.info(f"🔍 ФУНКЦИЯ ВЫЗВАНА: {function_name}")
    logging.info(f"🔍 АРГУМЕНТЫ: {json.dumps(arguments, ensure_ascii=False)}")

async def handle_function_call(function_name: str, arguments: Dict) -> Dict:
    """Обработка вызова функций ассистентом."""
    query = arguments.get("query", "")
    
    # Логируем вызов функции для отладки
    log_function_call(function_name, arguments)

    if function_name == "search_law_chunks":
        try:
            logging.info("🔍 Выполнение поиска в Elasticsearch для запроса: '%s'", query)
            es_results = search_law_chunks(query)
            if es_results:
                logging.info(f"✅ Найдено {len(es_results)} релевантных чанков в Elasticsearch")
                for i, chunk in enumerate(es_results[:2]):  # Выводим первые 2 чанка для проверки
                    logging.info(f"📄 Чанк {i+1}: {chunk[:100]}...")
                
                deep_results = await deep_research_service.research("\n".join(es_results))
                return {"deep_research_results": deep_results.to_dict()}
            logging.info("❌ Результаты поиска в законодательстве не найдены.")
            return {"error": "Результаты поиска в законодательстве не найдены."}
        except Exception as e:
            logging.error(f"Ошибка при поиске в законодательстве: {str(e)}")
            return {"error": f"Ошибка при поиске в законодательстве: {str(e)}"}

    elif function_name == "search_garant":
        try:
            logging.info("🔍 Выполнение поиска в Гаранте для запроса: '%s'", query)
            # Создаем простую функцию логирования, которая требуется в process_garant_request
            def rag_module(level, message):
                logging_level = getattr(logging, level.upper(), logging.INFO)
                logging.log(logging_level, message)
                return f"[{level.upper()}] {message}"
                
            garant_results = process_garant_request(query, logs=[], rag_module=rag_module)
            if garant_results:
                logging.info(f"✅ Получены результаты из Гаранта: {garant_results.get('docx_file_path', '')}")
                deep_results = await deep_research_service.research(garant_results.get("docx_file_path", ""))
                return {"deep_research_results": deep_results.to_dict()}
            logging.info("❌ Результаты Гаранта не найдены.")
            return {"error": "Результаты Гаранта не найдены."}
        except Exception as e:
            logging.error(f"Ошибка при поиске в Гаранте: {str(e)}")
            return {"error": f"Ошибка при поиске в Гаранте: {str(e)}"}

    elif function_name == "search_web":
        try:
            logging.info("🔍 Выполнение веб-поиска для запроса: '%s'", query)
            logs = []
            search_results = await search_and_scrape(query, logs)
            
            if search_results:
                extracted_texts = []
                for result in search_results:
                    if result.is_successful():
                        extracted_texts.append({
                            "url": result.url,
                            "title": result.title,
                            "text": result.text[:2000]  # Ограничиваем размер
                        })
                
                if extracted_texts:
                    logging.info(f"✅ Найдено {len(extracted_texts)} релевантных веб-страниц")
                    
                    combined_text = "\n\n".join([
                        f"Источник: {item['url']}\nЗаголовок: {item['title']}\n{item['text']}"
                        for item in extracted_texts
                    ])
                    
                    deep_results = await deep_research_service.research(combined_text)
                    return {"deep_research_results": deep_results.to_dict()}
                
            logging.info("❌ Релевантные веб-результаты не найдены.")
            return {"error": "Релевантные веб-результаты не найдены."}
        except Exception as e:
            logging.error(f"Ошибка при веб-поиске: {str(e)}")
            return {"error": f"Ошибка при веб-поиске: {str(e)}"}
    
    elif function_name == "deep_research":
        try:
            logging.info("🔍 Выполнение глубокого исследования для запроса: '%s'", query)
            deep_results = await deep_research_service.research(query)
            return {"deep_research_results": deep_results.to_dict()}
        except Exception as e:
            logging.error(f"Ошибка при глубоком исследовании: {str(e)}")
            return {"error": f"Ошибка при глубоком исследовании: {str(e)}"}
            
    return {"error": f"Неизвестная функция: {function_name}"}


@measure_time
async def send_custom_request(user_query: str, thread_id: Optional[str] = None, db: Optional[Session] = None) -> str:
    """
    Отправляет пользовательский запрос к Vertex AI.
    
    Args:
        user_query: Запрос пользователя
        thread_id: ID треда, если есть
        db: Сессия базы данных
        
    Returns:
        Ответ ассистента в виде строки
    """
    logging.info(f"📝 Новый запрос пользователя: {user_query[:100]}...")
    
    # Создаем промпт для ассистента
    system_prompt = """
    Ты - юридический ассистент LawGPT, специализирующийся на российском законодательстве.
    Твоя задача - предоставлять точную, полезную информацию по юридическим вопросам.
    
    Придерживайся следующих принципов:
    1. Используй актуальную информацию из российского законодательства
    2. Отвечай структурированно и информативно
    3. Если не уверен в ответе, так и скажи - не выдумывай информацию
    4. Предлагай ссылки на законы и нормативные акты, когда это уместно
    
    Ты можешь использовать следующие функции для исследования:
    - search_law_chunks: Поиск в базе российского законодательства
    - search_garant: Поиск в базе Гарант
    - search_web: Поиск в интернете
    - deep_research: Проведение глубокого исследования по запросу
    
    Функции позволяют тебе получить актуальную информацию для ответа.
    """
    
    # Подготовка истории сообщений
    context_messages = []
    
    # Если есть thread_id и db, получаем предыдущие сообщения из треда
    if thread_id and db:
        try:
            # Получаем последние сообщения из треда (не более 10)
            previous_messages = db.query(Message).filter(
                Message.thread_id == thread_id
            ).order_by(Message.created_at.desc()).limit(10).all()
            
            # Переворачиваем список, чтобы сообщения были в хронологическом порядке
            previous_messages.reverse()
            
            # Формируем историю сообщений
            for msg in previous_messages:
                if msg.role in ["user", "assistant"]:
                    context_messages.append({"role": msg.role, "content": msg.content})
        except Exception as e:
            logging.error(f"❌ Ошибка при получении истории сообщений: {e}")
    
    # Добавляем системный промпт и текущий запрос пользователя
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Добавляем контекст, если он есть
    if context_messages:
        messages.extend(context_messages)
    
    # Добавляем текущий запрос пользователя
    messages.append({"role": "user", "content": user_query})
    
    try:
        # Отправляем запрос к Vertex AI
        response = await vertex_service.chat_completion(messages)
        
        # Проверяем, нужно ли выполнить функцию
        if "функция:" in response.lower() or "function:" in response.lower():
            try:
                # Извлекаем имя функции и аргументы из ответа
                function_name = None
                arguments = {}
                
                # Простой парсер для извлечения функций
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if "функция:" in line.lower() or "function:" in line.lower():
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            function_name = parts[1].strip()
                    
                    # Проверяем наличие аргументов
                    if function_name and ("аргументы:" in line.lower() or "arguments:" in line.lower()):
                        # Пытаемся найти JSON объект после этой строки
                        json_str = ""
                        j = i + 1
                        while j < len(lines) and not lines[j].strip().startswith(("функция:", "function:")):
                            json_str += lines[j] + "\n"
                            j += 1
                        
                        try:
                            # Пытаемся распарсить JSON
                            arguments = json.loads(json_str)
                        except json.JSONDecodeError:
                            # Если не удалось распарсить JSON, извлекаем query напрямую
                            arguments = {"query": user_query}
                
                # Если имя функции определено, вызываем её
                if function_name:
                    function_result = await handle_function_call(function_name, arguments)
                    
                    # Формируем новое сообщение с результатами функции
                    function_response = f"Результаты выполнения функции {function_name}:\n{json.dumps(function_result, ensure_ascii=False, indent=2)}"
                    
                    # Отправляем запрос с результатами функции
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": function_response})
                    
                    # Получаем финальный ответ
                    final_response = await vertex_service.chat_completion(messages)
                    return final_response
            except Exception as func_error:
                logging.error(f"❌ Ошибка при вызове функции: {func_error}")
        
        return response
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке запроса к Vertex AI: {e}")
        return f"Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позднее. Ошибка: {str(e)}"