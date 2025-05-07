"""
Модуль для формирования промпта и интеллектуального сжатия текста.
Обеспечивает:
- Формирование промпта с учетом лимитов токенов
- Интеллектуальное сжатие результатов поиска
- Сохранение важных юридических деталей при сжатии
"""
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from app.utils.logger import get_logger, LogLevel
from app.services.deepseek_service import DeepSeekService

# Инициализируем логгер
logger = get_logger()

class PromptBuilder:
    """
    Класс для формирования промпта и интеллектуального сжатия текста.
    """
    def __init__(self, deepseek_service: Optional[DeepSeekService] = None):
        self.deepseek_service = deepseek_service or DeepSeekService()
        self.logger = logger

    async def build_prompt(
        self,
        query: str,
        es_results: List[Dict],
        tavily_results: List[Dict],
        chat_history: Optional[Union[str, List[Dict]]] = None,
        system_prompt: str = "",
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Формирует промпт для DeepSeek с учетом всех компонентов и лимитов.
        
        Args:
            query: Запрос пользователя
            es_results: Результаты поиска ElasticSearch (не более 6)
            tavily_results: Результаты поиска Tavily (не менее 5)
            chat_history: История чата (опционально)
            system_prompt: Системный промпт
            max_tokens: Максимальное количество токенов
            
        Returns:
            Dict с промптом и метаданными
        """
        try:
            # 1. Логируем начало формирования промпта
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "build_prompt",
                "query": query,
                "es_results_count": len(es_results),
                "tavily_results_count": len(tavily_results),
                "max_tokens": max_tokens
            }
            
            # 2. Форматируем историю чата (не более 5 сообщений или 3 пар)
            formatted_history = await self._format_chat_history(chat_history)
            log_entry["chat_history_messages"] = len(formatted_history) if formatted_history else 0
            
            # 3. Форматируем результаты поиска
            es_block = await self._format_es_results(es_results[:6])  # Ограничиваем до 6 результатов
            tavily_block = await self._format_tavily_results(tavily_results)  # Минимум 5 результатов
            
            # 4. Собираем все компоненты промпта
            prompt_parts = []
            if system_prompt:
                prompt_parts.append({"role": "system", "content": system_prompt})
            
            if formatted_history:
                prompt_parts.extend(formatted_history)
            
            # Добавляем результаты поиска как контекст
            context = []
            if es_block:
                context.append("РЕЗУЛЬТАТЫ ПОИСКА В ЗАКОНОДАТЕЛЬСТВЕ:\n" + es_block)
            if tavily_block:
                context.append("РЕЗУЛЬТАТЫ ПОИСКА В ИНТЕРНЕТЕ:\n" + tavily_block)
            
            if context:
                context_message = "\n\n" + "=" * 80 + "\n\n".join(context)
                prompt_parts.append({"role": "system", "content": context_message})
            
            # Добавляем запрос пользователя
            prompt_parts.append({"role": "user", "content": query})
            
            # 5. Проверяем общий размер и при необходимости сжимаем
            total_size = sum(len(p["content"]) for p in prompt_parts)
            if total_size > max_tokens:
                prompt_parts = await self._compress_prompt(prompt_parts, max_tokens)
            
            # 6. Логируем результат
            log_entry.update({
                "final_size": sum(len(p["content"]) for p in prompt_parts),
                "was_compressed": total_size > max_tokens,
                "status": "success"
            })
            self.logger.log(json.dumps(log_entry), LogLevel.INFO)
            
            return {
                "messages": prompt_parts,
                "metadata": {
                    "original_size": total_size,
                    "final_size": log_entry["final_size"],
                    "was_compressed": log_entry["was_compressed"]
                }
            }
            
        except Exception as e:
            error_log = {**log_entry, "status": "error", "error": str(e)}
            self.logger.log(json.dumps(error_log), LogLevel.ERROR)
            raise
    
    async def _format_chat_history(
        self, 
        history: Optional[Union[str, List[Dict]]]
    ) -> List[Dict[str, str]]:
        """
        Форматирует историю чата, ограничивая её 5 сообщениями или 3 парами.
        """
        if not history:
            return []
            
        try:
            # Преобразуем историю в список сообщений
            if isinstance(history, str):
                messages = json.loads(history)
            else:
                messages = history
                
            if not isinstance(messages, list):
                return []
                
            # Оставляем только последние сообщения
            formatted = []
            pairs_count = 0
            messages_count = 0
            
            for msg in reversed(messages):
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    continue
                    
                # Считаем пары user-assistant
                if msg["role"] == "user":
                    pairs_count += 1
                    
                messages_count += 1
                formatted.insert(0, {
                    "role": msg["role"],
                    "content": msg["content"].strip()
                })
                
                # Проверяем лимиты
                if pairs_count >= 3 or messages_count >= 5:
                    break
            
            return formatted
            
        except Exception as e:
            self.logger.log(f"Ошибка при форматировании истории чата: {str(e)}", LogLevel.ERROR)
            return []
    
    async def _format_es_results(self, results: List[Dict]) -> str:
        """
        Форматирует результаты ElasticSearch, сохраняя важные юридические детали.
        """
        if not results:
            return ""
            
        formatted = []
        for idx, result in enumerate(results):
            # Извлекаем и форматируем основные поля
            title = result.get("title", "").strip()
            text = result.get("text", "").strip()
            score = result.get("score", 0)
            
            # Извлекаем номера дел и нормы права
            legal_details = await self._extract_legal_details(text)
            
            # Форматируем результат
            parts = []
            if title:
                parts.append(f"Документ: {title}")
            if legal_details:
                parts.append(f"Важные детали: {legal_details}")
            parts.append(f"Текст: {text}")
            parts.append(f"Релевантность: {score:.2f}")
            
            formatted.append("\n".join(parts))
        
        return "\n\n" + "=" * 80 + "\n\n".join(formatted)
    
    async def _format_tavily_results(self, results: List[Dict]) -> str:
        """
        Форматирует результаты Tavily, сохраняя важные юридические детали.
        """
        if not results or len(results) < 5:
            return ""
            
        formatted = []
        for result in results:
            # Извлекаем основные поля
            title = result.get("title", "").strip()
            content = result.get("content", result.get("body", "")).strip()
            url = result.get("url", result.get("href", "")).strip()
            score = result.get("score", 0)
            
            # Извлекаем юридические детали
            legal_details = await self._extract_legal_details(content)
            
            # Форматируем результат
            parts = []
            if title:
                parts.append(f"Заголовок: {title}")
            if legal_details:
                parts.append(f"Важные детали: {legal_details}")
            parts.append(f"Содержание: {content}")
            if url:
                parts.append(f"Источник: {url}")
            parts.append(f"Релевантность: {score:.2f}")
            
            formatted.append("\n".join(parts))
        
        return "\n\n" + "=" * 80 + "\n\n".join(formatted[:5])  # Берем только топ-5 результатов
    
    async def _extract_legal_details(self, text: str) -> str:
        """
        Извлекает важные юридические детали из текста:
        - Номера судебных дел
        - Нормы права
        - Ссылки на источники
        """
        prompt = {
            "role": "user",
            "content": f"""Извлеки из текста важные юридические детали:
1. Номера судебных дел (например, А40-12345/2023)
2. Нормы права (например, ст. 15 ГК РФ)
3. Ссылки на источники и НПА

Текст:
{text}

Верни только найденные детали, каждую с новой строки. Если деталей нет, верни пустую строку."""
        }
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[prompt],
                temperature=0.1  # Низкая температура для более точного извлечения
            )
            
            if isinstance(response, dict):
                details = response["choices"][0]["message"]["content"].strip()
                return details if details else ""
            return ""
            
        except Exception as e:
            self.logger.log(f"Ошибка при извлечении юридических деталей: {str(e)}", LogLevel.ERROR)
            return ""
    
    async def _compress_prompt(
        self,
        prompt_parts: List[Dict[str, str]],
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """
        Интеллектуально сжимает промпт, сохраняя важные юридические детали.
        """
        # 1. Разделяем части промпта по типам
        system_prompts = []
        chat_history = []
        search_results = []
        user_query = None
        
        for part in prompt_parts:
            if part["role"] == "system":
                if "РЕЗУЛЬТАТЫ ПОИСКА" in part["content"]:
                    search_results.append(part)
                else:
                    system_prompts.append(part)
            elif part["role"] == "user" and not user_query:
                user_query = part
            else:
                chat_history.append(part)
        
        # 2. Сжимаем каждую часть отдельно
        compressed_parts = []
        
        # Системные промпты не сжимаем
        compressed_parts.extend(system_prompts)
        
        # Сжимаем историю чата если нужно
        if chat_history:
            # Оставляем только последние сообщения
            compressed_parts.extend(chat_history[-4:])  # 2 пары сообщений
        
        # Сжимаем результаты поиска
        if search_results:
            for result in search_results:
                compressed_content = await self._compress_search_results(
                    result["content"],
                    max_tokens // (len(search_results) + 2)  # Оставляем место для запроса
                )
                compressed_parts.append({
                    "role": "system",
                    "content": compressed_content
                })
        
        # Запрос пользователя всегда добавляем последним
        if user_query:
            compressed_parts.append(user_query)
        
        return compressed_parts
    
    async def _compress_search_results(self, content: str, max_tokens: int) -> str:
        """
        Интеллектуально сжимает результаты поиска через LLM.
        """
        prompt = {
            "role": "user",
            "content": f"""Сократи следующий текст до {max_tokens} токенов, сохранив:
1. ВСЕ номера судебных дел
2. ВСЕ нормы права и ссылки на законы
3. ВСЕ ссылки на источники
4. Наиболее важные выводы и аргументы

Текст для сжатия:
{content}

Сохрани структуру и форматирование исходного текста."""
        }
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[prompt],
                temperature=0.1
            )
            
            if isinstance(response, dict):
                compressed = response["choices"][0]["message"]["content"].strip()
                return compressed if compressed else content
            return content
            
        except Exception as e:
            self.logger.log(f"Ошибка при сжатии результатов поиска: {str(e)}", LogLevel.ERROR)
            return content 