from typing import List, Dict, Optional
import logging
from app.services.deepseek_service import DeepSeekService
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL
import re

class QueryOptimizer:
    """
    Сервис для оптимизации поисковых запросов с использованием DeepSeek.
    """
    def __init__(self):
        self.deepseek_service = DeepSeekService(
            api_key=DEEPSEEK_API_KEY,
            model=DEEPSEEK_MODEL
        )
        
    async def optimize_query(self, user_query: str) -> str:
        """
        Оптимизирует поисковый запрос для более эффективного поиска.
        
        Args:
            user_query: Исходный запрос пользователя
            
        Returns:
            str: Оптимизированный запрос
        """
        prompt = f"""
        Оптимизируй следующий поисковый запрос для более эффективного поиска в интернете в юридической сфере.
        Запрос должен быть кратким, точным и содержать ключевые слова с юридическим подтекстом.
        Исходный запрос: {user_query}
        
        Верни только оптимизированный запрос, без дополнительных пояснений.
        """
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Ошибка при оптимизации запроса: {str(e)}")
            return user_query
            
    async def split_complex_query(self, user_query: str) -> List[str]:
        """
        Разбивает сложный запрос на подзапросы.
        
        Args:
            user_query: Исходный запрос пользователя
            
        Returns:
            List[str]: Список подзапросов
        """
        prompt = f"""
        Разбей следующий сложный запрос на отдельные подзапросы для более эффективного поиска.
        Каждый подзапрос должен быть самостоятельным и содержать ключевые слова.
        Исходный запрос: {user_query}
        
        Верни только список подзапросов, каждый с новой строки, без дополнительных пояснений.
        """
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            return [q.strip() for q in response.split('\n') if q.strip()]
        except Exception as e:
            logging.error(f"Ошибка при разбиении запроса: {str(e)}")
            return [user_query]
            
    async def filter_by_relevance(self, results: List[Dict], original_query: str) -> List[Dict]:
        """
        Фильтрует результаты поиска по релевантности с помощью DeepSeek.
        
        Args:
            results: Список результатов поиска
            original_query: Исходный запрос пользователя
            
        Returns:
            List[Dict]: Отфильтрованные результаты
        """
        if not results:
            return []
            
        prompt = f"""
        Оцени релевантность следующих результатов поиска относительно запроса: {original_query}
        
        Результаты:
        {chr(10).join(f"{i+1}. {r.get('title', '')} - {r.get('url', '')}" for i, r in enumerate(results))}
        
        Верни только номера релевантных результатов (через запятую), без дополнительных пояснений.
        """
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            relevant_indices = [int(i.strip()) - 1 for i in response.split(',') if i.strip().isdigit()]
            return [results[i] for i in relevant_indices if 0 <= i < len(results)]
        except Exception as e:
            logging.error(f"Ошибка при фильтрации результатов: {str(e)}")
            return results
            
    async def refine_search_query(self, current_query: str, current_results: List[Dict]) -> str:
        """
        Уточняет поисковый запрос на основе текущих результатов.
        
        Args:
            current_query: Текущий поисковый запрос
            current_results: Текущие результаты поиска
            
        Returns:
            str: Уточненный запрос
        """
        prompt = f"""
        На основе текущих результатов поиска уточни запрос для получения более релевантных результатов.
        
        Текущий запрос: {current_query}
        
        Текущие результаты:
        {chr(10).join(f"{i+1}. {r.get('title', '')} - {r.get('url', '')}" for i, r in enumerate(current_results))}
        
        Верни только уточненный запрос, без дополнительных пояснений.
        """
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Ошибка при уточнении запроса: {str(e)}")
            return current_query
            
    async def get_two_search_queries(self, user_query: str) -> List[str]:
        """
        Генерирует ровно два уточнённых поисковых запроса для Tavily через DeepSeek.
        
        Args:
            user_query: Исходный запрос пользователя
            
        Returns:
            List[str]: Список из двух оптимизированных запросов
        """
        prompt = (
            f'На основе запроса пользователя "{user_query}" сформулируй два эффективных поисковых запроса для поиска '
            'юридической информации в интернете. Запросы должны:\n'
            '1. Быть максимально конкретными и содержать юридическую терминологию\n'
            '2. Охватывать разные аспекты исходного вопроса\n'
            '3. Включать ключевые слова для поиска судебной практики\n\n'
            'Верни только два запроса, каждый с новой строки, без пояснений и нумерации.'
        )
        
        try:
            response = await self.deepseek_service.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Проверяем тип ответа и извлекаем текст
            if isinstance(response, dict) and 'choices' in response:
                text = response["choices"][0]["message"]["content"]
            elif isinstance(response, str):
                text = response
            else:
                logging.error(f"Неожиданный формат ответа от DeepSeek: {type(response)}")
                return self._fallback_queries(user_query)
            
            # Разбираем и валидируем запросы
            queries = self._parse_and_validate_queries(text)
            
            # Если не удалось получить два валидных запроса, используем запасной вариант
            if len(queries) != 2:
                logging.warning(f"Получено неверное количество запросов ({len(queries)}), использую запасной вариант")
                return self._fallback_queries(user_query)
            
            logging.info(f"Сгенерированы поисковые запросы для Tavily: {queries}")
            return queries
            
        except Exception as e:
            logging.error(f"Ошибка при генерации поисковых запросов: {str(e)}")
            return self._fallback_queries(user_query)
    
    def _parse_and_validate_queries(self, text: str) -> List[str]:
        """
        Разбирает и валидирует запросы из текста ответа.
        
        Args:
            text: Текст ответа от модели
            
        Returns:
            List[str]: Список валидных запросов
        """
        # Разбиваем текст на строки и очищаем
        queries = []
        for line in text.split('\n'):
            # Очищаем строку
            line = line.strip()
            # Удаляем нумерацию в начале строки
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            # Удаляем кавычки
            line = line.strip('"\'')
            
            # Проверяем валидность запроса
            if line and len(line) >= 10:  # Минимальная длина для осмысленного запроса
                queries.append(line)
        
        return queries
    
    def _fallback_queries(self, user_query: str) -> List[str]:
        """
        Создает запасные запросы при ошибке генерации.
        
        Args:
            user_query: Исходный запрос пользователя
            
        Returns:
            List[str]: Список из двух запасных запросов
        """
        # Первый запрос - исходный + судебная практика
        query1 = f"{user_query} судебная практика"
        # Второй запрос - исходный + законодательство
        query2 = f"{user_query} законодательство РФ"
        
        return [query1, query2] 