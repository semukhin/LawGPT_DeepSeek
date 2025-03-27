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
from app.utilities import measure_time
from app.handlers.es_law_search import search_law_chunks
from app.handlers.web_search import google_search, search_and_scrape, run_multiple_searches
from app.services.deepresearch_service import DeepResearchService
from app.services.deepseek_service import DeepSeekService
from app.models import Message, Thread
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from app.context_manager import ContextManager

# Инициализация сервисов
deep_research_service = DeepResearchService()
deepseek_service = DeepSeekService(
    api_key=DEEPSEEK_API_KEY, 
    model=DEEPSEEK_MODEL,
    temperature=1.2
)

# Инициализация менеджера контекста
context_manager = ContextManager(model=DEEPSEEK_MODEL)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Добавить в начало файла
MAX_PROMPT_CHARS = 20000  # Максимальная длина итогового промта
MAX_SEARCH_RESULTS_CHARS = 6000  # Лимит на результаты поиска
MAX_ES_RESULT_CHARS = 1000  # Лимит на один фрагмент из ElasticSearch
MAX_WEB_RESULT_CHARS = 1800  # Лимит на один веб-результат


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
        "закон", "кодекс", "статья", "договор", "иск", "223-ФЗ", "44-ФЗ", "44 фз", "указ", "постановление", "суд", "право", "юрист", 
        "норма", "регулирован", "законодательств", "ответственност", "штраф", "приговор"
        "обязательств", "претензи", "вина", "устав", "соглашение", "гк", "гпк", "кас", "115-ФЗ",
        "налог", "юрлицо", "физлиц", "гражданин", "организаци", "фгуп", "праве", "УК РФ", "Уголовный кодекс", "пристава"
        "аренда", "залог", "недвижимость", "сделка", "наследство", "правомочия", "умысел",
        "акционер", "дивиденды", "правонарушение", "преступление", "имущество", "арбитраж", "астрент",
        "оферта", "акцепт", "нотариус", "доверенность", "представительство", "компенсации", "возмещение", "взыскание"
        "банкротство", "ликвидация", "реорганизация", "выписка", "егрюл", "ооо", "оао", "оао",
        "капитал", "учредитель", "предприниматель", "ип", "ао", "регистрац", "лиценз",
        "санкц", "арбитраж", "истец", "ответчик", "апелляц", "кассац", "имуществ", "сво", "решение",
        "214-ФЗ", "229-ФЗ", "230-ФЗ", "259-ФЗ", "263-ФЗ", "290-ФЗ", "353-ФЗ", "44-ФЗ", "94-ФЗ", "115-ФЗ",
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
    
    # В функции send_custom_request для общих запросов:

    if is_general:
        logging.info("🎭 Распознан общий (не юридический) запрос, пропускаем поиск")
        
        # Для общих запросов используем упрощенный системный промпт
        system_prompt = """
        Ты - дружелюбный и интеллигентный юридический ассистент LawGPT, специализирующийся на российском законодательстве.
        Сейчас ты общаешься с пользователем в режиме обычного диалога.
        Отвечай кратко, дружелюбно и по существу, не переходя к юридическому анализу.
        
        Не пытайся интерпретировать общие вопросы как юридические запросы.
        Например, на "привет" просто поздоровайся, а не анализируй юридическое лицо с названием "Привет".
        
        На вопросы о себе можешь отвечать, что ты юридический ассистент LawGPT, 
        созданный для помощи пользователям в юридических вопросах.
        """
        
        # Получаем историю диалога
        chat_history = []
        if thread_id and db:
            try:
                # Получаем последние сообщения из треда (ограничиваем 10 сообщениями)
                messages = db.query(Message).filter(
                    Message.thread_id == thread_id
                ).order_by(Message.created_at).all()
                
                # Обеспечиваем правильное чередование сообщений
                previous_role = None
                for msg in messages:
                    # Пропускаем сообщения, нарушающие чередование
                    if msg.role == previous_role:
                        logging.info(f"Пропускаем последовательное сообщение с ролью {msg.role}")
                        continue
                        
                    chat_history.append({"role": msg.role, "content": msg.content})
                    previous_role = msg.role
                    
                # Если история начинается с сообщения assistant, удаляем его
                if chat_history and chat_history[0]["role"] == "assistant":
                    logging.info("Удаляем первое сообщение с ролью assistant")
                    chat_history = chat_history[1:]
                    
                logging.info(f"📝 Загружено {len(chat_history)} предыдущих сообщений из треда после фильтрации")
            except Exception as e:
                logging.error(f"❌ Ошибка при загрузке истории сообщений: {str(e)}")
        
        # Формируем сообщения с историей
        all_messages = []
        
        # Добавляем системный промпт
        all_messages.append({"role": "system", "content": system_prompt})
        
        # Добавляем историю диалога
        for msg in chat_history:
            all_messages.append(msg)
            
        # Проверяем, что последнее сообщение не от user перед добавлением текущего запроса
        if chat_history and chat_history[-1]["role"] == "user":
            # Удаляем последнее сообщение, чтобы избежать последовательных user сообщений
            logging.info("Удаляем последнее сообщение пользователя для обеспечения чередования")
            all_messages.pop()
            
        # Добавляем текущий запрос пользователя
        all_messages.append({"role": "user", "content": user_query})
        
        # Логируем последовательность сообщений для отладки
        roles_sequence = [msg["role"] for msg in all_messages]
        logging.info(f"Финальная последовательность ролей сообщений: {roles_sequence}")
        
        # Вызываем DeepSeek API с полной историей диалога
        response = await deepseek_service.chat_completion(all_messages)
        
        # Извлекаем ответ из результата
        if isinstance(response, dict) and 'choices' in response and len(response['choices']) > 0:
            assistant_response = response['choices'][0]['message']['content']
        else:
            assistant_response = "Извините, произошла ошибка при обработке запроса."
        
        # Сохраняем сообщения в БД, если указан thread_id
        if thread_id and db:
            try:
                db.add(Message(thread_id=thread_id, role="user", content=user_query))
                db.add(Message(thread_id=thread_id, role="assistant", content=assistant_response))
                db.commit()
                logging.info(f"✅ Сообщения сохранены в БД для треда {thread_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка при сохранении сообщений в БД: {e}")
        
        return assistant_response       
    
    # Основной системный промпт для юридических запросов
    system_prompt = """
                Ты - юридический ассистент LawGPT (профессиональный юрист), специализирующийся на российском законодательстве.
                Твоя задача - предоставлять точную, полезную информацию по юридическим вопросам, основываясь на фактических данных из 
                законодательства, судебной практики и проверенных источников.
                
                1. Структурируй ответы на запросы пользователя.

                2. Используй законы Российской Федерации, комментарии, формы процессуальных документов, договоров, аналитические данные, 
                что позволит тебе предоставлять пользователю персонализированные ответы и рекомендации, основанные на актуальных правовых нормах. 

                3. Ты не должен рекомендовать пользователю обращаться к kad.arbitr.ru, СПС "Гарант" или "КонсультантПлюс", "СудАкт" (sudact.ru) или "Кодекс".

                4. Не упоминай в ответах источник данных. Тебе нельзя в сообщениях пользователю сообщать какими источниками данных ты пользуешься.

                5. Диалог с пользователем следует вести исключительно по юридическим вопросам, строго избегая технические.

                
                ***ВАЖНЫЕ ПРАВИЛА ПО РАБОТЕ С НОМЕРАМИ СУДЕБНЫХ ДЕЛ:***

                1. ИСПОЛЬЗУЙ ТОЛЬКО номера судебных дел, которые ЯВНО указаны в промте или запросе пользователя.
                
                2. НИКОГДА не придумывай и не создавай номера судебных дел самостоятельно. 
                
                3. Если в запросе (промте) или в результатах поиска указан номер судебногодела, ОБЯЗАТЕЛЬНО используй ИМЕННО ЭТОТ номер в ответе без изменений.
                 
                4. Проверяй каждый номер дела в своем ответе - он должен ТОЧНО соответствовать номеру из исходных материалов. 
                Не выдумывай не существующие номера судебных дел, а используй только те номера которые тебе поступили с промтом.
             
                5. При цитировании судебной практики ВСЕГДА указывай ТОЧНЫЙ номер дела из источника (источник в промте).
                
                6. Учитывай контекст предыдущих сообщений в диалоге при формировании ответа.
                """

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
            logging.info("🔍 Выполнение поиска в ElasticSearch для запроса: '%s'", user_query)
            es_results = search_law_chunks(user_query)
            if es_results:
                logging.info(f"✅ Найдено {len(es_results)} релевантных чанков в ElasticSearch")
                
                # Отформатируем результаты с ограничением размера
                formatted_results = "\n\n## Российское законодательство:\n\n"
                total_size = len(formatted_results)
                
                # Ограничиваем количество результатов до 5 наиболее релевантных
                limited_results = es_results[:5]
                
                for chunk in limited_results:
                    chunk_text = f"{chunk}\n\n---\n\n"
                    
                    # Проверяем, не превысим ли лимит
                    if total_size + len(chunk_text) > MAX_SEARCH_RESULTS_CHARS:
                        # Обрезаем фрагмент, если он превышает лимит
                        available_size = MAX_SEARCH_RESULTS_CHARS - total_size
                        truncated_chunk = chunk[:available_size] + "..."
                        chunk_text = f"{truncated_chunk}\n\n---\n\n"
                        formatted_results += chunk_text
                        break
                    
                    formatted_results += chunk_text
                    total_size += len(chunk_text)
                
                return formatted_results
            return ""
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в ElasticSearch: {str(e)}")
            return ""
        

    # 2. Функция поиска в интернете (всегда выполняем)
    async def search_internet():
        try:
            logging.info("🔍 Выполнение поиска в интернете для запроса: '%s'", user_query)
            
            # Ограничиваем количество ссылок до 3
            web_results = await search_and_scrape(user_query, logs, max_results=3, force_refresh=False)
            
            if web_results:
                formatted_results = "\n\n## Интернет-источники:\n\n"
                total_size = len(formatted_results)
                
                for i, result in enumerate(web_results, 1):
                    if result.is_successful():
                        source_text = f"### Источник {i}: {result.title}\n"
                        source_text += f"URL: {result.url}\n\n"
                        source_text += f"{result.text}\n\n---\n\n"
                        
                        # Проверяем, не превысим ли лимит
                        if total_size + len(source_text) > MAX_SEARCH_RESULTS_CHARS:
                            # Обрезаем текст, если он превышает лимит
                            available_size = MAX_SEARCH_RESULTS_CHARS - total_size
                            truncated_text = result.text[:available_size] + "..."
                            source_text = f"### Источник {i}: {result.title}\n"
                            source_text += f"URL: {result.url}\n\n"
                            source_text += f"{truncated_text}\n\n---\n\n"
                            formatted_results += source_text
                            break
                        
                        formatted_results += source_text
                        total_size += len(source_text)
                
                return formatted_results
            return ""
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в интернете: {str(e)}")
            return ""
    
    # 3. Запускаем все поиски параллельно
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
    
    # 6. Сначала получаем форматированную историю диалога (до определения max_context_size)
    chat_history_formatted = ""
    if thread_id and db:
        try:
            # Получаем сообщения из треда (не больше 10 для контекста)
            messages = db.query(Message).filter(
                Message.thread_id == thread_id
            ).order_by(Message.created_at).all()
            
            if messages:
                # Обеспечиваем правильное чередование сообщений
                chat_history = []
                previous_role = None
                
                for msg in messages:
                    # Пропускаем только последовательные сообщения от пользователя
                    if msg.role == "user" and msg.role == previous_role:
                        continue
                        
                    chat_history.append(msg)
                    previous_role = msg.role
                
                # Если история начинается с сообщения assistant, удаляем его
                if chat_history and chat_history[0].role == "assistant":
                    chat_history = chat_history[1:]
                    
                # Переворачиваем порядок, чтобы восстановить хронологию
                chat_history.reverse()
                
                logging.info(f"📝 Загружено {len(chat_history)} предыдущих сообщений из треда после фильтрации")
                
                # Форматируем историю диалога
                formatted_history = []
                for msg in chat_history:
                    role = "ПОЛЬЗОВАТЕЛЬ" if msg.role == "user" else "АССИСТЕНТ"
                    formatted_history.append(f"{role}: {msg.content[:500]}...")
                
                if formatted_history:
                    chat_history_formatted = "\n\n".join(formatted_history)
                    logging.info(f"✅ История диалога добавлена в контекст")
        except Exception as e:
            logging.error(f"❌ Ошибка при загрузке истории сообщений: {str(e)}")
    
    # Определяем максимальный размер запроса
    max_query_size = 2000  # Ограничение на размер изначального запроса
    query_truncated = user_query
    if len(user_query) > max_query_size:
        query_truncated = user_query[:max_query_size] + "..."

    # Расчет оставшегося места для контекста поиска
    prompt_header = f"""
            ЗАПРОС ПОЛЬЗОВАТЕЛЯ: 
            {query_truncated}

            РЕЗУЛЬТАТЫ ПОИСКА (Полезны только для юридических запросов):
            """
            
    prompt_footer = f"""
            ИНСТРУКЦИЯ:
            1. Внимательно проанализируй запрос пользователя и контекст предыдущих сообщений. Определи тип запроса:
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

            4. Используй контекст предыдущих сообщений для формирования связного и последовательного ответа.
            """

    # Ограничиваем общий размер промта 
    max_context_size = MAX_PROMPT_CHARS - len(prompt_header) - len(prompt_footer)

    # Обрезаем результаты поиска, если они слишком большие
    if len(combined_context) > max_context_size:
        combined_context = combined_context[:max_context_size] + "\n\n... (результаты поиска сокращены из-за ограничений размера)"

    # Добавляем историю чата в контекст после определения max_context_size
    if chat_history_formatted:
        combined_context += f"\n\n## КОНТЕКСТ ПРЕДЫДУЩЕГО ДИАЛОГА:\n\n{chat_history_formatted}\n\n"

    user_query_with_context = prompt_header + combined_context + prompt_footer
                
    try:
        # Формируем сообщения для DeepSeek
        all_messages = []

        # Добавляем системный промпт
        all_messages.append({"role": "system", "content": system_prompt})
        
        # Получаем историю диалога для DeepSeek
        chat_history = []
        if thread_id and db:
            try:
                # Получаем последние сообщения из треда
                messages = db.query(Message).filter(
                    Message.thread_id == thread_id
                ).order_by(Message.created_at).all()
                
                # Обеспечиваем правильное чередование сообщений
                previous_role = None
                for msg in messages:
                    # Пропускаем сообщения, нарушающие чередование
                    if msg.role == previous_role:
                        logging.info(f"Пропускаем последовательное сообщение с ролью {msg.role}")
                        continue
                        
                    chat_history.append({"role": msg.role, "content": msg.content})
                    previous_role = msg.role
                    
                # Если история начинается с сообщения assistant, удаляем его
                if chat_history and chat_history[0]["role"] == "assistant":
                    logging.info("Удаляем первое сообщение с ролью assistant")
                    chat_history = chat_history[1:]
                    
                logging.info(f"📝 Загружено {len(chat_history)} предыдущих сообщений для DeepSeek")
            except Exception as e:
                logging.error(f"❌ Ошибка при загрузке истории сообщений для DeepSeek: {str(e)}")

        # Добавляем историю диалога
        for msg in chat_history:
            all_messages.append(msg)
            
        # Проверяем, что последнее сообщение не от user перед добавлением текущего запроса
        if chat_history and chat_history[-1]["role"] == "user":
            # Удаляем последнее сообщение, чтобы избежать последовательных user сообщений
            logging.info("Удаляем последнее сообщение пользователя для обеспечения чередования")
            all_messages.pop()
            
        # Добавляем текущий запрос пользователя
        all_messages.append({"role": "user", "content": user_query})

        # Логируем последовательность сообщений для отладки
        roles_sequence = [msg["role"] for msg in all_messages]
        logging.info(f"Финальная последовательность ролей сообщений: {roles_sequence}")

        # Используем DeepResearch для анализа собранной информации
        logging.info("🔍 Выполнение глубокого исследования с учетом всех источников и контекста диалога...")
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