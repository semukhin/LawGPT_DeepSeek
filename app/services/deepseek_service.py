"""
Сервис для работы с DeepSeek API.
Обеспечивает интерфейс для генерации текста с использованием моделей DeepSeek.
Поддерживает function calling и многораундовые диалоги.
"""
import os
import logging
import json
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Union, Literal
from fastapi import HTTPException
from app.utils import ensure_correct_encoding, sanitize_search_results, validate_messages, validate_context
from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, OPENROUTER_API_KEY

def decode_unicode(text: str) -> str:
    """Декодирует escape-последовательности Unicode в строке."""
    try:
        return text.encode('utf-8').decode('unicode-escape')
    except:
        return text

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

class DeepSeekService:
    """
    Сервис для выполнения запросов к DeepSeek API.
    Поддерживает вызов функций и многораундовые диалоги.
    """
    
    def __init__(self):
        openrouter_api_key = OPENROUTER_API_KEY
        
        if not openrouter_api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY не задан в конфигурации!")
            # Пробуем получить из DEEPSEEK_API_KEY для обратной совместимости
            openrouter_api_key = DEEPSEEK_API_KEY
            if openrouter_api_key:
                logger.info("Используем DEEPSEEK_API_KEY в качестве запасного варианта")
        
        if not openrouter_api_key:
            logger.error("❌ API ключ для OpenRouter не найден в конфигурации!")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key
        )
        self.model = "deepseek/deepseek-chat-v3-0324"
        
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.6,
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Отправка запроса к DeepSeek через OpenRouter API
        """
        try:
            logger.info(f"Отправка запроса к OpenRouter API: {self.model}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers={
                    "HTTP-Referer": "https://lawgpt.ru",  # URL нашего сайта
                    "X-Title": "LawGPT",  # Название нашего приложения
                }
            )
            
            return {
                "choices": [{
                    "message": {
                        "content": completion.choices[0].message.content
                    }
                }]
            }
            
        except Exception as e:
            logger.error(f"Ошибка OpenRouter API: {str(e)}")
            raise

    async def prepare_context(self, context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Подготовка контекста с обработкой кодировки"""
        # Обрабатываем кодировку всего контекста
        sanitized_context = sanitize_search_results(context)
        
        # Дополнительная обработка для каждого элемента
        for item in sanitized_context:
            if isinstance(item.get('data'), str):
                item['data'] = ensure_correct_encoding(item['data'])
            if isinstance(item.get('content'), str):
                item['content'] = ensure_correct_encoding(item['content'])
        
        return sanitized_context
    
    async def generate_response(self, messages: List[Dict[str, str]], context: List[Dict[str, Any]] = None) -> str:
        """Генерация ответа от DeepSeek с предварительной обработкой контекста"""
        try:
            if context:
                context = validate_context(context)
            
            # Обрабатываем кодировку сообщений
            sanitized_messages = validate_messages(messages)
            
            # Здесь ваш существующий код для отправки запроса в DeepSeek
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": sanitized_messages
                }
                
                if context:
                    payload["context"] = context
                
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"DeepSeek API error: {error_text}"
                        )
                    
                    result = await response.json()
                    return ensure_correct_encoding(result["choices"][0]["message"]["content"])
                    
        except Exception as e:
            logging.error(f"Error in DeepSeek service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

async def _generate(
    self, 
    messages: List[Dict], 
    functions: Optional[List[Dict]] = None,
    max_tokens: int = 8192
) -> str:
    """
    Внутренний метод генерации ответа с проверкой ограничений.
    
    Args:
        messages: Список сообщений
        functions: Список доступных функций
        max_tokens: Максимальное количество токенов
    """
    # Строгая проверка max_tokens
    max_tokens = max(1, min(max_tokens, 8192))
    
    # Фиксированный таймаут в 180 секунд
    fixed_timeout = 180
    
    payload = {
        "model": self.model,
        "messages": messages,
        "temperature": self.temperature,
        "max_tokens": max_tokens
    }
    
    if functions:
        payload["functions"] = functions
        payload["function_call"] = "auto"
    
    try:
        logging.info(f"Отправка запроса к DeepSeek API: {self.api_base}/chat/completions")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=fixed_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"API Error: {error_text}")
                        raise ValueError(f"API Error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    return result['choices'][0]['message']['content']
            
            except asyncio.TimeoutError:
                logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                return "Сервис пока не может обработать запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
                
    except Exception as e:
        logging.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
        return f"Ошибка API: {str(e)}"
        
        
        
async def chat_with_functions(
    self,
    messages: List[Dict[str, Any]],
    functions: List[Dict[str, Any]],
    function_call: Union[Literal["auto"], Literal["none"], Dict[str, str]] = "auto"
) -> Dict[str, Any]:
    """
    Отправляет запрос к DeepSeek с поддержкой вызова функций.
    
    Args:
        messages: История диалога
        functions: Описание функций в формате JSON Schema
        function_call: Режим вызова функций
        
    Returns:
        Полный ответ API, включая возможный вызов функции
    """
    # Включаем более подробную отладку для функциональных вызовов
    logging.info(f"Запрос chat_with_functions, function_call={function_call}")
    
    # Фиксированный таймаут в 180 секунд
    fixed_timeout = 180
    
    # Формируем payload
    url = f"{self.api_base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}"
    }
    
    payload = {
        "model": self.model,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": self.max_tokens,
        "functions": functions,
        "function_call": function_call
    }
    
    logging.info(f"Отправляемый payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        logging.info(f"Отправка запроса к DeepSeek API: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=payload,
                    timeout=fixed_timeout
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logging.error(f"Ошибка DeepSeek API ({response.status}): {response_text[:200]}...")
                        return f"Ошибка API: {response.status} - {response_text[:200]}..."
                    
                    try:
                        response_json = json.loads(response_text)
                        
                        # Проверяем наличие function_call в ответе
                        if 'choices' in response_json and len(response_json['choices']) > 0:
                            choice = response_json['choices'][0]
                            message = choice.get('message', {})
                            
                            if 'function_call' in message:
                                logging.info(f"✅ Function call найден: {message['function_call'].get('name')}")
                            else:
                                logging.warning("⚠️ Function call не найден в ответе")
                        
                        return response_json
                    except json.JSONDecodeError:
                        logging.error(f"Ошибка декодирования JSON ответа: {response_text[:200]}...")
                        return f"Ошибка декодирования ответа API: {response_text[:200]}..."
            
            except asyncio.TimeoutError:
                logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                return "Сервис пока не может обработать запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
        
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при запросе к DeepSeek API: {str(e)}")
        return f"Ошибка: {str(e)}"

async def _process_stream(self, response):
    """Обработка потокового ответа от DeepSeek"""
    async for line in response.content:
        if line:
            try:
                line = line.decode('utf-8').strip()
                # Декодируем строку
                line = decode_unicode(line)
                
                if line.startswith('data: ') and line != 'data: [DONE]':
                    json_str = line[6:]  # Убираем 'data: '
                    try:
                        chunk = json.loads(json_str)
                        content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            return content
                    except json.JSONDecodeError:
                        logging.error(f"Ошибка декодирования JSON из потока: {line}")
            except Exception as e:
                logging.error(f"Ошибка обработки потокового ответа: {str(e)}")