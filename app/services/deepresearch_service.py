import re
import os
import sys
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, Any, List, Union, AsyncGenerator
from pathlib import Path
from datetime import datetime
from app.handlers.user_doc_request import extract_text_from_any_document
from app.handlers.es_law_search import search_law_chunks
from app.services.tavily_service import TavilyService
from app.services.deepseek_service import DeepSeekService
from app.models import PromptLog  # Импорт модели для логов промптов
from sqlalchemy.orm import Session
from app import models
from app.handlers.parallel_search import run_parallel_search  # Добавляем импорт
from app.services.web_scraper import WebScraper
from app.services.db_service import DBService
from app.handlers.web_search import WebSearchHandler
from app.utils import ensure_correct_encoding  # Добавляем импорт
from app.utils.logger import EnhancedLogger, LogLevel, get_logger
import types

# Импортируем настройки из config.py
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

# Системные промпты
GENERAL_SYSTEM_PROMPT = """
    Ты - дружелюбный и интеллигентный ассистент LawGPT.
    Сейчас ты общаешься с пользователем в режиме обычного диалога.
    
    ВАЖНО: На общие вопросы и приветствия отвечай КРАТКО и ДРУЖЕЛЮБНО, 
    НЕ упоминая юридическую тематику и законодательство.    
"""

LEGAL_SYSTEM_PROMPT = """
                Ты - юридический ассистент LawGPT, высококвалифицированный эксперт в области российского права. 
                Твоя задача - предоставлять точную, обоснованную и практически применимую юридическую информацию в соответствии с актуальным законодательством РФ.

                **КЛЮЧЕВЫЕ ПРИНЦИПЫ РАБОТЫ:**

                1. ТОЧНОСТЬ И АКТУАЛЬНОСТЬ: При анализе вопроса пользователя учитывай актуальные нормы права, включая последние изменения в законодательстве.

                2. ПРАВОВОЕ ОБОСНОВАНИЕ: Каждый тезис в твоем ответе должен опираться на конкретные нормы права (статьи законов, постановления пленумов ВС РФ, определения судов). 

                3. СТРУКТУРИРОВАННОСТЬ: Организуй ответ в логической последовательности:
                    Краткое юридическое резюме ситуации,
                    Анализ применимых правовых норм,
                    Обязательно процитируй найденные номера дел и реквизиты судебных актов,
                    Конкретные рекомендации и алгоритм действий,
                    Возможные правовые риски и их минимизация,
                    Выводы (1-3 предложения).

                4. ПРАКТИЧЕСКАЯ НАПРАВЛЕННОСТЬ: Предлагай конкретные правовые механизмы решения проблемы с указанием процессуальных сроков, подсудности, формы и содержания необходимых документов.

                
                **ПРАВИЛА РАБОТЫ С ДОКУМЕНТАМИ И ИСТОЧНИКАМИ:**
                    1. СУДЕБНАЯ ПРАКТИКА:
                        Используй ТОЛЬКО номера судебных дел, ЯВНО указанные в запросе пользователя или найденные в результатах поиска
                        НИКОГДА не придумывай номера дел самостоятельно
                        При цитировании практики указывай полные реквизиты: номер дела, наименование суда, дату принятия решения

                    2. ЗАКОНОДАТЕЛЬСТВО:
                        При ссылке на нормативные акты указывай полное название, номер и дату принятия закона,
                        Корректно цитируй статьи законов, не искажая их смысл и содержание,
                        Учитывай иерархию нормативных актов (Конституция → федеральные конституционные законы → федеральные законы → указы Президента → постановления Правительства → ведомственные акты),
                        При наличии коллизий правовых норм указывай на это и объясняй принцип разрешения коллизии.

                    3. ДОГОВОРЫ И ДОКУМЕНТЫ:
                        При анализе договорных отношений учитывай принцип свободы договора и его ограничения
                        Предлагай формулировки условий с учетом судебной практики и типичных рисков
                        При рекомендации составления документов указывай их обязательные реквизиты и содержание.
        
                               
                **СТИЛЬ КОММУНИКАЦИИ:**
                    1. ПРОФЕССИОНАЛЬНЫЙ, но доступный для понимания неюристами
                    2. КОНКРЕТНЫЙ: избегай размытых формулировок и абстрактных рекомендаций
                    3. НЕПРЕДВЗЯТЫЙ: представляй различные правовые позиции по спорным вопросам
                    4. КОНФИДЕНЦИАЛЬНЫЙ: напоминай о необходимости сохранения конфиденциальности информации
                    5. ЭТИЧНЫЙ: не рекомендуй незаконные способы решения проблем

                **ВАЖНЫЕ ОГРАНИЧЕНИЯ:**
                    1. НЕ РЕКОМЕНДУЙ обращаться к внешним ресурсам (kad.arbitr.ru, "Гарант", "КонсультантПлюс", "СудАкт", "Кодекс")
                    2. НЕ УПОМИНАЙ источники данных, которыми ты пользуешься
                    3. НЕ ОТВЕЧАЙ на технические вопросы, не связанные с юриспруденцией
                    4. НЕ ВЫДУМЫВАЙ номера судебных дел и реквизиты документов
                    

                **ОСОБЫЕ ИНСТРУКЦИИ:**
                    1. Отвечай ТОЛЬКО на последний вопрос пользователя, если он не связан с предыдущими сообщениями в треде.
                    2. Если запрос пользователя содержит номер судебного дела, статьи закона или договора - используй эти реквизиты в ответе.
                    3. Если вопрос неясен или требует уточнения - запрашивай дополнительную информацию.
                    4. При наличии неоднозначных трактовок правовых норм - представляй все обоснованные подходы.
                    
        """

