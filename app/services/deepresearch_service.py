import os
import sys
import json
import asyncio
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime
from app.handlers.user_doc_request import extract_text_from_any_document
from app.handlers.deepresearch_audit import audit_deepresearch, deepresearch_audit
from app.services.deepseek_service import DeepSeekService

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
            temperature=0.7,  # Снижаем температуру для более фактического ответа
            max_tokens=8000,
            timeout=120
        )
            
        logging.info(f"DeepResearchService инициализирован. Директория для результатов: {self.output_dir}")
        
        # Счетчик использования для отладки
        self.usage_counter = 0

    def filter_suspicious_court_numbers(self, text: str) -> str:
        """
        Фильтрует подозрительные номера судебных дел в тексте.
        
        Args:
            text: Исходный текст ответа
            
        Returns:
            Отфильтрованный текст
        """
        import re
        
        # Шаблоны подозрительных номеров дел
        suspicious_patterns = [
            r'А\d+-\d{6}/\d{4}',  # Шаблон вида А40-123456/2019
            r'А\d+-\d{5,6}/\d{4}',  # Шаблоны с 5-6 цифрами в номере
        ]
        
        # Функция для проверки на подозрительные последовательности
        def is_suspicious_sequence(num_str):
            # Проверка на последовательные цифры (123456, 654321)
            sequential_up = '0123456789'
            sequential_down = '9876543210'
            for i in range(len(num_str) - 2):
                if num_str[i:i+3] in sequential_up or num_str[i:i+3] in sequential_down:
                    return True
            
            # Проверка на повторяющиеся цифры (111, 222)
            for i in range(len(num_str) - 2):
                if num_str[i] == num_str[i+1] == num_str[i+2]:
                    return True
            
            return False
        
        # Поиск и проверка всех подозрительных номеров дел
        for pattern in suspicious_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                court_num = match.group(0)
                num_part = re.search(r'\d+', court_num).group(0)
                
                # Если номер подозрительный, заменяем на общую формулировку
                if is_suspicious_sequence(num_part) or len(num_part) >= 6:
                    replacement = "согласно сложившейся судебной практике"
                    text = text.replace(court_num, replacement)
        
        return text

    @audit_deepresearch
    async def research(self, query: str, additional_context: Optional[List[Dict]] = None) -> ResearchResult:
        """
        Выполняет глубокий анализ запроса с использованием DeepSeek API.
        
        Args:
            query: Текст запроса или путь к файлу для анализа
            additional_context: Дополнительный контекст из других источников
                    
        Returns:
            ResearchResult: Результат исследования в структурированном виде
        """
        self.usage_counter += 1
        logging.info(f"[DeepResearch #{self.usage_counter}] Начинаем исследование. Длина запроса: {len(query)} символов")
        
        # Обработка файлов, если query - путь к файлу
        if isinstance(query, str) and (query.endswith('.docx') or query.endswith('.pdf')):
            query = self.read_document(query) or query
        
        try:
            # Определяем системный промпт на основе типа запроса
            system_prompt = ("Ты - эксперт по юридическому анализу. "
                        "Проведи глубокое исследование предоставленного запроса. "
                        "Анализируй с точки зрения российского законодательства, если применимо. "
                        "Структурируй ответ, выделяя ключевые моменты, актуальные правовые нормы, "
                        "судебную практику и практические рекомендации по теме. "
                        "\n\nСТРОГО ЗАПРЕЩЕНО:"
                        "\n1. НИКОГДА не указывай номера судебных дел с повторяющимися или последовательными цифрами (например, А40-123456/2019, А40-123123/2020, А40-123321/2022 и т.п.)."
                        "\n2. НИКОГДА не указывай выдуманные номера судебных дел."
                        "\n3. При ссылке на судебную практику либо:"
                        "\n   а) ссылайся только на реальные номера дел из предоставленных источников,"
                        "\n   б) либо указывай общие сведения о судебной позиции без привязки к конкретным делам (например: \"Согласно позиции ВС РФ...\" или \"В судебной практике сложился подход...\")."
                        "\n4. Никогда не указывай номера дел вида \"А40-XXXXXX/YYYY\", где XXXXXX - шестизначное число, а YYYY - год, если ты его придумал."
                        "\n\nЕсли не уверен в точности номера дела - НЕ УКАЗЫВАЙ его вообще.")
            
            # Формируем пользовательский промпт
            user_prompt = f"Проведи детальный юридический анализ запроса:\n\n{query}"
            
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
            
            # Используем DeepSeek API
            analysis = await self.deepseek_service.generate_with_system(system_prompt, user_prompt)
            
            # Фильтруем подозрительные номера судебных дел
            filtered_analysis = self.filter_suspicious_court_numbers(analysis)
            
            # Формируем структурированный результат
            result = ResearchResult(
                query=query[:1000] + "..." if len(query) > 3000 else query,
                analysis=filtered_analysis,
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