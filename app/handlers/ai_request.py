"""
Модуль для работы с DeepSeek API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
"""
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session 
import json
import asyncio
from app.handlers.parallel_search import run_parallel_search
from app.handlers.es_law_search import search_law_chunks
from app.handlers.web_search import run_multiple_searches
from app.services.deepresearch_service import DeepResearchService
from app.services.deepseek_service import DeepSeekService
from app.models import get_messages
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from app.context_manager import ContextManager
from app.utils.logger import get_logger

# Инициализация логгера
logger = get_logger()

# Инициализация сервисов
deep_research_service = DeepResearchService()
deepseek_service = DeepSeekService()

# Инициализация менеджера контекста
context_manager = ContextManager(model=DEEPSEEK_MODEL)

# Добавить в начало файла
MAX_PROMPT_CHARS = 30000  # Максимальная длина итогового промта
MAX_SEARCH_RESULTS_CHARS = 10000  # Лимит на результаты поиска
MAX_ES_RESULT_CHARS = 10000  # Лимит на один фрагмент из ElasticSearch
MAX_WEB_RESULT_CHARS = 3800  # Лимит на один веб-результат

# Системные промпты
GENERAL_SYSTEM_PROMPT = """Ты - профессиональный юридический ассистент. Отвечай на вопросы пользователя, основываясь на законодательстве РФ."""

RESEARCH_SYSTEM_PROMPT = """Ты - профессиональный юридический исследователь. Анализируй правовые вопросы, используя законодательство РФ, судебную практику и правовые позиции."""

def log_function_call(function_name: str, arguments: Dict) -> None:
    """Логирует вызов функции с аргументами для отладки."""
    logger.info(f"🔍 ФУНКЦИЯ ВЫЗВАНА: {function_name}")
    logger.info(f"🔍 АРГУМЕНТЫ: {json.dumps(arguments, ensure_ascii=False)}")

def format_chat_history(chat_history: List[Dict]) -> str:
    """
    Форматирует историю чата в строку.
    
    Args:
        chat_history: Список сообщений из базы данных
        
    Returns:
        str: Отформатированная история чата
    """
    if not chat_history:
        return ""
        
    formatted = []
    for msg in chat_history:
        formatted.append(f"Пользователь: {msg.get('user_message', '')}")
        formatted.append(f"Ассистент: {msg.get('assistant_message', '')}")
    
    return "\n".join(formatted)

def build_deepseek_messages(system_prompt: str, chat_history: List[Dict], user_query: str) -> List[Dict]:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-10:]:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_query})
    return messages

async def send_custom_request(
    user_query: str,
    thread_id: Optional[str] = None,
    db: Optional[Session] = None,
    document_text: str = "",
    chat_history: Optional[str] = None
) -> str:
    """
    Отправляет пользовательский запрос и выполняет прямой поиск без function calling.
    Args:
        user_query: Запрос пользователя
        thread_id: ID треда чата
        db: Сессия базы данных
        document_text: Текст документа (если есть)
        chat_history: История чата в формате JSON строки
    Returns:
        str: Ответ ассистента
    """
    logger.info(f"📝 Новый запрос пользователя: {user_query[:100]}...")
    try:
        # Получаем историю сообщений
        messages = None
        if chat_history:
            try:
                messages = json.loads(chat_history)
            except json.JSONDecodeError:
                logger.warning("❌ Не удалось распарсить переданную историю чата как JSON")
        if not messages and thread_id and db:
            messages = await get_messages(thread_id, db)
            logger.info(f"📜 Получена история чата: {len(messages)} сообщений")
        if not messages:
            messages = []
        # Определяем тип запроса
        research_service = DeepResearchService()
        is_general = research_service.is_general_query(user_query)
        system_prompt = GENERAL_SYSTEM_PROMPT if is_general else RESEARCH_SYSTEM_PROMPT
        deepseek_messages = build_deepseek_messages(system_prompt, messages, user_query)
        # Выполняем поиск только для юридических запросов
        search_results = None
        if not is_general:
            logger.info("🚀 Запуск параллельного поиска для юридического запроса")
            search_results = await run_parallel_search(user_query)
        else:
            logger.info("📝 Обработка общего запроса без поиска")
        # Получаем результат исследования, передавая массив сообщений
        result = await research_service.research(
            query=user_query,
            chat_history=deepseek_messages,  # теперь это массив сообщений
            search_data=search_results,
            thread_id=thread_id,
            db=db
        )
        return result.analysis
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке запроса: {str(e)}")
        return f"Извините, произошла ошибка при обработке запроса: {str(e)}"


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


