"""
Модуль для работы с DeepSeek API.
Поддерживает отправку запросов пользователей к ассистенту с возможностью функциональных вызовов.
Дополнительно различает обычные запросы диалога от юридических вопросов.
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
from app.services.deepresearch_service import DeepResearchService
from app.services.deepseek_service import DeepSeekService
from app.models import Message, Thread
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

# Инициализация сервисов
deep_research_service = DeepResearchService()
deepseek_service = DeepSeekService(
    api_key=DEEPSEEK_API_KEY, 
    model=DEEPSEEK_MODEL,
    temperature=0.8
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_function_call(function_name: str, arguments: Dict) -> None:
    """Логирует вызов функции с аргументами для отладки."""
    logging.info(f"🔍 ФУНКЦИЯ ВЫЗВАНА: {function_name}")
    logging.info(f"🔍 АРГУМЕНТЫ: {json.dumps(arguments, ensure_ascii=False)}")


def is_general_query(query: str) -> bool:
    """
    Проверяет, является ли запрос общим (не юридическим).
    
    Args:
        query: Текст запроса пользователя
        
    Returns:
        True, если это общий запрос, False если юридический
    """
    # Преобразуем запрос в нижний регистр для проверки
    query_lower = query.lower().strip()
    
    # Список юридических терминов (приведенный к нижнему регистру)
    legal_terms = [
        "закон", "кодекс", "статья", "договор", "иск", "суд", "право", "юрист", 
        "норма", "регулирован", "законодательств", "ответственност", "штраф", 
        "обязательств", "претензи", "вина", "устав", "соглашение", "гк", "гпк", "кас", 
        "налог", "юрлицо", "физлиц", "гражданин", "организаци", "фгуп", "праве",
        "аренда", "залог", "недвижимость", "сделка", "наследство", "правомочия",
        "акционер", "дивиденды", "правонарушение", "преступление", "имущество",
        "оферта", "акцепт", "нотариус", "доверенность", "представительство",
        "банкротство", "ликвидация", "реорганизация", "выписка", "егрюл", "ооо",
        "капитал", "учредитель", "предприниматель", "ип", "ао", "регистрац", "лиценз",
        "санкц", "арбитраж", "истец", "ответчик", "апелляц", "кассац", "имуществ", "сво"
    ]
    
    # Проверка на юридические термины (ВСЕГДА перед другими проверками)
    for term in legal_terms:
        if term in query_lower:
            # Если найден юридический термин, то это не общий запрос
            return False
    
    # Список паттернов общих запросов
    general_patterns = [
        # Приветствия
        "привет", "здравствуй", "добрый день", "доброе утро", "добрый вечер", "здорово", "хай",
        "приветствую", "салют", "доброго времени", "хеллоу", "ку", "хола", "йоу", "вечер добрый",
        
        # О собеседнике
        "как тебя зовут", "кто ты", "что ты умеешь", "что ты можешь", "чем ты занимаешься",
        "расскажи о себе", "как называешься", "кто тебя создал", "кто разработал",
        "твои возможности", "твоя версия", "твои функции", "ты робот", "ты бот", 
        "искусственный интеллект", "нейронная сеть", "большая языковая модель", 
        "когда тебя создали", "где ты находишься", "твой разработчик",
        
        # Вопросы о самочувствии
        "как дела", "как настроение", "как жизнь", "как ты", "все хорошо", 
        "что нового", "как поживаешь", "как себя чувствуешь", "как твои дела",
        
        # Благодарности
        "спасибо", "благодарю", "спс", "пасиб", "сенкс", "благодарен", "благодарна", 
        "мерси", "признателен", "большое спасибо", "от души", "ценю", "респект",
        
        # Фразы прощания
        "пока", "до свидания", "увидимся", "всего доброго", "до встречи", "бывай",
        "удачи", "прощай", "до скорого", "покеда", "будь здоров", "покедова", "чао",
        
        # Комплименты и оценки
        "молодец", "отлично", "хорошо", "супер", "класс", "круто", "неплохо", "прекрасно", 
        "замечательно", "превосходно", "блестяще", "великолепно", "потрясающе", "умница", 
        "шикарно", "браво", "впечатляет", "огонь", "бомба",
        
        # Извинения и сожаления
        "извини", "прости", "сорри", "виноват", "прошу прощения", "мне жаль", "сожалею", 
        "не хотел", "моя ошибка", "мой косяк", "не обижайся", "извиняюсь",
        
        # Согласие/несогласие
        "согласен", "не согласен", "так точно", "отлично", "неверно", "правильно", 
        "неправильно", "верно", "соглашусь", "поддерживаю", "категорически нет",
        
        # Вопросы о модели
        "какую нейросеть", "какой нейронной", "какой llm", "какая модель", "на чем работаешь",
        "на какой технологии", "на какой основе", "на каком языке", "deepseek", "claude", "gpt",
        "токены", "контекст", "обучение", "языковая модель", "ии", "аи", "искусственный", "ai",
        "сколько параметров", "твоя архитектура", "transformer", "трансформер",
        
        # Короткие подтверждения
        "ок", "ясно", "понял", "понятно", "да", "нет", "конечно", "разумеется", "возможно",
        "именно", "наверное", "вероятно", "очевидно", "логично", "безусловно",
        
        # Просьбы о помощи
        "помоги", "подскажи", "помощь", "поддержка", "не понимаю", "как работает",
        "объясни", "разъясни", "уточни", "как мне", "что делать", "как быть",
        
        # Указания на ошибки
        "ошибка", "ты ошибаешься", "это неправильно", "ошибся", "не так", "неточно",
        "некорректно", "неправда", "путаешь", "заблуждаешься", 
        
        # Просьбы о продолжении
        "продолжай", "дальше", "что еще", "и что", "еще", "расскажи больше",
        "продолжение", "дальнейшее", "следующее", "что потом", "а затем"
    ]

    # Проверяем, содержит ли запрос общие паттерны
    for pattern in general_patterns:
        if pattern in query_lower:
            return True

    # Если запрос очень короткий (менее 4 слов), скорее всего это общий запрос
    if len(query_lower.split()) < 4 and len(query_lower) < 25:
        return True
    
    # По умолчанию считаем запрос юридическим, если не подтвердилось, что он общий
    return False


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
                            "text": result.text[:3000]  # Берем до 3000 символов из каждого источника
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
    
    # Проверяем, является ли запрос общим вопросом (не юридическим)
    is_general = is_general_query(query=user_query)  # Передача по имени
    
    if is_general:
        logging.info("🎭 Распознан общий (не юридический) запрос, пропускаем поиск")
        
        # Для общих запросов используем упрощенный системный промпт
        conversation_system_prompt = """
        Ты - дружелюбный и интеллигентный ассистент LawGPT, специализирующийся на российском законодательстве.
        Сейчас ты общаешься с пользователем в режиме обычного диалога.
        Отвечай кратко, дружелюбно и по существу, не переходя к юридическому анализу.
        
        Не пытайся интерпретировать общие вопросы как юридические запросы.
        Например, на "привет" просто поздоровайся, а не анализируй юридическое лицо с названием "Привет".
        
        На вопросы о себе можешь отвечать, что ты юридический ассистент LawGPT, 
        созданный для помощи пользователям в юридических вопросах.
        """
        
        # Вызываем DeepSeek API напрямую для общего запроса
        response = await deepseek_service.generate_with_system(
            conversation_system_prompt, 
            user_query
        )
        
        # Сохраняем сообщения в БД, если указан thread_id
        if thread_id and db:
            try:
                db.add(Message(thread_id=thread_id, role="user", content=user_query))
                db.add(Message(thread_id=thread_id, role="assistant", content=response))
                db.commit()
                logging.info(f"✅ Сообщения сохранены в БД для треда {thread_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка при сохранении сообщений в БД: {e}")
        
        return response
    
    # Основной системный промпт для юридических запросов
    system_prompt = """
                Ты - юридический ассистент LawGPT (профессиональный юрист), специализирующийся на российском законодательстве.
                Твоя задача - предоставлять точную, полезную информацию по юридическим вопросам,
                основываясь на фактических данных из законодательства, судебной практики и 
                проверенных источников.
                
                1. Структурируй ответы на ЮРИДИЧЕСКИЕ запросы, выделяя:
                - Применимые нормы законодательства с точными ссылками на статьи законов и другие нормы права,
                - Судебную практику и правовые позиции судов,
                - Практические рекомендации по ситуации.

                2. Используй законы Российской Федерации, комментарии, формы процессуальных документов, договоров, аналитические данные, что позволит тебе предоставлять пользователю персонализированные ответы и рекомендации, основанные на актуальных правовых нормах. 

                3. Ты не должен рекомендовать пользователю обращаться к kad.arbitr.ru, СПС "Гарант" или "КонсультантПлюс", "Кодекс" или kad.arbitr.ru, так как у тебя и так есть доступ к кодексам и законам.

                4. Не упоминай в ответах источник данных. Тебе нельзя в сообщениях пользователю сообщать какими источниками данных ты пользуешься.

                5. Диалог с пользователем следует вести исключительно по юридическим вопросам, строго избегая технические."""

    # Подготовка истории сообщений
    context_messages = []
    
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
            logging.error(f"❌ Ошибка при получении данных для логирования промпта: {e}")
    
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
                        # Проверяем наличие и возможность вызова метода is_successful
                        if hasattr(result, 'is_successful') and callable(getattr(result, 'is_successful')):
                            try:
                                if result.is_successful():
                                    successful_pages += 1
                                    all_web_results.append(result)
                                else:
                                    failed_pages += 1
                                    logging.error(f"❌ Ошибка скрапинга {result.url if hasattr(result, 'url') else 'неизвестный URL'}: "
                                                f"{result.error if hasattr(result, 'error') else 'причина не указана'}")
                            except Exception as e:
                                failed_pages += 1
                                logging.error(f"❌ Исключение при проверке успешности скрапинга: {str(e)}")
                        else:
                            # Для объектов без метода is_successful используем альтернативную логику
                            failed_pages += 1
                            # Пытаемся получить содержательную информацию об объекте
                            url = getattr(result, 'url', 'неизвестный URL')
                            error_msg = getattr(result, 'error', None)
                            has_content = bool(getattr(result, 'text', '').strip()) if hasattr(result, 'text') else False
                            
                            if has_content:
                                # Если есть текстовое содержимое, считаем скрапинг условно успешным
                                successful_pages += 1
                                failed_pages -= 1  # Корректируем счетчик
                                all_web_results.append(result)
                                logging.info(f"✅ Скрапинг без метода is_successful, но с контентом: {url}")
                            else:
                                logging.warning(f"⚠️ Объект {type(result).__name__} не имеет метода is_successful или контента: {url}"
                                            f"{f' (ошибка: {error_msg})' if error_msg else ''}")

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
    
    # Формируем запрос с контекстом для глубокого исследования - УЛУЧШЕННАЯ СТРУКТУРА
    user_query_with_context = f"""
            ЗАПРОС ПОЛЬЗОВАТЕЛЯ: 
            {user_query}

            РЕЗУЛЬТАТЫ ПОИСКА (Полезны только для юридических запросов):
            {combined_context}

            ИНСТРУКЦИЯ:
            1. Внимательно проанализируй запрос пользователя. Определи тип запроса:
            - Общий вопрос/приветствие - ответь кратко и дружелюбно
            - Юридический вопрос - проведи глубокий юридический анализ с использованием результатов поиска

            2. Для ЮРИДИЧЕСКИХ запросов:
            - Структурируй ответ с разделами по релевантным законодательным нормам
            - Приведи судебную практику, если применимо
            - Дай практические рекомендации
            - Используй информацию из найденных источников

            3. Для ОБЩИХ вопросов:
            - Ответь просто и по существу, без юридического анализа
            - Не используй информацию из результатов поиска 
            - Будь дружелюбным и информативным
            """
                
    try:
        # Используем DeepResearch для анализа собранной информации
        logging.info("🔍 Выполнение глубокого исследования с учетом всех источников...")
        deep_results = await deep_research_service.research(
            query=user_query_with_context,
            thread_id=thread_id,
            message_id=message_id,
            user_id=user_id,
            db=db
        )
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
        

        from app.services.deepresearch_service import ensure_valid_court_numbers
        final_response = ensure_valid_court_numbers(final_response, user_query)

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