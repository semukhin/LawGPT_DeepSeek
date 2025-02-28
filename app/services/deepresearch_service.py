import os
import sys
import json
import asyncio
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from app.handlers.user_doc_request import extract_text_from_any_document
from app.handlers.deepresearch_audit import audit_deepresearch, deepresearch_audit


# Импортируем ключ из config.py
from app.config import OPENAI_API_KEY

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
    Комбинирует возможности Shandu и OpenAI API для анализа.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Инициализирует сервис с настройками для сохранения результатов.
        
        Args:
            output_dir: Директория для сохранения результатов исследований.
        """
        self.output_dir = output_dir or "research_results"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Используем ключ API из конфигурации
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        logging.info(f"DeepResearchService инициализирован. Директория для результатов: {self.output_dir}")
        
        # Счетчик использования для отладки
        self.usage_counter = 0
        pass


    @audit_deepresearch
    async def research(self, query: str) -> ResearchResult:
        """
        Выполняет глубокий анализ запроса с использованием LLM.
        
        Args:
            query: Текст запроса или путь к файлу для анализа.
                
        Returns:
            ResearchResult: Результат исследования в структурированном виде.
        """
        self.usage_counter += 1
        logging.info(f"[DeepResearch #{self.usage_counter}] Начинаем исследование. Длина запроса: {len(query)} символов")
        
        # Проверяем, является ли запрос путем к файлу
        if query.endswith('.docx') or query.endswith('.pdf'):
            logging.info(f"[DeepResearch #{self.usage_counter}] Запрос определен как путь к файлу: {query}")
            extracted_text = self.read_document(query)
            if extracted_text:
                logging.info(f"[DeepResearch #{self.usage_counter}] Текст из файла успешно извлечен ({len(extracted_text)} символов)")
                query = extracted_text
            else:
                logging.error(f"[DeepResearch #{self.usage_counter}] Не удалось извлечь текст из файла: {query}")
        
        # Логируем небольшой фрагмент запроса для отладки
        if len(query) > 500:
            logging.info(f"[DeepResearch #{self.usage_counter}] Начало запроса: {query[:200]}...")
            logging.info(f"[DeepResearch #{self.usage_counter}] Конец запроса: ...{query[-200:]}")
        else:
            logging.info(f"[DeepResearch #{self.usage_counter}] Запрос: {query}")
        
        try:
            # Определяем тип контента для адаптации промпта
            is_legal_document = any(marker in query.lower() for marker in 
                ["статья", "кодекс", "федеральный закон", "постановление", "гк рф", "гпк рф", "упк рф", "коап"])
            
            # Выбор специализированного промпта в зависимости от содержимого
            if is_legal_document:
                system_prompt = ("Ты - эксперт по юридическому анализу. "
                            "Проанализируй предоставленный юридический текст, выдели ключевые моменты, права и обязанности, "
                            "сроки, штрафы и другие важные элементы. Сосредоточься на правовой сути и дай объективный анализ.")
            else:
                system_prompt = ("Ты - эксперт по юридическому анализу. "
                            "Проведи глубокое исследование предоставленного запроса. "
                            "Анализируй с точки зрения российского законодательства, если применимо. "
                            "Структурируй ответ, выделяя ключевые моменты, актуальные правовые нормы, "
                            "судебную практику и практические рекомендации по теме.")
            
            logging.info(f"[DeepResearch #{self.usage_counter}] Отправка запроса в OpenAI API")
            start_time = datetime.now()
            
            # Выполняем запрос с использованием того же клиента OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проведи детальный юридический анализ:\n\n{query}"}
                ],
                temperature=0.3  # Снижаем температуру для более фактического ответа
            )
            
            analysis = response.choices[0].message.content
            
            # Вычисляем время выполнения для мониторинга производительности
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logging.info(f"[DeepResearch #{self.usage_counter}] Запрос обработан. Время: {execution_time:.2f} секунд")
            
            # Логируем небольшой фрагмент ответа для отладки
            if len(analysis) > 300:
                logging.info(f"[DeepResearch #{self.usage_counter}] Начало анализа: {analysis[:150]}...")
                logging.info(f"[DeepResearch #{self.usage_counter}] Конец анализа: ...{analysis[-150:]}")
            else:
                logging.info(f"[DeepResearch #{self.usage_counter}] Анализ: {analysis}")
            
            # Формируем структурированный результат
            result = ResearchResult(
                query=query[:1000] + "..." if len(query) > 1000 else query,  # Обрезаем для компактности
                analysis=analysis,
                timestamp=self._get_current_time()
            )
            
            # Сохраняем результат если указана директория
            if self.output_dir:
                result_filename = f"research_{self.usage_counter}_{self._get_timestamp()}.json"
                result_path = os.path.join(self.output_dir, result_filename)
                result.save_to_file(result_path)
                logging.info(f"[DeepResearch #{self.usage_counter}] Результат сохранен: {result_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при исследовании: {str(e)}"
            logging.error(f"[DeepResearch #{self.usage_counter}] {error_msg}")
            return ResearchResult(
                query=query[:500] + "..." if len(query) > 500 else query,
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
                max_length = 50000  # Примерный лимит для модели GPT-4
                if len(extracted_text) > max_length:
                    extracted_text = extracted_text[:max_length] + "...[текст обрезан из-за ограничений размера]"
                    
                return extracted_text
            
            return None
        except Exception as e:
            logging.error(f"[DeepResearch #{self.usage_counter}] Ошибка при извлечении текста из документа {file_path}: {str(e)}")
            return None
        pass   

    @audit_deepresearch
    def _get_timestamp(self) -> str:
        """Возвращает текущую метку времени в формате для имен файлов."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    

    @audit_deepresearch
    def _get_current_time(self) -> str:
        """Возвращает текущее время в ISO формате."""
        return datetime.now().isoformat()

