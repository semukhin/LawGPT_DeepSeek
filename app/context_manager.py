from typing import List, Dict, Any, Protocol
from dataclasses import dataclass
import tiktoken

class ContextManager:
    def __init__(
        self, 
        max_tokens: int = 8192,  
        model: str = 'deepseek-reasoner'
    ):
        self.max_tokens = max_tokens
        # Используем encoding_for_model, если модель поддерживается, 
        # иначе используем cl100k_base, который подходит для многих моделей
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def _count_tokens(self, text: str) -> int:
        """Подсчет токенов в тексте."""
        if not text:
            return 0
        return len(self.tokenizer.encode(text))
    
    def prepare_context(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str = ""
    ) -> List[Dict[str, str]]:
        """
        Подготовка контекста с учетом ограничений по токенам.
        Сохраняет системный промпт и последние сообщения в пределах лимита токенов.
        
        Args:
            messages: Список сообщений
            system_prompt: Системный промпт
            
        Returns:
            Список сообщений, которые можно передать в модель
        """
        prepared_messages = []
        current_tokens = 0
        
        # Добавляем системный промпт первым
        if system_prompt:
            system_msg = {"role": "system", "content": system_prompt}
            system_tokens = self._count_tokens(system_prompt)
            current_tokens += system_tokens
            prepared_messages.append(system_msg)
        
        # Обратный проход по сообщениям для сохранения последних
        # Сначала сортируем сообщения по дате создания (более старые вначале)
        sorted_messages = sorted(messages, key=lambda x: x.get('created_at', 0))
        
        # Проходим сообщения в обратном порядке (начиная с самых новых)
        for message in reversed(sorted_messages):
            content = message.get('content', '')
            role = message.get('role', 'user')
            
            msg_tokens = self._count_tokens(content)
            
            # Проверка лимита токенов
            if current_tokens + msg_tokens > self.max_tokens:
                break
            
            current_tokens += msg_tokens
            # Вставляем новые сообщения после системного промпта
            if prepared_messages and prepared_messages[0].get('role') == 'system':
                prepared_messages.insert(1, {"role": role, "content": content})
            else:
                prepared_messages.insert(0, {"role": role, "content": content})
        
        return prepared_messages
    
    def get_last_n_messages(
        self,
        messages: List[Dict[str, Any]],
        n: int = 5
    ) -> List[Dict[str, str]]:
        """
        Получает последние n сообщений из списка.
        
        Args:
            messages: Список сообщений
            n: Количество последних сообщений
            
        Returns:
            Список последних n сообщений
        """
        # Сортируем сообщения по дате создания
        sorted_messages = sorted(messages, key=lambda x: x.get('created_at', 0))
        
        # Берем последние n сообщений
        last_n = sorted_messages[-n:] if len(sorted_messages) >= n else sorted_messages
        
        # Конвертируем в формат, который ожидает модель
        formatted_messages = []
        for msg in last_n:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            formatted_messages.append({
                "role": role,
                "content": content
            })
        
        return formatted_messages

class AIProvider(Protocol):
    def generate_text(self, prompt: str) -> str:
        """Протокол для любого AI провайдера"""
        ...

class OpenAIProvider:
    def __init__(self, client):
        self.client = client
    
    def generate_text(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

class VertexAIProvider:
    def __init__(self, client):
        self.client = client
    
    def generate_text(self, prompt: str) -> str:
        # Ваша реализация для Vertex AI
        response = self.client.predict(prompt)
        return response.text

# Пример использования
class ThreadService:

    async def summarize_context(self, messages: List[Dict[str, str]], ai_provider: AIProvider) -> str:
        """
        Суммаризирует контекст беседы для уменьшения токенов.
        
        Args:
            messages: Список сообщений
            ai_provider: Провайдер ИИ для генерации суммаризации
            
        Returns:
            Строка с суммаризированным контекстом
        """
        # Объединяем содержимое сообщений
        combined_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages])
        
        # Создаем промпт для суммаризации
        prompt = f"Суммаризируй следующий диалог, сохраняя ключевые моменты и контекст:\n\n{combined_text}"
        
        # Получаем суммаризацию от провайдера ИИ
        summary = ai_provider.generate_text(prompt)
        
        return f"Контекст предыдущего разговора: {summary}"

    def prepare_ai_context(
        self, 
        thread_id: str, 
        ai_provider: AIProvider,
        system_prompt: str = ""
    ):
        # Извлечение сообщений
        messages = self.get_thread_messages(thread_id)
        
        context_manager = ContextManager()
        
        # Если контекст слишком большой - суммаризируем
        if len(messages) > 20:
            summary = context_manager.summarize_context(messages, ai_provider)
            messages = [
                {"role": "system", "content": summary},
                messages[-1]  # Последнее сообщение
            ]
        
        # Подготовка контекста
        prepared_context = context_manager.prepare_context(
            messages, 
            system_prompt
        )
        
        return prepared_context