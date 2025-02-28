"""
Модуль для работы с DeepSeek API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
"""
import json
import logging
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session 
from app.handlers.parallel_search import run_parallel_search
from app.utils import measure_time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.garant_process import process_garant_request
from app.handlers.web_search import google_search, search_and_scrape
from app.services.deepresearch_service import DeepResearchService
from app.services.deepseek_service import DeepSeekService
from app.context_manager import ContextManager
from app.models import Message 
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

# Инициализация сервисов
deep_research_service = DeepResearchService()
deepseek_service = DeepSeekService(
    api_key=DEEPSEEK_API_KEY, 
    model=DEEPSEEK_MODEL,
    temperature=0.7
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


# Определение схем функций для DeepSeek API
AVAILABLE_FUNCTIONS = [
    {
        "name": "search_law_chunks",
        "description": "Поиск в базе российского законодательства по указанному запросу",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в законодательстве"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_garant",
        "description": "Поиск в базе Гарант по указанному запросу",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в базе Гарант"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_web",
        "description": "Поиск в интернете по указанному запросу",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в интернете"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "deep_research",
        "description": "Проведение глубокого исследования по указанному запросу",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для глубокого исследования"
                }
            },
            "required": ["query"]
        }
    }
]


@measure_time
async def send_custom_request(user_query: str, thread_id: Optional[str] = None, db: Optional[Session] = None) -> str:
    """
    Отправляет пользовательский запрос к DeepSeek API.
    
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
    
    Ты можешь использовать доступные функции для исследования:
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
                elif msg.role == "function":
                    # Обработка сообщений от функций для правильного формата DeepSeek
                    context_messages.append({
                        "role": "function", 
                        "name": msg.metadata.get("function_name", "unknown"), 
                        "content": msg.content
                    })
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
        # Используем DeepSeek с поддержкой function calling
        response = await deepseek_service.chat_with_functions(
            messages=messages,
            functions=AVAILABLE_FUNCTIONS,
            function_call="auto"
        )
        
        # Проверяем, есть ли вызов функции в ответе
        if isinstance(response, dict) and 'choices' in response:
            choice = response['choices'][0]
            message = choice.get('message', {})
            
            if 'function_call' in message:
                function_call = message['function_call']
                function_name = function_call.get('name')
                function_args = json.loads(function_call.get('arguments', '{}'))
                
                logging.info(f"✅ DeepSeek вызвал функцию {function_name}")
                
                # Вызываем указанную функцию
                function_result = await handle_function_call(function_name, function_args)
                
                # Добавляем результат функции в историю сообщений
                messages.append({
                    "role": "assistant",
                    "content": message.get('content', ''),
                    "function_call": {
                        "name": function_name,
                        "arguments": function_call.get('arguments', '{}')
                    }
                })
                
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_result, ensure_ascii=False)
                })
                
                # Получаем финальный ответ
                final_response = await deepseek_service.chat_completion(messages)
                
                # Сохраняем в базу данных, если указан thread_id
                if thread_id and db:
                    try:
                        # Сохраняем исходный запрос пользователя
                        db.add(Message(
                            thread_id=thread_id, 
                            role="user", 
                            content=user_query
                        ))
                        
                        # Сохраняем сообщение с вызовом функции
                        db.add(Message(
                            thread_id=thread_id, 
                            role="assistant", 
                            content=message.get('content', ''),
                            metadata={"function_call": {
                                "name": function_name,
                                "arguments": function_args
                            }}
                        ))
                        
                        # Сохраняем результат функции
                        db.add(Message(
                            thread_id=thread_id, 
                            role="function", 
                            content=json.dumps(function_result, ensure_ascii=False),
                            metadata={"function_name": function_name}
                        ))
                        
                        # Сохраняем финальный ответ
                        db.add(Message(
                            thread_id=thread_id, 
                            role="assistant", 
                            content=final_response
                        ))
                        
                        db.commit()
                    except Exception as e:
                        logging.error(f"❌ Ошибка при сохранении сообщений в БД: {e}")
                
                return final_response
            else:
                # Если нет вызова функции, возвращаем обычный ответ
                response_text = message.get('content', 'Ошибка: Не удалось получить ответ')
                
                # Сохраняем в базу данных, если указан thread_id
                if thread_id and db:
                    try:
                        db.add(Message(thread_id=thread_id, role="user", content=user_query))
                        db.add(Message(thread_id=thread_id, role="assistant", content=response_text))
                        db.commit()
                    except Exception as e:
                        logging.error(f"❌ Ошибка при сохранении сообщений в БД: {e}")
                
                return response_text
        
        # Если ответ в неожиданном формате, возвращаем как есть
        if isinstance(response, str):
            return response
        
        logging.error(f"❌ Неожиданный формат ответа от DeepSeek: {response}")
        return "Ошибка: Неожиданный формат ответа от API"
        
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке запроса к DeepSeek API: {e}")
        return f"Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позднее. Ошибка: {str(e)}"