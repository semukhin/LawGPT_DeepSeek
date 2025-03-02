"""
Модуль для работы с DeepSeek API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
"""
import json
import asyncio
import logging
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session 
from app.handlers.parallel_search import run_parallel_search
from app.utils import measure_time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.garant_process import process_garant_request
from app.handlers.web_search import google_search, search_and_scrape, run_multiple_searches
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
    temperature=0.2  # Уменьшаем температуру для более детерминированного поведения
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
                
                # Соединяем все найденные чанки в один текст
                combined_text = "\n\n".join(es_results)
                
                # Используем DeepResearch для анализа найденного законодательства
                deep_results = await deep_research_service.research(combined_text)
                
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
                            "text": result.text[:3000]  # Берем до 3000 символов из каждого источника
                        })
                
                combined_text = "\n\n".join([
                    f"Источник: {item['url']}\nЗаголовок: {item['title']}\n{item['text']}"
                    for item in extracted_texts
                ])
                
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
                        "data": es_results[:5]  # Берем до 5 наиболее релевантных результатов
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
                            "data": extracted_texts[:5]  # Берем до 5 наиболее релевантных результатов
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
        "name": "search_garant",
        "description": "Поиск в базе Гарант по указанному запросу. Используй для поиска судебной практики, постановлений, и решений судов.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст запроса для поиска в базе Гарант. Для поиска судебной практики сформулируй запрос с указанием релевантных статей и конкретными юридическими терминами."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_web",
        "description": "Поиск в интернете по указанному запросу. Используй для поиска актуальной информации, статей, и обзоров.",
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
        "description": "Проведение глубокого исследования по указанному запросу. Используй для комплексного анализа правовых вопросов.",
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
async def send_custom_request(user_query: str, thread_id: Optional[str] = None, db: Optional[Session] = None) -> str:
    """
    Отправляет пользовательский запрос и выполняет прямой поиск без function calling.
    
    Args:
        user_query: Запрос пользователя
        thread_id: ID треда, если есть
        db: Сессия базы данных
        
    Returns:
        Ответ ассистента в виде строки
    """
    logging.info(f"📝 Новый запрос пользователя: {user_query[:100]}...")
    
    # Системный промпт для анализа информации
    system_prompt = """
    Ты - юридический ассистент LawGPT (профессиональный юрист), специализирующийся на российском законодательстве.
    Твоя задача - предоставлять точную, полезную информацию по юридическим вопросам,
    основываясь на фактических данных из законодательства, судебной практики и 
    проверенных источников.
    
    Структурируй ответы, выделяя:
    - Применимые нормы законодательства с точными ссылками на статьи законов и другие нормы права,
    - Судебную практику и правовые позиции судов,
    - Практические рекомендации по ситуации.


        1. Ты анализируешь вопросы пользователя, связанные с законодательством, судебной практикой и готовишь процессуальные документы (исковые заявления, отзывы о исковых заявлениях, ходатайства и другие) и договоры. 

        2. Не сокращай твой итоговый ответ, он должен быть большим, максимально развёрнутым и структурированным, с ссылками на нормы права или разъяснения госорганов и цитатами из решений судов.

        3. Используй законы Российской Федерации, комментарии, формы процессуальных документов, договоров, аналитические данные, что позволит тебе предоставлять пользователю персонализированные ответы и рекомендации, основанные на актуальных правовых нормах. 

        4. Ты не должен рекомендовать пользователю обращаться к официальным источникам законов и кодексов, таким как "Гарант" или "КонсультантПлюс", "Кодекс" или kad.arbitr.ru, так как у тебя и так есть доступ к кодексам и законам.

        5. Не упоминай в ответах источник данных. Тебе нельзя в сообщениях пользователю сообщать какими источниками данных ты пользуешься.

        6. Диалог с пользователем следует вести исключительно по юридическим вопросам, строго избегая технические.

            СТРОГО ЗАПРЕЩЕНО:
        1. НИКОГДА не указывай номера судебных дел с повторяющимися или последовательными цифрами (например, А40-123456/2019, А40-123123/2020, А40-123321/2022 и т.п.).
        2. НИКОГДА не указывай выдуманные номера судебных дел.
        3. При ссылке на судебную практику либо:
        а) ссылайся только на реальные номера дел из предоставленных источников,
        б) либо указывай общие сведения о судебной позиции без привязки к конкретным делам (например: "Согласно позиции ВС РФ..." или "В судебной практике сложился подход...").
        4. Никогда не указывай номера дел вида "А40-XXXXXX/YYYY", где XXXXXX - шестизначное число, а YYYY - год, если ты его придумал.

        Если не уверен в точности номера дела - НЕ УКАЗЫВАЙ его вообще.
    
    При ответах на вопросы о судебной практике указывай, что ты приводишь "обобщенную информацию из судебной практики".
    
    Основывайся ТОЛЬКО на фактической информации из предоставленных источников.
    НЕ ВЫДУМЫВАЙ информацию.    """
    
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
    
    # Собираем контекст из источников параллельно
    logs = []
    combined_context = ""
    search_tasks = []
    
    # 1. Функция поиска в ElasticSearch (всегда выполняем)
    @measure_time
    async def search_elasticsearch():
        try:
            es_results = search_law_chunks(user_query)
            if es_results:
                logging.info(f"✅ Найдено {len(es_results)} релевантных чанков в Elasticsearch")
                result_text = "## Информация из законодательства:\n\n"
                for i, chunk in enumerate(es_results[:5]):  # Берем до 5 наиболее релевантных результатов
                    result_text += f"{chunk}\n\n"
                return result_text
            return ""
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в законодательстве: {str(e)}")
            return ""
    
    # 2. Функция поиска в интернете (всегда выполняем)
    async def search_internet():
        try:
            logging.info("🔍 Выполнение поиска в интернете...")
            
            # Создаем собственный список для логирования
            internet_logs = []
            
            search_results = await run_multiple_searches(
                query=user_query, 
                logs=internet_logs
            )
            
            # Добавляем логи интернет-поиска в общие логи
            if logs is not None and isinstance(logs, list):
                logs.extend(internet_logs)
            
            # Статистика результатов скрапинга
            successful_pages = 0
            failed_pages = 0
            all_web_results = []
            
            # Собираем все результаты из разных типов поиска
            for search_type, results in search_results.items():
                if results and isinstance(results, list):
                    for result in results:
                        if hasattr(result, 'is_successful') and result.is_successful():
                            successful_pages += 1
                            all_web_results.append(result)
                        else:
                            failed_pages += 1
                            if hasattr(result, 'url') and hasattr(result, 'error'):
                                logging.error(f"❌ Ошибка скрапинга {result.url}: {result.error}")
            
            logging.info(f"📊 Статистика скрапинга: успешно {successful_pages}, неудачно {failed_pages}")
            
            if all_web_results:
                logging.info(f"✅ Найдено {len(all_web_results)} релевантных веб-страниц с текстом")
                
                # Добавляем найденные результаты в контекст
                result_text = "## Информация из интернета:\n\n"
                for i, result in enumerate(all_web_results[:5]):
                    logging.info(f"📄 Успешно извлечен текст с {result.url} ({len(result.text)} символов)")
                    result_text += f"Источник: {result.url}\nЗаголовок: {result.title}\n{result.text[:2000]}...\n\n"
                return result_text
            else:
                logging.info("❌ Релевантные результаты из интернета не найдены")
                return ""
        except Exception as e:
            logging.error(f"❌ Ошибка при веб-поиске: {str(e)}")
            return ""
    
    # 3. Запускаем все поиски параллельно (без Гаранта)
    search_tasks.append(search_elasticsearch())
    search_tasks.append(search_internet())
    
    search_results = await asyncio.gather(*search_tasks)
    
    # 4. Объединяем результаты всех поисков
    for result in search_results:
        if result:
            combined_context += result
    
    # 5. Если нет результатов поиска, добавляем сообщение
    if not combined_context.strip():
        logging.warning("⚠️ Не найдено релевантной информации ни в одном источнике")
        combined_context = "## Информация из источников не найдена\n\nПо запросу не удалось найти релевантную информацию в источниках. Ответ будет основан на общих знаниях."
    
    # Формируем запрос с контекстом для глубокого исследования
    user_query_with_context = f"Запрос пользователя: {user_query}\n\nНайденная информация:\n{combined_context}"
    
    try:
        # Используем DeepResearch для анализа собранной информации
        logging.info("🔍 Выполнение глубокого исследования с учетом всех источников...")
        deep_results = await deep_research_service.research(user_query_with_context)
        final_response = deep_results.analysis
        
        # Сохраняем сообщения в БД, если указан thread_id
        if thread_id and db:
            try:
                db.add(Message(thread_id=thread_id, role="user", content=user_query))
                db.add(Message(thread_id=thread_id, role="assistant", content=final_response))
                db.commit()
                logging.info(f"✅ Сообщения сохранены в БД для треда {thread_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка при сохранении сообщений в БД: {e}")
        
        return final_response
    except Exception as e:
        error_msg = f"Извините, произошла ошибка при выполнении исследования: {str(e)}"
        logging.error(f"❌ Ошибка при глубоком исследовании: {str(e)}")
        
        # Сохраняем в БД сообщение об ошибке
        if thread_id and db:
            try:
                db.add(Message(thread_id=thread_id, role="user", content=user_query))
                db.add(Message(thread_id=thread_id, role="assistant", content=error_msg))
                db.commit()
            except Exception as db_err:
                logging.error(f"❌ Ошибка при сохранении сообщений об ошибке в БД: {db_err}")
        
        return error_msg