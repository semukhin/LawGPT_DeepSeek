"""
Модуль для работы с DeepSeek API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
"""
from typing import Dict, Optional, List, Any, Union
from sqlalchemy.orm import Session 
import logging
import json
import asyncio
from app.handlers.parallel_search import run_parallel_search
from app.utils import measure_time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.web_search import google_search, search_and_scrape, run_multiple_searches
from app.services.deepresearch_service import DeepResearchService, ResearchResult
from app.services.deepseek_service import DeepSeekService
from app.models import Message, Thread
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from app.context_manager import ContextManager
from app.utils.chat_utils import get_messages

# Инициализация сервисов
deep_research_service = DeepResearchService()
deepseek_service = DeepSeekService(
    api_key=DEEPSEEK_API_KEY, 
    model=DEEPSEEK_MODEL,
    temperature=0.7,    
)

# Инициализация менеджера контекста
context_manager = ContextManager(model=DEEPSEEK_MODEL)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Добавить в начало файла
MAX_PROMPT_CHARS = 30000  # Максимальная длина итогового промта
MAX_SEARCH_RESULTS_CHARS = 10000  # Лимит на результаты поиска
MAX_ES_RESULT_CHARS = 10000  # Лимит на один фрагмент из ElasticSearch
MAX_WEB_RESULT_CHARS = 3800  # Лимит на один веб-результат

def log_function_call(function_name: str, arguments: Dict) -> None:
    """Логирует вызов функции с аргументами для отладки."""
    logging.info(f"🔍 ФУНКЦИЯ ВЫЗВАНА: {function_name}")
    logging.info(f"🔍 АРГУМЕНТЫ: {json.dumps(arguments, ensure_ascii=False)}")

@measure_time
async def send_custom_request(user_query: str, thread_id: Optional[str] = None, db: Optional[Session] = None, document_text: str = "") -> str:
    """
    Отправляет пользовательский запрос и выполняет прямой поиск без function calling.
    """
    logging.info(f"📝 Новый запрос пользователя: {user_query[:100]}...")

    try:
        # Получаем историю сообщений, если есть thread_id
        chat_history = []
        if thread_id and db:
            chat_history = await get_messages(thread_id, db)
            logging.info(f"📜 Получена история чата: {len(chat_history)} сообщений")
        
        # Подготавливаем контекст с историей
        prepared_context = context_manager.prepare_context(chat_history)
        logging.info(f"📜 Подготовленный контекст: {len(prepared_context)} сообщений")

        # Проверяем, является ли запрос общим вопросом (не юридическим)
        is_general = deep_research_service.is_general_query(query=user_query)
        
        logging.info(f"🔎 Результат проверки is_general_query: {'общий запрос' if is_general else 'юридический запрос'}")
        
        # Формируем обогащенный запрос
        enhanced_query = f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_query}\n\n"
        
        # Для общих запросов пропускаем поиск
        if not is_general:
            logging.info("🔍 Выполняем поиск для юридического запроса")
            
            # Выполняем параллельный поиск
            search_results = await run_parallel_search(user_query)
            
            if search_results and not search_results.get("error"):
                # Добавляем результаты поиска в запрос
                if "combined_context" in search_results:
                    enhanced_query += "РЕЗУЛЬТАТЫ ПОИСКА:\n" + search_results["combined_context"]
                else:
                    enhanced_query += "РЕЗУЛЬТАТЫ ПОИСКА:\nРелевантная информация не найдена."
            else:
                enhanced_query += "РЕЗУЛЬТАТЫ ПОИСКА:\nРелевантная информация не найдена."
        
        # Добавляем историю чата в запрос
        if prepared_context:
            enhanced_query += "\nИСТОРИЯ ЧАТА:\n"
            for msg in prepared_context:
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                enhanced_query += f"{role}: {msg['content']}\n"
        
        # Получаем ответ от DeepSeek API, передавая уже определенный тип запроса
        response = await deep_research_service.research(enhanced_query, is_general=is_general)
        
        # Извлекаем ответ из результата
        if isinstance(response, ResearchResult):
            assistant_response = response.analysis
        elif isinstance(response, dict) and 'choices' in response and len(response['choices']) > 0:
            assistant_response = response['choices'][0]['message']['content']
        else:
            assistant_response = str(response)
        
        # Сохраняем сообщения в БД
        if thread_id and db:
            # Сохраняем запрос пользователя
            user_message = Message(
                thread_id=thread_id,
                role="user",
                content=user_query
            )
            db.add(user_message)
            
            # Сохраняем ответ ассистента
            assistant_message = Message(
                thread_id=thread_id,
                role="assistant",
                content=assistant_response
            )
            db.add(assistant_message)
            db.commit()
        
        return assistant_response
        
    except Exception as e:
        logging.error(f"❌ Ошибка при обработке запроса: {str(e)}")
        return f"Произошла ошибка при обработке запроса: {str(e)}"


# Определение схем функций для DeepSeek API
AVAILABLE_FUNCTIONS = [
    {
        "name": "search_law_chunks",
        "description": "Поиск в базе российского законодательства по указанному запросу. Используй эту функцию для запросов о законах, правовых нормах, гражданском кодексе, и других законодательных актах.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в законодательстве. Должен содержать ключевые юридические термины и номера статей, если известны."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_web",
        "description": "Поиск в интернете по указанному запросу. Используй для поиска судебной практкии, актуальной информации, статей, и обзоров.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в интернете. Запрос должен быть сформулирован так, чтобы получить актуальную информацию по теме."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "deep_research",
        "description": "Проведение глубокого исследования по указанному запросу. Используй для комплексного анализа правовых вопросов на основе найденной информации.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для глубокого исследования. Должен быть детальным и содержать конкретную юридическую проблему для анализа."
                }
            },
            "required": ["query"]
        }
    }
]