RESEARCH_SYSTEM_PROMPT = """
Ты — юридический ассистент LawGPT. Проанализируй предоставленные данные и дай структурированный, обоснованный юридический ответ согласно инструкциям.
"""

# 📂 Добавление пути к third_party для корректного импорта shandu
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
if THIRD_PARTY_DIR not in sys.path:
    sys.path.insert(0, THIRD_PARTY_DIR)

# Добавление констант для контроля размера
MAX_INPUT_QUERY_SIZE = 24000  # Увеличиваем лимит для входного запроса
MAX_ADDITIONAL_CONTEXT_SIZE = 32000  # Увеличиваем лимит на дополнительный контекст
MAX_SEARCH_RESULTS = 10  # Максимальное количество результатов поиска
MIN_RELEVANCE_SCORE = 0.6  # Минимальный порог релевантности

# Улучшенная конфигурация логгера для детальной информации
# logging.basicConfig(
#     level=logging.INFO,
#     format=
#     "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s")


def truncate_text_intelligently(text: str, max_length: int) -> str:
    """
    Умная обрезка текста, сохраняя наиболее информативные части.
    """
    if len(text) <= max_length:
        return text

    start_buffer = int(max_length * 0.05)
    end_buffer = int(max_length * 0.03)
    middle_buffer = max_length - start_buffer - end_buffer - 20

    paragraphs = text.split('\n\n')

    if len(paragraphs) <= 1:
        return text[:start_buffer] + "..." + text[-end_buffer:]

    start_text = ""
    for p in paragraphs:
        if len(start_text) + len(p) + 2 <= start_buffer:
            start_text += p + "\n\n"
        else:
            if len(start_text) < start_buffer:
                remaining = start_buffer - len(start_text)
                if remaining > 20:
                    start_text += p[:remaining] + "..."
            break

    end_text = ""
    for p in reversed(paragraphs):
        if len(end_text) + len(p) + 2 <= end_buffer:
            end_text = p + "\n\n" + end_text
        else:
            if len(end_text) < end_buffer:
                remaining = end_buffer - len(end_text)
                if remaining > 20:
                    end_text = "..." + p[-remaining:] + "\n\n" + end_text
            break

    if middle_buffer > 100:
        middle_start_index = len(start_text)
        middle_end_index = len(text) - len(end_text)
        middle_text = text[middle_start_index:middle_end_index]
        middle_paragraphs = middle_text.split('\n\n')
        selected_middle = ""
        middle_position = len(middle_paragraphs) // 2
        for i in range(max(0, middle_position - 1), min(len(middle_paragraphs), middle_position + 2)):
            if len(selected_middle) + len(middle_paragraphs[i]) + 2 <= middle_buffer:
                selected_middle += middle_paragraphs[i] + "\n\n"
            else:
                break
        return start_text + "\n...\n\n" + selected_middle + "\n...\n\n" + end_text

    return start_text + "\n...\n\n" + end_text


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

    def __init__(
        self,
        query: str,
        analysis: str,
        timestamp: Optional[str] = None,
        error: Optional[str] = None,
        reasoning_content: Optional[str] = None
    ):
        self.query = query
        self.analysis = analysis
        self.timestamp = timestamp
        self.error = error
        self.reasoning_content = reasoning_content

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует результат в словарь."""
        return {
            "query": self.query,
            "analysis": self.analysis,
            "timestamp": self.timestamp,
            "error": self.error,
            "reasoning_content": self.reasoning_content
        }

    def save_to_file(self, filepath: str) -> None:
        """Сохраняет результат в файл."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class PromptLogger:
    """Класс для сохранения логов и промптов в файлы"""
    
    def __init__(self, base_dir: Optional[str] = None):
        # Используем переданный base_dir или текущую директорию приложения
        if base_dir:
            self.base_dir = base_dir
        else:
            # Получаем путь к директории приложения
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.base_dir = app_dir
        
        # Используем существующие папки в корне приложения
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.prompts_dir = os.path.join(self.base_dir, 'prompts')
        self.responses_dir = os.path.join(self.base_dir, 'responses')
        
        # Создаем директории, если их нет
        for dir_path in [self.logs_dir, self.prompts_dir, self.responses_dir]:
            os.makedirs(dir_path, exist_ok=True)
            
        # Настраиваем логгер для файла
        self.file_handler = logging.FileHandler(
            os.path.join(self.logs_dir, f'log_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        self.file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(self.file_handler)
    
    def save_log(self, message: str, level: str = 'INFO'):
        """Сохраняет лог в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Записываем в общий лог-файл
        if level.upper() == 'ERROR':
            logging.error(message)
        else:
            logging.info(message)
            
        # Дополнительно сохраняем важные сообщения в отдельные файлы
        if level.upper() in ['ERROR', 'WARNING']:
            log_file = os.path.join(self.logs_dir, f'log_{timestamp}.txt')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {level} - {message}\n")
    
    def save_prompt(self, messages: List[Dict], query: str, parameters: Dict):
        """Сохраняет промпт в JSON файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = os.path.join(self.prompts_dir, f'prompt_{timestamp}.json')
        
        prompt_data = {
            "timestamp": timestamp,
            "query": query,
            "messages": messages,
            "parameters": parameters
        }
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            
        self.save_log(f"Сохранен промпт: {prompt_file}")
    
    def save_response(self, response: Dict, query: str):
        """Сохраняет ответ DeepSeek в JSON файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = os.path.join(self.responses_dir, f'response_{timestamp}.json')
        
        response_data = {
            "timestamp": timestamp,
            "query": query,
            "response": response
        }
        
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)
            
        self.save_log(f"Сохранен ответ: {response_file}")


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
        self.deepseek_service = DeepSeekService(api_key=DEEPSEEK_API_KEY,
                                                model=DEEPSEEK_MODEL,
                                                temperature=0.6,
                                                max_tokens=8192,
                                                timeout=180)

        # Инициализируем сервисы
        self.web_scraper = WebScraper(
            timeout=20,
            max_retries=2,
            max_concurrent=8
        )

        # Инициализируем логгер
        self.logger = get_logger()  # Используем глобальный логгер
        self.prompt_logger = self.logger

        self.logger.log(
            f"DeepResearchService инициализирован. Директория для результатов: {self.output_dir}",
            LogLevel.INFO
        )
        self.usage_counter = 0

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

        # 1. Сначала проверяем сокращения кодексов и законов
        code_patterns = [
            "гк", "гк рф",
            "гпк", "гпк рф",
            "упк", "упк рф",
            "ук", "ук рф",
            "кас", "кас рф",
            "коап", "коап рф",
            "тк", "тк рф",
            "жк", "жк рф",
            "зк", "зк рф",
            "бк", "бк рф",
            "нк", "нк рф",
            "апк", "апк рф",
            "ск", "ск рф"
        ]

        # Проверяем кодексы без учета регистра
        for pattern in code_patterns:
            # Преобразуем и паттерн, и часть запроса в нижний регистр для сравнения
            if any(p.lower() in query_lower for p in [pattern, pattern.upper(), pattern.title()]):
                # Для логирования используем оригинальный текст из запроса
                found_pattern = next(p for p in [pattern, pattern.upper(), pattern.title()] if p.lower() in query_lower)
                self.logger.log(f"Найден кодекс в запросе '{query}': {found_pattern}", LogLevel.INFO)
                return False

        # 2. Проверяем номера дел
        case_patterns = [
            r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*',  # Арбитражные дела: А40-12345/2023
            r'\d{1,2}-\d+/\d{2,4}',  # Суды общей юрисдикции: 2-1234/2023
            r'\d{1,2}[АA][ПпPp]/\d{2,4}',  # Административные дела: 3АП/2023
            r'[УуUu]\d{1,2}-\d+/\d{2,4}',  # Уголовные дела: У1-1234/2023
            r'[МмMm]\d{1,2}-\d+/\d{2,4}',  # Мировые судьи: М12-1234/2023
            r'[КкKk][АаAa][СсSs]-\d+/\d{2,4}',  # Кассация: КАС-1234/2023
            r'[ВвVv][СсSs]-\d+/\d{2,4}',  # Верховный суд: ВС-1234/2023
        ]

        for pattern in case_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                self.logger.log(f"Найден номер судебного дела по шаблону: {pattern}", LogLevel.INFO)
                return False

        # 3. Проверяем юридические термины
        legal_terms = [
            # Базовые юридические понятия
            "закон",
            "кодекс",
            "статья",
            "ст",  # Добавляем сокращение статьи
            "договор",
            "иск",
            "указ",
            "постановление",
            "распоряжение",
            "суд",
            "право",
            "юрист",
            "норма",
            "регулирован",
            "законодательств",
            "ответственност",
            "обязательств",
            "претензи",
            "вина",
            "устав",
            "соглашение",
            "приговор",
            "протокол",
            "правомочи",
            "правоспособност",
            "дееспособност",
            "юрисдикц",
            "субъект",
            "объект права",
            "правоотношени",
            "правопреемств",
            "презумпц",
            "юстиц",
            "правоприменен",
            "правонаделен",
            "деликт",
            "декрет",
            "доктрин",
            "прецедент",
            "санкци",
            "диспозиц",
            "гипотез",
            "правопорядок",
            "легитимн",
            "легализац",
            "квалификац",
            "юридическ",
            "удостоверен",
            "заверен",
            "определение",
            "рассрочк",
            "исполнен",
            
        ]

        for term in legal_terms:
            if term in query_lower:
                self.logger.log(f"Найден юридический термин: {term}", LogLevel.INFO)
                return False

        # 4. Только после всех юридических проверок смотрим общие паттерны
        general_patterns = [
            # Приветствия
            "привет",
            "здравствуй",
            "добрый день",
            "доброе утро",
            "добрый вечер",
            "здорово",
            "хай",
            "приветствую",
            "салют",
            "доброго времени",
            "хеллоу",
            "ку",
            "хола",
            "йоу",
            "вечер добрый",

            # Согласие/несогласие
            "да",
            "нет",
            "согласен",
            "не согласен",
            "конечно",
            "разумеется"
        ]

        for pattern in general_patterns:
            if pattern in query_lower:
                self.logger.log(f"Найден общий паттерн: {pattern}", LogLevel.INFO)
                return True

        # Если запрос очень короткий (менее 3 слов), скорее всего это общий запрос
        if len(query_lower.split()) < 3 and len(query_lower) < 15:
            self.logger.log("Запрос короткий, считаем общим", LogLevel.INFO)
            return True

        # По умолчанию считаем запрос общим, если не подтвердилось, что он юридический
        self.logger.log("Запрос не определен как юридический, считаем общим", LogLevel.INFO)
        return True

    def _extract_optimized_query(self, response):
        # Исправлено: если response — dict, берем поле 'content', иначе работаем как со строкой
        if isinstance(response, dict):
            content = response.get('content', '')
            return content.strip()
        elif isinstance(response, str):
            return response.strip()
        return ''

    def get_response_content(self, response):
        """
        Универсальный способ получить content и reasoning_content из ответа DeepSeek (dict или объект).
        """
        try:
            # dict-стиль
            if isinstance(response, dict):
                content = response["choices"][0]["message"]["content"]
                reasoning_content = response["choices"][0]["message"].get("reasoning_content")
            else:
                # объект-стиль
                content = response.choices[0].message.content
                reasoning_content = getattr(response.choices[0].message, "reasoning_content", None)
            return content, reasoning_content
        except Exception as e:
            self.logger.log(f"❌ Ошибка при разборе ответа DeepSeek: {str(e)}", LogLevel.ERROR)
            return "Извините, произошла ошибка при обработке ответа от модели.", None

    async def research(
        self, 
        query: str, 
        context: Optional[str] = None, 
        is_general: Optional[bool] = None, 
        chat_history: Optional[str] = None, 
        search_data: Optional[dict] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
        message_id: Optional[int] = None
    ) -> ResearchResult:
        try:
            if is_general is None:
                is_general = self.is_general_query(query)
                self.logger.log(f"📝 Определен тип запроса: {'общий' if is_general else 'юридический'}", LogLevel.INFO)

            if is_general:
                self.logger.log("📝 Обработка общего запроса", LogLevel.INFO)
                messages = [
                    {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ]
                response = await self.deepseek_service.chat_completion(messages)
                content, reasoning_content = self.get_response_content(response)
                # --- Сохраняем промпт в prompt_logs ---
                if db and thread_id and user_id:
                    try:
                        from app.models import PromptLog
                        db.add(PromptLog(
                            thread_id=thread_id,
                            user_id=user_id,
                            system_prompt=GENERAL_SYSTEM_PROMPT,
                            user_prompt=query,
                            message_id=message_id
                        ))
                        db.commit()
                    except Exception as e:
                        self.logger.log(f"❌ Ошибка при сохранении prompt_log: {str(e)}", LogLevel.ERROR)
                # --- Сохраняем результат в research_results ---
                if db and thread_id:
                    try:
                        from app.models import ResearchResult as ResearchResultModel
                        db.add(ResearchResultModel(
                            thread_id=thread_id,
                            query=query,
                            findings=None,
                            analysis=content
                        ))
                        db.commit()
                    except Exception as e:
                        self.logger.log(f"❌ Ошибка при сохранении research_result: {str(e)}", LogLevel.ERROR)
                return ResearchResult(
                    query=query,
                    analysis=content,
                    timestamp=self._get_timestamp(),
                    reasoning_content=reasoning_content
                )

            # --- Новый алгоритм для юридических запросов ---
            from app.services.query_optimizer import QueryOptimizer
            optimizer = QueryOptimizer()
            self.logger.log("🔎 Генерация двух уточнённых поисковых формулировок через DeepSeek...", LogLevel.INFO)
            queries = await optimizer.get_two_search_queries(query)
            if not queries or len(queries) != 2:
                self.logger.log(f"❌ Не удалось сгенерировать две поисковые формулировки, используем исходный запрос дважды", LogLevel.WARNING)
                queries = [query, query]
            self.logger.log(f"✅ Сформулированы поисковые запросы: {queries}", LogLevel.INFO)

            # Поиск по каждой формулировке
            tavily_service = TavilyService()
            es_results = []
            tavily_results = []
            for q in queries:
                es = await search_law_chunks(q, 5)
                tav = await tavily_service.search(q, 5)
                es_results.append(es)
                tavily_results.append(tav)

            # Формируем блоки для промпта
            es_block = self._format_es_results([item for sublist in es_results for item in sublist])
            tavily_block = self._format_tavily_results(queries, tavily_results)
            es_by_tavily_block = ""
            chat_block = self._format_chat_history(chat_history) if chat_history else ""

            research_prompt = self._build_research_prompt(
                query=query,
                es_block=es_block,
                es_by_tavily_block=es_by_tavily_block,
                tavily_block=tavily_block,
                chat_block=chat_block
            )

            messages = [
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": research_prompt}
            ]
            # --- Сохраняем промпт в prompt_logs ---
            if db and thread_id and user_id:
                try:
                    from app.models import PromptLog
                    db.add(PromptLog(
                        thread_id=thread_id,
                        user_id=user_id,
                        system_prompt=RESEARCH_SYSTEM_PROMPT,
                        user_prompt=research_prompt,
                        message_id=message_id
                    ))
                    db.commit()
                except Exception as e:
                    self.logger.log(f"❌ Ошибка при сохранении prompt_log: {str(e)}", LogLevel.ERROR)
            response = await self.deepseek_service.chat_completion(messages)
            content, reasoning_content = self.get_response_content(response)
            # --- Сохраняем результат в research_results ---
            if db and thread_id:
                try:
                    from app.models import ResearchResult as ResearchResultModel
                    db.add(ResearchResultModel(
                        thread_id=thread_id,
                        query=query,
                        findings=str({
                            'queries': queries,
                            'es_results': es_results,
                            'tavily_results': tavily_results
                        }),
                        analysis=content
                    ))
                    db.commit()
                except Exception as e:
                    self.logger.log(f"❌ Ошибка при сохранении research_result: {str(e)}", LogLevel.ERROR)

            # --- Сохраняем промпт и ответ в .json ---
            if hasattr(self, 'logger') and hasattr(self.logger, 'save_prompt'):
                try:
                    self.logger.save_prompt(messages, query, parameters={"thread_id": thread_id, "user_id": user_id})
                except Exception as e:
                    self.logger.log(f"Ошибка при сохранении промпта: {e}", LogLevel.ERROR)
            if hasattr(self, 'logger') and hasattr(self.logger, 'save_response'):
                try:
                    self.logger.save_response({"result": content, "reasoning": reasoning_content}, query)
                except Exception as e:
                    self.logger.log(f"Ошибка при сохранении ответа: {e}", LogLevel.ERROR)

            return ResearchResult(
                query=query,
                analysis=content,
                timestamp=self._get_timestamp(),
                reasoning_content=reasoning_content
            )

        except Exception as e:
            self.logger.log(f"❌ Ошибка при выполнении исследования: {str(e)}", LogLevel.ERROR)
            return ResearchResult(
                query=query,
                analysis="Извините, произошла ошибка при обработке запроса.",
                error=str(e),
                timestamp=self._get_timestamp(),
                reasoning_content=None
            )

    def _format_es_results(self, results: List[Dict]) -> str:
        """Форматирует результаты ElasticSearch."""
        self.logger.log(f"[ES] Получено результатов: {len(results)}", LogLevel.INFO)
        if not results:
            self.logger.log("[ES] Нет результатов для форматирования", LogLevel.WARNING)
            return "Нет результатов из законодательства."
        formatted = []
        for idx, r in enumerate(results):
            text = ensure_correct_encoding(str(r.get("text", "")))
            title = ensure_correct_encoding(str(r.get("title", "")))
            score = r.get("score", 0)
            highlights = r.get("highlights", [])
            # Логируем структуру результата
            self.logger.log(f"[ES] Результат {idx+1}: title='{title}', score={score}, highlights={len(highlights)}", LogLevel.DEBUG)
            if text:
                result_parts = []
                if title:
                    result_parts.append(f"Документ: {title}")
                result_parts.append(f"Текст: {text}")
                if highlights:
                    highlight_text = "\n".join(highlights)
                    result_parts.append(f"Релевантные фрагменты: {highlight_text}")
                result_parts.append(f"Релевантность: {score:.2f}")
                formatted.append("\n".join(result_parts))
        if not formatted:
            self.logger.log("[ES] После форматирования нет валидных результатов", LogLevel.WARNING)
            return "Нет результатов из законодательства."
        formatted.sort(key=lambda x: float(x.split("Релевантность:")[-1].strip() or "0"), reverse=True)
        formatted = formatted[:10]
        final_text = "\n\n" + "=" * 80 + "\n\n".join(formatted)
        if len(final_text) > 15000:
            final_text = truncate_text_intelligently(final_text, 15000)
        self.logger.log(f"[ES] Итоговый размер форматированного блока: {len(final_text)} символов", LogLevel.INFO)
        return final_text
        
    def _format_tavily_results(self, queries: List[str], results: List[List[Dict]]) -> str:
        """Форматирует результаты Tavily."""
        if not queries or not results or not isinstance(results, list):
            self.logger.log("❌ Нет результатов Tavily для форматирования", LogLevel.WARNING)
            return "Нет результатов."
        self.logger.log(f"[TAVILY] Получено запросов: {len(queries)}", LogLevel.INFO)
        self.logger.log(f"[TAVILY] Получено списков результатов: {len(results)}", LogLevel.INFO)
        blocks = []
        for i, (query, result_list) in enumerate(zip(queries, results)):
            self.logger.log(f"[TAVILY] Форматирование результатов для запроса {i+1}: {query}", LogLevel.INFO)
            self.logger.log(f"[TAVILY] Количество результатов: {len(result_list)}", LogLevel.INFO)
            if result_list and isinstance(result_list, list):
                sorted_results = sorted(
                    result_list,
                    key=lambda x: float(x.get("score", 0)),
                    reverse=True
                )
                formatted_results = []
                for idx, r in enumerate(sorted_results):
                    title = r.get("title", "").strip()
                    body = r.get("body", r.get("content", "")).strip()
                    url = r.get("href", r.get("url", "")).strip()
                    source = r.get("source", "").strip()
                    score = r.get("score", 0)
                    # Логируем структуру результата
                    self.logger.log(f"[TAVILY] Результат {idx+1}: title='{title}', score={score}, url='{url}'", LogLevel.DEBUG)
                    if body:
                        result_parts = []
                        if title:
                            result_parts.append(f"Заголовок: {title}")
                        result_parts.append(f"Содержание: {body}")
                        if url:
                            result_parts.append(f"Источник: {url}")
                        if source:
                            result_parts.append(f"Домен: {source}")
                        result_parts.append(f"Релевантность: {score:.2f}")
                        formatted_results.append("\n".join(result_parts))
                if formatted_results:
                    content = "\n\n".join(formatted_results[:5])
                    blocks.append(f"Результаты поиска для запроса '{query}':\n{content}")
        if not blocks:
            self.logger.log("[TAVILY] После форматирования нет валидных результатов", LogLevel.WARNING)
            return "Нет релевантных результатов."
        final_text = "\n\n" + "=" * 80 + "\n\n".join(blocks)
        self.logger.log(f"[TAVILY] Итоговый размер форматированного блока: {len(final_text)} символов", LogLevel.INFO)
        return final_text
        
    def _format_chat_history(self, history: str) -> str:
        """
        Форматирует историю чата для включения в промпт.
        Преобразует историю в структурированный формат диалога.
        Args:
            history: JSON строка с историей чата в формате:
            [{"role": "user"/"assistant", "content": "text"}]
        Returns:
            str: Отформатированная история чата
        """
        if not history:
            return ""
            
        try:
            # Пробуем распарсить историю как JSON
            if isinstance(history, str):
                try:
                    messages = json.loads(history)
                except json.JSONDecodeError:
                    self.logger.log("❌ Не удалось распарсить историю чата как JSON", LogLevel.ERROR)
                    return ""
            else:
                messages = history

            # Проверяем формат сообщений
            if not isinstance(messages, list):
                self.logger.log("❌ История чата должна быть списком", LogLevel.ERROR)
                return ""

            # Форматируем диалог
            formatted_messages = []
            for msg in messages[-5:]:  # Берем только последние 5 сообщений
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "").strip()
                    if role and content:
                        prefix = "Ассистент" if role == "assistant" else "Пользователь"
                        formatted_messages.append(f"{prefix}: {content}")

            # Объединяем сообщения
            formatted_history = "\n\n".join(formatted_messages)

            # Если история слишком длинная, обрезаем
            if len(formatted_history) > 5000:
                formatted_history = truncate_text_intelligently(formatted_history, 5000)

            self.logger.log(f"📝 История чата отформатирована, размер: {len(formatted_history)} символов", LogLevel.INFO)
            return formatted_history

        except Exception as e:
            self.logger.log(f"⚠️ Ошибка при форматировании истории чата: {str(e)}", LogLevel.ERROR)
            return ""
        
    def _format_es_results_by_tavily(self, queries: list, results_by_query: list) -> str:
        """Форматирует результаты ElasticSearch по уточнённым запросам Tavily."""
        if not queries or not results_by_query:
            return "Нет результатов по уточнённым запросам."
        blocks = []
        for i, (query, results) in enumerate(zip(queries, results_by_query)):
            content = "\n".join([
                ensure_correct_encoding(str(r.get("text", "")))
                for r in results
            ])[:8000]
            blocks.append(f"Уточнённый запрос {i+1}: {query}\n{content}")
        return "\n\n".join(blocks)

    def _build_research_prompt(
        self,
        query: str,
        es_block: str,
        es_by_tavily_block: str,
        tavily_block: str,
        chat_block: str
    ) -> str:
        """
        Собирает промпт для исследования.
        Структурирует информацию по приоритетности и релевантности.
        """
        parts = []
        
        # 1. Добавляем исходный запрос
        parts.append(f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{query}\n")
        
        # 2. Добавляем историю чата, если есть
        if chat_block:
            parts.append(f"ИСТОРИЯ ДИАЛОГА:\n{chat_block}\n")
        
        # 3. Добавляем результаты поиска в законодательстве
        if es_block and es_block != "Нет результатов из законодательства.":
            parts.append(f"РЕЗУЛЬТАТЫ ПОИСКА В ЗАКОНОДАТЕЛЬСТВЕ:\n{es_block}\n")
        
        # 4. Добавляем результаты поиска по уточнённым запросам
        if es_by_tavily_block and es_by_tavily_block != "Нет результатов по уточнённым запросам.":
            parts.append(f"ДОПОЛНИТЕЛЬНЫЕ РЕЗУЛЬТАТЫ ИЗ ЗАКОНОДАТЕЛЬСТВА:\n{es_by_tavily_block}\n")
        
        # 5. Добавляем результаты поиска в интернете
        if tavily_block and tavily_block != "Нет релевантных результатов.":
            parts.append(f"РЕЗУЛЬТАТЫ ПОИСКА В ИНТЕРНЕТЕ:\n{tavily_block}\n")
        
        # 6. Добавляем LEGAL_SYSTEM_PROMPT вместо старых инструкций
        parts.append(LEGAL_SYSTEM_PROMPT)
        
        # Объединяем все части с разделителями
        return "\n" + "=" * 80 + "\n\n".join(parts)

    def read_document(self, file_path: str) -> Optional[str]:
        """
        Извлекает текст из документа.
            
        Args:
            file_path: Путь к документу
                    
        Returns:
            Текстовое содержимое документа или None в случае ошибки
        """
        try:
            self.logger.log(
                f"[DeepResearch #{self.usage_counter}] Извлечение текста из документа: {file_path}", LogLevel.INFO
            )
            extracted_text = extract_text_from_any_document(file_path)

            if extracted_text:
                self.logger.log(
                    f"[DeepResearch #{self.usage_counter}] Успешно извлечен текст ({len(extracted_text)} символов)", LogLevel.INFO
                )
                # Если текст слишком большой, обрезаем его
                max_length = 30000
                if len(extracted_text) > max_length:
                    extracted_text = extracted_text[:max_length] + "...[текст обрезан из-за ограничений размера]"

                return extracted_text

            return None
        except Exception as e:
            self.logger.log(
                f"[DeepResearch #{self.usage_counter}] Ошибка при извлечении текста из документа {file_path}: {str(e)}", LogLevel.ERROR
            )
            return None

    def _get_timestamp(self) -> str:
        """Возвращает текущую метку времени в формате для имен файлов."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _get_current_time(self) -> str:
        """Возвращает текущее время в ISO формате."""
        return datetime.now().isoformat()
