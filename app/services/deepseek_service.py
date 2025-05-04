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

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL

def decode_unicode(text: str) -> str:
    """Декодирует escape-последовательности Unicode в строке."""
    try:
        return text.encode('utf-8').decode('unicode-escape')
    except:
        return text

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DeepSeekService:
    """
    Сервис для выполнения запросов к DeepSeek API.
    Поддерживает вызов функций и многораундовые диалоги.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "deepseek-reasoner",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        timeout: int = 180
    ):
        """
        Инициализирует сервис с параметрами API DeepSeek.
        
        Args:
            api_key: API ключ DeepSeek (если None, берется из конфигурации)
            api_base: Базовый URL API (если None, берется из конфигурации)
            model: Имя модели для использования
            temperature: Параметр температуры для генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
            timeout: Таймаут запроса в секундах
        """
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_base = api_base or DEEPSEEK_API_BASE or "https://api.deepseek.com/v1"
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            logging.warning("DeepSeek API ключ не указан. API не будет работать.")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        model: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """
        Отправляет запрос к API DeepSeek для генерации ответа.
        
        Args:
            messages: История диалога
            functions: Описание доступных функций
            function_call: Режим вызова функций
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            stream: Потоковая генерация
            top_p: Параметр top_p
            presence_penalty: Штраф за повторение
            frequency_penalty: Штраф за частоту
            model: Модель для использования
            
        Returns:
            Union[str, Dict[str, Any]]: Ответ от API
        """
        if not self.api_key:
            return "Ошибка: API ключ DeepSeek не настроен"
        
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Проверяем и исправляем кодировку во всех сообщениях
        messages = validate_messages(messages)
        
        # Защита от None для всех параметров
        def safe_str(val, default=""):
            return str(val) if val is not None else default

        # Формируем payload с обязательными параметрами
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": stream
        }
        
        # Добавляем опциональные параметры
        if functions:
            # Проверяем и исправляем кодировку в описаниях функций
            payload["functions"] = [ensure_correct_encoding(func) for func in functions]
        
        if function_call:
            payload["function_call"] = ensure_correct_encoding(function_call)
            
        if top_p is not None:
            payload["top_p"] = top_p
            
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
            
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty

        # Безопасно добавляем context, chat_history, search_data если они есть
        if hasattr(self, 'context') and self.context is not None:
            payload["context"] = safe_str(self.context)
        if hasattr(self, 'chat_history') and self.chat_history is not None:
            payload["chat_history"] = safe_str(self.chat_history)
        if hasattr(self, 'search_data') and self.search_data is not None:
            payload["search_data"] = self.search_data if isinstance(self.search_data, dict) else safe_str(self.search_data)

        # Логируем отправляемый payload с проверкой кодировки
        logging.info(f"Отправляемый payload: {json.dumps(ensure_correct_encoding(payload), ensure_ascii=False)[:200]}...")

        try:
            # Устанавливаем фиксированный таймаут в 180 секунд (3 минуты)
            fixed_timeout = 180
            
            logging.info(f"Отправка запроса к DeepSeek API: {url}")
            logging.info(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        url, 
                        headers=headers, 
                        json=payload,
                        timeout=fixed_timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logging.error(f"Ошибка DeepSeek API ({response.status}): {error_text}")
                            return f"Ошибка API: {response.status} - {error_text}"
                        
                        if stream:
                            # Обработка потокового ответа
                            full_response = ""
                            reasoning_content = ""
                            async for line in response.content:
                                line = line.decode('utf-8').strip()
                                if line.startswith('data: ') and line != 'data: [DONE]':
                                    json_str = line[6:]  # Убираем 'data: '
                                    try:
                                        chunk = json.loads(json_str)
                                        if 'reasoning_content' in chunk.get('choices', [{}])[0].get('delta', {}):
                                            reasoning_content += chunk['choices'][0]['delta']['reasoning_content']
                                        else:
                                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                            if content:
                                                full_response += ensure_correct_encoding(content)
                                    except json.JSONDecodeError:
                                        logging.error(f"Ошибка декодирования JSON из потока: {line}")
                            return {
                                "choices": [{
                                    "message": {
                                        "content": full_response,
                                        "reasoning_content": reasoning_content
                                    }
                                }]
                            }
                        else:
                            # Обработка обычного ответа
                            response_json = await response.json()
                            logging.info(f"Ответ API: {json.dumps(response_json, ensure_ascii=False)}")
                            
                            # Обрабатываем кодировку в ответе
                            if 'choices' in response_json and len(response_json['choices']) > 0:
                                choice = response_json['choices'][0]
                                if 'message' in choice:
                                    message = choice['message']
                                    if 'content' in message:
                                        message['content'] = ensure_correct_encoding(message['content'])
                                    if 'function_call' in message:
                                        message['function_call'] = ensure_correct_encoding(message['function_call'])
                                    if 'reasoning_content' in message:
                                        message['reasoning_content'] = ensure_correct_encoding(message['reasoning_content'])
                            
                            return response_json
                except asyncio.TimeoutError:
                    # Таймаут в 3 минуты превышен
                    logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                    return "Сервис пока не может обработать ваш запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
                
        except Exception as e:
            logging.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
            return f"Ошибка: {str(e)}"

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
        "temperature": 1.2,
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