async def handle_function_call(function_name: str, arguments: Dict, thread_id: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Обработка вызова функций ассистентом.
    
    Args:
        function_name: Имя вызываемой функции
        arguments: Аргументы функции
        thread_id: ID треда чата
        db: Сессия базы данных
        
    Returns:
        Dict[str, Any]: Результат выполнения функции
    """
    query = arguments.get("query", "")

    # Логируем вызов функции для отладки
    log_function_call(function_name, arguments)

    if function_name == "search_law_chunks":
        try:
            logger.info("🔍 Выполнение поиска в Elasticsearch для запроса: '%s'", query)
            es_results = search_law_chunks(query)
            if es_results:
                logger.info(f"✅ Найдено {len(es_results)} релевантных чанков в Elasticsearch")
                for i, chunk in enumerate(es_results[:2]):  # Выводим первые 2 чанка для проверки
                    logger.info(f"📄 Чанк {i+1}: {chunk[:100]}...")

                # Соединяем все найденные чанки в один текст
                combined_text = "\n\n".join(es_results)

                # Используем DeepResearch для анализа найденного законодательства
                result = await deep_research_service.research(
                    query=combined_text
                )
                
                return {
                    "found": True,
                    "chunks_count": len(es_results),
                    "deep_research_results": result.to_dict()
                }
            else:
                return {"found": False, "error": "Результаты поиска в законодательстве не найдены."}
                
        except Exception as e:
            logger.error(f"Ошибка при поиске в законодательстве: {str(e)}")
            return {"found": False, "error": f"Ошибка при поиске в законодательстве: {str(e)}"}

    elif function_name == "search_web":
        try:
            logger.info("🔍 Выполнение веб-поиска для запроса: '%s'", query)
            logs = []

            # Используем множественный поиск вместо простого
            search_results = await run_multiple_searches(query, logs)

            # Собираем все успешные результаты из разных типов поиска
            all_results = []
            for search_type, results in search_results.items():
                all_results.extend(results)

            if all_results:
                logger.info(f"✅ Найдено {len(all_results)} релевантных веб-страниц")

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

                # Используем DeepResearch для анализа
                result = await deep_research_service.research(
                    query=combined_text
                )
                
                return {
                    "found": True, 
                    "sources_count": len(extracted_texts),
                    "sources": [{"url": item["url"], "title": item["title"]} for item in extracted_texts[:5]],
                    "deep_research_results": result.to_dict()
                }
            else:
                return {"found": False, "error": "Релевантные веб-результаты не найдены."}
                
        except Exception as e:
            logger.error(f"Ошибка при веб-поиске: {str(e)}")
            return {"found": False, "error": f"Ошибка при веб-поиске: {str(e)}"}

    elif function_name == "deep_research":
        try:
            logger.info("🔍 Выполнение глубокого исследования для запроса: '%s'", query)

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
                logger.error(f"Ошибка при получении контекста из Elasticsearch: {str(e)}")

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
                logger.error(f"Ошибка при получении контекста из интернета: {str(e)}")

            # Выполняем исследование с учетом всего найденного контекста
            result = await deep_research_service.research(
                query=query,
                additional_context=additional_context
            )
            
            return {
                "found": True,
                "deep_research_results": result.to_dict()
            }

        except Exception as e:
            logger.error(f"Ошибка при глубоком исследовании: {str(e)}")
            return {"found": False, "error": f"Ошибка при глубоком исследовании: {str(e)}"}

    return {"found": False, "error": f"Неизвестная функция: {function_name}"}