@measure_time
async def handle_function_call(function_name: str, arguments: Dict, thread_id: Optional[str] = None, db: Optional[Session] = None) -> Dict:
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

                # Соединяем все найденные чанки в один текст
                combined_text = "\n\n".join(es_results)

                # Используем DeepResearch для анализа найденного законодательства
                deep_results = await deep_research_service.research(
                    query=combined_text, 
                    thread_id=thread_id,  # Передаем thread_id
                    message_id=None, 
                    user_id=None, 
                    db=db  # Передаем db
                )

                return {
                    "found": True,
                    "chunks_count": len(es_results),
                    "deep_research_results": deep_results.to_dict()
                }

            logging.info("❌ Результаты поиска в законодательстве не найдены.")
            return {"found": False, "error": "Результаты поиска в законодательстве не найдены."}
        except Exception as e:
            logging.error(f"Ошибка при поиске в законодательстве: {str(e)}")
            return {"found": False, "error": f"Ошибка при поиске в законодательстве: {str(e)}"}


    elif function_name == "search_web":
        try:
            logging.info("🔍 Выполнение веб-поиска для запроса: '%s'", query)
            logs = []

            # Используем множественный поиск вместо простого
            search_results = await run_multiple_searches(query, logs)

            # Собираем все успешные результаты из разных типов поиска
            all_results = []
            for search_type, results in search_results.items():
                all_results.extend(results)

            if all_results:
                logging.info(f"✅ Найдено {len(all_results)} релевантных веб-страниц")

                # Подготавливаем контент для анализа
                extracted_texts = []
                for result in all_results:
                    if result.is_successful():
                        extracted_texts.append({
                            "url": result.url,
                            "title": result.title,
                            "text": result.text[:2000]  # Берем до 2000 символов из каждого источника
                        })

                combined_text = "\n\n".join([
                    f"Источник: {item['url']}\nЗаголовок: {item['title']}\n{item['text']}"
                    for item in extracted_texts
                ])

                user_id = None
                message_id = None
                if thread_id and db:
                    try:
                        # Получаем последнее сообщение пользователя
                        user_message = db.query(Message).filter(
                            Message.thread_id == thread_id,
                            Message.role == "user"
                        ).order_by(Message.created_at.desc()).limit(10).first()

                        if user_message:
                            message_id = user_message.id

                        # Получаем текущего пользователя через связь треда
                        thread = db.query(Thread).filter(Thread.id == thread_id).first()
                        if thread:
                            user_id = thread.user_id
                    except Exception as e:
                        logging.error(f"❌ Ошибка при получении данных для логирования: {e}")

                # Используем DeepResearch для анализа
                deep_results = await deep_research_service.research(combined_text)

                return {
                    "found": True, 
                    "sources_count": len(extracted_texts),
                    "sources": [{"url": item["url"], "title": item["title"]} for item in extracted_texts[:5]],
                    "deep_research_results": deep_results.to_dict()
                }

            logging.info("❌ Релевантные веб-результаты не найдены.")
            return {"found": False, "error": "Релевантные веб-результаты не найдены."}
        except Exception as e:
            logging.error(f"Ошибка при веб-поиске: {str(e)}")
            return {"found": False, "error": f"Ошибка при веб-поиске: {str(e)}"}


    elif function_name == "deep_research":
        try:
            logging.info("🔍 Выполнение глубокого исследования для запроса: '%s'", query)

            # Собираем контекст из всех доступных источников
            logs = []
            additional_context = []

            # 1. Поиск в Elasticsearch
            try:
                es_results = search_law_chunks(query)
                if es_results:
                    additional_context.append({
                        "type": "legislation",
                        "found": True,
                        "data": es_results[:10]  # Берем до 10 наиболее релевантных результатов
                    })
            except Exception as e:
                logging.error(f"Ошибка при получении контекста из Elasticsearch: {str(e)}")

            # 2. Поиск в интернете
            try:
                web_results = await run_multiple_searches(query, logs)
                all_web_results = []
                for search_type, results in web_results.items():
                    all_web_results.extend(results)

                if all_web_results:
                    extracted_texts = []
                    for result in all_web_results:
                        if result.is_successful():
                            extracted_texts.append({
                                "url": result.url,
                                "title": result.title,
                                "text": result.text[:2000]  # Ограничиваем размер для каждого результата
                            })

                    if extracted_texts:
                        additional_context.append({
                            "type": "web",
                            "found": True,
                            "data": extracted_texts[:3]  # Берем до 3 наиболее релевантных результатов
                        })
            except Exception as e:
                logging.error(f"Ошибка при получении контекста из интернета: {str(e)}")

            # Выполняем исследование с учетом всего найденного контекста
            deep_results = await deep_research_service.research(query, additional_context)

            return {
                "found": True,
                "deep_research_results": deep_results.to_dict()
            }
        except Exception as e:
            logging.error(f"Ошибка при глубоком исследовании: {str(e)}")
            return {"found": False, "error": f"Ошибка при глубоком исследовании: {str(e)}"}

    return {"found": False, "error": f"Неизвестная функция: {function_name}"}