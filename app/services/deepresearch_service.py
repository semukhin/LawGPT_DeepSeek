import re
import os
import sys
import json
import asyncio
import aiohttp
import logging
import re  # Добавлен импорт для регулярных выражений
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime
from app.handlers.user_doc_request import extract_text_from_any_document
from app.handlers.deepresearch_audit import audit_deepresearch, deepresearch_audit
from app.services.deepseek_service import DeepSeekService
from app.models import PromptLog  # Импорт модели для логов промптов
from sqlalchemy.orm import Session
from app import models

# Импортируем настройки из config.py
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

# 📂 Добавление пути к third_party для корректного импорта shandu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)

# Улучшенная конфигурация логгера для детальной информации
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)

def highlight_court_numbers(query: str) -> str:
    """
    Выделяет номера судебных дел в запросе с учетом различных форматов российских судов.
    """
    """Заглушка для функции выделения номеров судебных дел"""
    return query


def validate_court_numbers(response: str, original_query: str) -> str:
    """Заглушка для функции валидации номеров судебных дел"""
    return response

def ensure_valid_court_numbers(answer: str, original_query: str) -> str:
    """Заглушка для функции финальной проверки номеров дел"""
    return answer

class ResearchResult:
    """Контейнер для результатов исследования."""
    
    def __init__(self, query: str, analysis: str, timestamp: str, error: Optional[str] = None):
        self.query = query
        self.analysis = analysis
        self.timestamp = timestamp
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует результат в словарь."""
        return {
            "query": self.query,
            "analysis": self.analysis,
            "timestamp": self.timestamp,
            "error": self.error
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Сохраняет результат в файл."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

class DeepResearchService:
    """
    Сервис для глубокого исследования юридических вопросов.
    Комбинирует возможности Shandu и DeepSeek API для анализа.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Инициализирует сервис с настройками для сохранения результатов.
        
        Args:
            output_dir: Директория для сохранения результатов исследований.
        """
        self.output_dir = output_dir or "research_results"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Инициализируем DeepSeek сервис
        self.deepseek_service = DeepSeekService(
            api_key=DEEPSEEK_API_KEY,
            model=DEEPSEEK_MODEL,
            temperature=1.0, 
            max_tokens=8192,
            timeout=120
        )
            
        logging.info(f"DeepResearchService инициализирован. Директория для результатов: {self.output_dir}")
        
        # Счетчик использования для отладки
        self.usage_counter = 0

    def filter_suspicious_court_numbers(self, text: str) -> str:
        """Заглушка для функции фильтрации подозрительных номеров судебных дел"""
        return text
        

        # Функция для проверки на последовательные цифры
    def is_general_query(self, query: str) -> bool:
        """
        Определяет, является ли запрос общим (не юридическим).
        
        Args:
            query: Текст запроса
            
        Returns:
            True, если запрос общий, False, если юридический
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

    @audit_deepresearch
    async def research(self, query: str, additional_context: Optional[List[Dict]] = None, thread_id: Optional[str] = None, message_id: Optional[int] = None, user_id: Optional[int] = None, db: Optional[Session] = None) -> ResearchResult:
        """
        Выполняет глубокий анализ запроса с использованием DeepSeek API.
        
        Args:
            query: Текст запроса или путь к файлу для анализа
            additional_context: Дополнительный контекст из других источников
            thread_id: ID треда, если запрос в рамках диалога
            message_id: ID сообщения пользователя
            user_id: ID пользователя
            db: Сессия базы данных
                    
        Returns:
            ResearchResult: Результат исследования в структурированном виде
        """
        self.usage_counter += 1
        logging.info(f"[DeepResearch #{self.usage_counter}] Начинаем исследование. Длина запроса: {len(query)} символов")
        
        # Обработка файлов, если query - путь к файлу
        if isinstance(query, str) and (query.endswith('.docx') or query.endswith('.pdf')):
            query = self.read_document(query) or query
            
        # Проверка структуры запроса для определения, есть ли в нем явное разделение
        # на запрос пользователя и результаты поиска
        if "ЗАПРОС ПОЛЬЗОВАТЕЛЯ:" in query and "РЕЗУЛЬТАТЫ ПОИСКА:" in query:
            # Запрос уже структурирован, извлекаем чистый запрос пользователя
            user_query_part = query.split("ЗАПРОС ПОЛЬЗОВАТЕЛЯ:")[1].split("РЕЗУЛЬТАТЫ ПОИСКА")[0].strip()
            is_general = self.is_general_query(user_query_part)

            # # Применяем highlight_court_numbers только к запросу пользователя, а не ко всему тексту
            # highlighted_user_query = highlight_court_numbers(user_query_part)
            
            # # Заменяем оригинальный запрос пользователя на подсвеченный, если он изменился
            # if highlighted_user_query != user_query_part:
            #     query = query.replace(
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_query_part}",
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{highlighted_user_query}"
            #     )
            #     # На случай другого форматирования
            #     query = query.replace(
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ: \n{user_query_part}",
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ: \n{highlighted_user_query}"
            #     )
            #     # И третий вариант без переносов
            #     query = query.replace(
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {user_query_part}",
            #         f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {highlighted_user_query}"
            #     )
        else:
            is_general = self.is_general_query(query)
