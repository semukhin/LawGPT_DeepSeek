from typing import List, Dict, Any, Protocol
from dataclasses import dataclass
import tiktoken

class ContextManager:
    def __init__(
        self, 
        max_tokens: int = 4000,  # Настраиваемый лимит
        model: str = 'gpt-4'
    ):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.encoding_for_model(model)
    
    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def prepare_context(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str = ""
    ) -> List[Dict[str, str]]:
        """
        Подготовка контекста с учетом ограничений по токенам
        """
        prepared_messages = []
        current_tokens = 0
        
        # Добавляем системный промпт первым
        if system_prompt:
            system_msg = {"role": "system", "content": system_prompt}
            current_tokens += self._count_tokens(system_prompt)
            prepared_messages.append(system_msg)
        
        # Обратный проход по сообщениям для сохранения последних
        for message in reversed(messages):
            msg_tokens = self._count_tokens(message['content'])
            
            # Проверка лимита токенов
            if current_tokens + msg_tokens > self.max_tokens:
                break
            
            current_tokens += msg_tokens
            prepared_messages.insert(1, message)  # Вставляем после системного промпта
        
        return prepared_messages
    
    def summarize_context(
        self, 
        messages: List[Dict[str, str]], 
        ai_provider: Any  # Абстракция для разных провайдеров
    ) -> str:
        """
        Суммаризация длинного контекста
        """
        context_text = "\n".join([m['content'] for m in messages])
        
        summary_prompt = f"""
        Создай краткое связное резюме следующего диалога, 
        сохраняя ключевые смыслы и контекст:
        
        {context_text}
        
        Резюме:
        """
        
        # Универсальный вызов с абстракцией провайдера
        summary = ai_provider.generate_text(summary_prompt)
        return summary

class AIProvider(Protocol):
    def generate_text(self, prompt: str) -> str:
        """Протокол для любого AI провайдера"""
        ...

class OpenAIProvider:
    def __init__(self, client):
        self.client = client
    
    def generate_text(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4",
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