# Не применяем highlight_court_numbers ко всему тексту,
            # так как в нем может быть системный промпт с примерами
            # Вместо этого логируем предупреждение
            logging.warning("Запрос не содержит структурированные части, пропускаем обработку номеров судебных дел")


        # Получаем историю сообщений, если есть thread_id и db
        chat_history = []
        if thread_id and db:
            try:
                from app.models import Message
                # Получаем последние 5 сообщений из треда, сортируя по дате создания
                messages = db.query(Message).filter(
                    Message.thread_id == thread_id
                ).order_by(Message.created_at.desc()).limit(5).all()
                
                # Переворачиваем список для хронологического порядка
                messages.reverse()
                
                # Логируем найденные сообщения
                logging.info(f"[DeepResearch #{self.usage_counter}] Найдено {len(messages)} предыдущих сообщений в треде {thread_id}")
                
                # Формируем историю сообщений в нужном формате
                for msg in messages:
                    chat_history.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None
                    })
            except Exception as e:
                logging.error(f"[DeepResearch #{self.usage_counter}] Ошибка при получении истории диалога: {str(e)}")
            
        # Определяем системный промпт на основе типа запроса
        if is_general:
            logging.info(f"[DeepResearch #{self.usage_counter}] Обнаружен общий (не юридический) запрос")
            system_prompt = """
            Ты - дружелюбный и интеллигентный ассистент LawGPT, специализирующийся на российском законодательстве.
            Сейчас ты общаешься с пользователем в режиме обычного диалога.
            
            Текущий запрос пользователя не связан с юридическими темами, это общий вопрос или приветствие.
            Отвечай кратко, дружелюбно и по существу, не переходя к юридическому анализу.
            
            Не пытайся интерпретировать общие вопросы как юридические запросы.
            Например, на "привет" просто поздоровайся, а не анализируй юридическое лицо с названием "Привет".
            
            На вопросы о себе можешь отвечать, что ты юридический ассистент LawGPT, 
            созданный для помощи пользователям в юридических вопросах.
            
            Учитывай контекст предыдущих сообщений из диалога.
            """
        else:
            # Основной системный промпт для юридических запросов
            system_prompt = """
                Ты - юридический ассистент LawGPT (профессиональный юрист), специализирующийся на российском законодательстве.
                Твоя задача - предоставлять точную, полезную информацию по юридическим вопросам, основываясь на фактических данных из 
                законодательства, судебной практики и проверенных источников.
                
                1. Структурируй ответы на ЮРИДИЧЕСКИЕ запросы.

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
            
        # Проверка структуры запроса для определения, есть ли в нем явное разделение
        # на запрос пользователя и результаты поиска
        if "ЗАПРОС ПОЛЬЗОВАТЕЛЯ:" in query and "РЕЗУЛЬТАТЫ ПОИСКА:" in query:
            # Запрос уже структурирован, проверяем наличие контекста диалога
            if "КОНТЕКСТ ПРЕДЫДУЩИХ СООБЩЕНИЙ:" not in query and chat_history:
                # Добавляем контекст диалога, если он есть, но не был добавлен ранее
                formatted_history = []
                for msg in chat_history:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    formatted_history.append(f"{role.upper()}: {content}")
                
                if formatted_history:
                    context_section = "\n\nКОНТЕКСТ ПРЕДЫДУЩИХ СООБЩЕНИЙ:\n" + "\n\n".join(formatted_history)
                    # Вставляем контекст после инструкции, если она есть
                    if "ИНСТРУКЦИЯ:" in query:
                        parts = query.split("ИНСТРУКЦИЯ:")
                        query = parts[0] + "ИНСТРУКЦИЯ:" + parts[1] + context_section
                    else:
                        query += context_section
            
            # Используем запрос как есть с добавленным контекстом
            user_prompt = query
        else:
            # Формируем пользовательский промпт
            user_prompt = f"Проведи детальный анализ запроса:\n\n{query}"
            
            # Добавляем контекст из предыдущих сообщений
            if chat_history:
                user_prompt += "\n\nКонтекст предыдущих сообщений:\n"
                for msg in chat_history:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    user_prompt += f"{role.upper()}: {content}\n\n"
            
            # Добавляем контекст из других источников, если он есть
            if additional_context:
                user_prompt += "\n\nДополнительная информация из других источников:\n"
                for ctx in additional_context:
                    source_type = ctx.get("type", "неизвестный источник")
                    if ctx.get("found"):
                        user_prompt += f"\n--- Из источника {source_type} ---\n"
                        if "data" in ctx:
                            if isinstance(ctx["data"], list):
                                for item in ctx["data"][:3]:  # Берем до 3 элементов
                                    user_prompt += f"{item[:1000]}...\n\n"
                            elif isinstance(ctx["data"], dict):
                                for key, value in ctx["data"].items():
                                    if key not in ["path", "error", "type"]:
                                        user_prompt += f"{value[:1000]}...\n\n"
                            else:
                                user_prompt += f"{str(ctx['data'])[:3000]}...\n\n"
        
        # Используем запрос без обработки номеров судебных дел
        enhanced_prompt = user_prompt
                
        # Сохраняем промпт в базу данных после того как определили системный промпт и пользовательский запрос
        if db is not None and thread_id is not None and user_id is not None:
            try:
                # Проверяем схему таблицы prompt_logs на наличие столбца message_id
                from sqlalchemy import inspect
                inspector = inspect(db.get_bind())
                try:
                    columns = [col['name'] for col in inspector.get_columns('prompt_logs')]
                    has_message_id = 'message_id' in columns
                except Exception:
                    has_message_id = False
                    
                # Подготавливаем данные для записи в таблицу
                prompt_data = {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "system_prompt": system_prompt,  # Теперь system_prompt уже определен
                    "user_prompt": enhanced_prompt    # И enhanced_prompt тоже
                }
                
                # Добавляем message_id только если столбец существует и значение не None
                if has_message_id and message_id is not None:
                    prompt_data["message_id"] = message_id
                
                # Создаем запись с нужными полями
                prompt_log = models.PromptLog(**prompt_data)
                db.add(prompt_log)
                db.commit()
                logging.info(f"✅ Промпт сохранен в БД для треда {thread_id}")
            except Exception as e:
                # Откатываем транзакцию и логируем ошибку
                try:
                    db.rollback()
                except Exception:
                    pass  # Игнорируем ошибки при откате
                logging.error(f"❌ Ошибка при сохранении промпта: {e}")
        
        try:
            # Запрос к DeepSeek API с правильным системным промптом
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Заменить блок с добавлением истории сообщений (строки 500-508) на следующий код:

            # Добавляем историю сообщений, чтобы обеспечить строгое чередование user/assistant
            if chat_history:
                # Обеспечиваем правильное чередование сообщений
                interleaved_messages = []
                previous_role = None
                
                for msg in chat_history:
                    current_role = msg.get("role")
                    
                    # Пропускаем сообщения, нарушающие чередование
                    if current_role == previous_role:
                        logging.info(f"[DeepResearch #{self.usage_counter}] Пропускаем последовательное сообщение с ролью {current_role}")
                        continue
                        
                    # Добавляем сообщение, если роль валидна для API
                    if current_role in ["user", "assistant"]:
                        interleaved_messages.append(msg)
                        previous_role = current_role
                
                # Если история начинается с сообщения assistant, удаляем его
                if interleaved_messages and interleaved_messages[0].get("role") == "assistant":
                    logging.info(f"[DeepResearch #{self.usage_counter}] Удаляем первое сообщение с ролью assistant")
                    interleaved_messages = interleaved_messages[1:]
                
                # Если последнее сообщение от assistant, а мы собираемся добавить user message,
                # удаляем его, чтобы предотвратить последовательные user сообщения
                if interleaved_messages and interleaved_messages[-1].get("role") == "assistant":
                    # Если текущий запрос от пользователя, то нужно удалить последнее сообщение assistant
                    pass  # Оставляем последнее сообщение assistant, это правильное чередование
                elif interleaved_messages and interleaved_messages[-1].get("role") == "user":
                    # Если последнее сообщение от user, а следующее тоже будет от user, удаляем последнее
                    logging.info(f"[DeepResearch #{self.usage_counter}] Удаляем последнее сообщение user для обеспечения чередования")
                    interleaved_messages = interleaved_messages[:-1]
                
                # Добавляем отфильтрованные сообщения истории в messages
                for msg in interleaved_messages:
                    messages.append({
                        "role": msg.get("role"),
                        "content": msg.get("content", "")
                    })
                
                # Проверяем, что последнее сообщение не от user перед добавлением текущего запроса
                if messages and messages[-1].get("role") == "user":
                    # Удаляем последнее сообщение, чтобы избежать последовательных user сообщений
                    logging.info(f"[DeepResearch #{self.usage_counter}] Удаляем последнее сообщение перед добавлением текущего запроса")
                    messages.pop()
            
            # Добавляем текущий запрос пользователя
            messages.append({"role": "user", "content": enhanced_prompt})
            
            # Логируем количество сообщений для диагностики
            logging.info(f"[DeepResearch #{self.usage_counter}] Отправка {len(messages)} сообщений в API, включая системное")
            
            # Прямой и единственный запрос к API
            url = f"{self.deepseek_service.api_base}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_service.api_key}"
            }
            payload = {
                "model": self.deepseek_service.model,
                "messages": messages,
                "temperature": self.deepseek_service.temperature,
                "max_tokens": self.deepseek_service.max_tokens
            }
            
            logging.info("Отправка запроса к DeepSeek API")
            
            # Единственный запрос с фиксированным таймаутом 120 секунд
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Ошибка DeepSeek API ({response.status}): {error_text}")
                        analysis = f"Ошибка API: {response.status} - {error_text}"
                    else:
                        response_json = await response.json()
                        if 'choices' in response_json and len(response_json['choices']) > 0:
                            analysis = response_json['choices'][0]['message']['content']
                            
                            # # Валидация номеров судебных дел в ответе
                            # analysis = validate_court_numbers(analysis, query)
                        else:
                            analysis = "Не удалось получить ответ от API DeepSeek"
            
            # Формируем структурированный результат
            result = ResearchResult(
                query=query[:1000] + "..." if len(query) > 3000 else query,
                analysis=analysis,
                timestamp=self._get_current_time()
            )
            
            # Сохраняем результат если указана директория
            if self.output_dir:
                result_filename = f"research_{self.usage_counter}_{self._get_timestamp()}.json"
                result_path = os.path.join(self.output_dir, result_filename)
                result.save_to_file(result_path)
            
            return result
                
        except Exception as e:
            error_msg = f"Ошибка при исследовании: {str(e)}"
            logging.error(f"[DeepResearch #{self.usage_counter}] {error_msg}")
            return ResearchResult(
                query=query[:5000] + "..." if len(query) > 5000 else query,
                analysis=f"Произошла ошибка при выполнении исследования: {str(e)}",
                timestamp=self._get_current_time(),
                error=str(e)
            )
        
    @audit_deepresearch
    def read_document(self, file_path: str) -> Optional[str]:
        """
        Извлекает текст из документа.
            
        Args:
            file_path: Путь к документу
                    
        Returns:
            Текстовое содержимое документа или None в случае ошибки
        """
        try:
            logging.info(f"[DeepResearch #{self.usage_counter}] Извлечение текста из документа: {file_path}")
            extracted_text = extract_text_from_any_document(file_path)
                
            if extracted_text:
                logging.info(f"[DeepResearch #{self.usage_counter}] Успешно извлечен текст ({len(extracted_text)} символов)")
                # Если текст слишком большой, обрезаем его
                max_length = 50000  # Примерный лимит для моделей
                if len(extracted_text) > max_length:
                    extracted_text = extracted_text[:max_length] + "...[текст обрезан из-за ограничений размера]"
                        
                return extracted_text
                
            return None
        except Exception as e:
            logging.error(f"[DeepResearch #{self.usage_counter}] Ошибка при извлечении текста из документа {file_path}: {str(e)}")
            return None  

    @audit_deepresearch
    def _get_timestamp(self) -> str:
        """Возвращает текущую метку времени в формате для имен файлов."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
    @audit_deepresearch
    def _get_current_time(self) -> str:
        """Возвращает текущее время в ISO формате."""
        return datetime.now().isoformat()