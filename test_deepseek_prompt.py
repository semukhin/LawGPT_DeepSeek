import sys
import os
import json
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import codecs
import locale

# Устанавливаем кодировку для терминала
os.environ["PYTHONIOENCODING"] = "utf-8"
locale.setlocale(locale.LC_ALL, "")

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.deepresearch_service import DeepResearchService
from app.handlers.web_search import search_and_scrape
from app.handlers.es_law_search import search_law_chunks
from app.utils import ensure_correct_encoding, validate_messages, validate_context

# Создаем директорию для логов, если её нет
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Формируем имя файла лога с текущей датой
log_filename = os.path.join(log_dir, f'deepseek_prompt_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Создаем и настраиваем обработчик для файла
file_handler = logging.FileHandler(log_filename, encoding='utf-8', mode='w')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Создаем и настраиваем обработчик для консоли с поддержкой UTF-8
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Настраиваем корневой логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Удаляем существующие обработчики
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Добавляем новые обработчики
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Функция для сохранения результата в отдельный файл
def save_result_to_file(result_dict: dict, prefix: str = "result"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_filename = os.path.join(log_dir, f'{prefix}_{timestamp}.json')
    with open(result_filename, 'w', encoding='utf-8') as f:
        json.dump(ensure_correct_encoding(result_dict), f, ensure_ascii=False, indent=2)
    logging.info(f"Результат сохранен в файл: {result_filename}")

class PromptAnalyzer:
    def __init__(self):
        self.research_service = DeepResearchService()
        self.logs = []

    async def analyze_prompt_formation(self, query: str):
        """Анализирует формирование промпта для заданного запроса"""
        
        logging.info("\n🔍 Начинаем анализ формирования промпта")
        logging.info(f"Запрос пользователя:\n{query}")
        
        # 1. Поиск в ElasticSearch
        logging.info("\n=== Поиск в ElasticSearch ===")
        es_results = search_law_chunks(query)
        es_content = ""
        if es_results:
            # Отладочная информация
            logging.info("Структура первого результата из ElasticSearch:")
            if es_results and len(es_results) > 0:
                logging.info(f"Тип первого результата: {type(es_results[0])}")
                if isinstance(es_results[0], dict):
                    logging.info(f"Ключи в словаре: {es_results[0].keys()}")
                logging.info(f"Содержимое первого результата: {es_results[0]}")

            # Преобразуем результаты в строки и проверяем кодировку
            formatted_results = []
            for i, result in enumerate(es_results, 1):
                try:
                    # Если результат - словарь, пытаемся извлечь текст
                    if isinstance(result, dict):
                        # Проверяем различные возможные ключи
                        text = (result.get('text') or 
                               result.get('content') or 
                               result.get('source_text') or 
                               result.get('form_text') or 
                               str(result))
                    else:
                        text = str(result)
                    
                    # Проверяем и исправляем кодировку
                    fixed_text = ensure_correct_encoding(text)
                    formatted_results.append(f"Источник {i}:\n{fixed_text}")
                except Exception as e:
                    logging.error(f"Ошибка при обработке результата {i}: {str(e)}")
                    logging.error(f"Проблемный результат: {result}")
            
            es_content = "\n\n".join(formatted_results)
            logging.info(f"Найдено {len(es_results)} результатов в ElasticSearch")
            logging.info(f"Общий размер результатов ElasticSearch: {len(es_content)} символов")
        
        # 2. Поиск в интернете
        logging.info("\n=== Поиск в интернете ===")
        web_results = await search_and_scrape(query, self.logs)
        web_content = ""
        if web_results:
            # Проверяем кодировку веб-результатов
            web_content = "\n\n".join([
                f"Источник {i+1} ({result['url']}):\n{ensure_correct_encoding(result['text'])}"
                for i, result in enumerate(web_results)
            ])
            logging.info(f"Найдено {len(web_results)} результатов в интернете")
            logging.info(f"Общий размер результатов из интернета: {len(web_content)} символов")

        # 3. Формируем контекст
        additional_context = []
        if es_content:
            additional_context.append({
                "source": "elasticsearch",
                "data": es_content
            })
        if web_content:
            additional_context.append({
                "source": "web",
                "data": web_content
            })

        # Проверяем кодировку контекста
        additional_context = validate_context(additional_context)

        # 4. Отправляем запрос в DeepSeek и перехватываем промпт
        logging.info("\n=== Отправка запроса в DeepSeek ===")
        
        # Сохраняем оригинальный метод post
        original_post = self.research_service.deepseek_service.chat_completion
        
        # Создаем функцию для перехвата запроса
        async def intercepted_chat_completion(messages, **kwargs):
            # Отладочная информация о входящих сообщениях
            logging.info("\n=== Отладка сообщений ===")
            logging.info(f"Тип messages: {type(messages)}")
            
            # Создаем директорию для промптов, если её нет
            prompts_dir = 'prompts'
            if not os.path.exists(prompts_dir):
                os.makedirs(prompts_dir)
            
            # Сохраняем полное содержимое каждого сообщения в отдельный файл
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, msg in enumerate(messages):
                msg_file = os.path.join(prompts_dir, f'message_{timestamp}_{i+1}.txt')
                try:
                    with open(msg_file, 'w', encoding='utf-8') as f:
                        f.write(f"Role: {msg.get('role', 'unknown')}\n")
                        f.write(f"Content:\n{msg.get('content', '')}")
                    logging.info(f"Сообщение {i+1} сохранено в файл: {msg_file}")
                except Exception as e:
                    logging.error(f"Ошибка при сохранении сообщения {i+1}: {str(e)}")

            # Преобразуем сообщения в правильный формат и декодируем контент
            formatted_messages = []
            for msg in messages:
                try:
                    if isinstance(msg, dict):
                        role = str(msg.get('role', 'unknown'))
                        content = msg.get('content', '')
                        if not isinstance(content, str):
                            content = str(content)
                        # Декодируем контент
                        content = ensure_correct_encoding(content)
                    else:
                        role = 'unknown'
                        content = ensure_correct_encoding(str(msg))
                    
                    formatted_messages.append({
                        "role": role,
                        "content": content
                    })
                except Exception as e:
                    logging.error(f"Ошибка при форматировании сообщения: {str(e)}")
                    logging.error(f"Проблемное сообщение: {msg}")
            
            # Сохраняем полный промпт в JSON
            prompt_file = os.path.join(prompts_dir, f"deepseek_prompt_{timestamp}.json")
            
            # Анализируем параметры запроса
            model = kwargs.get('model', self.research_service.deepseek_service.model)
            temperature = kwargs.get('temperature', self.research_service.deepseek_service.temperature)
            max_tokens = kwargs.get('max_tokens', self.research_service.deepseek_service.max_tokens)
            
            try:
                prompt_data = {
                    "timestamp": timestamp,
                    "query": query,
                    "messages": formatted_messages,
                    "parameters": {
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    "context_info": {
                        "es_results_count": len(es_results) if es_results else 0,
                        "web_results_count": len(web_results) if web_results else 0,
                        "total_context_size": sum(len(msg.get('content', '')) for msg in formatted_messages)
                    }
                }
                
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    json.dump(prompt_data, f, ensure_ascii=False, indent=2)
                logging.info(f"💾 Полный промпт сохранен в файл: {prompt_file}")
                
                # Логируем размеры сообщений
                logging.info("\n=== Размеры сообщений ===")
                for i, msg in enumerate(formatted_messages):
                    logging.info(f"Сообщение {i+1} ({msg['role']}): {len(msg['content'])} символов")
                logging.info(f"Общий размер промпта: {prompt_data['context_info']['total_context_size']} символов")
                
            except Exception as e:
                logging.error(f"Ошибка при сохранении промпта: {str(e)}")
            
            # Вызываем оригинальный метод с отформатированными сообщениями
            try:
                return await original_post(formatted_messages, **kwargs)
            except Exception as e:
                logging.error(f"Ошибка при вызове original_post: {str(e)}")
                logging.error(f"formatted_messages: {formatted_messages}")
                raise

        # Подменяем метод
        self.research_service.deepseek_service.chat_completion = intercepted_chat_completion

        # Выполняем запрос
        result = await self.research_service.research(
            query=query,
            additional_context=additional_context
        )

        # Анализируем ответ
        logging.info("\n=== Анализ ответа DeepSeek ===")
        
        try:
            # Пытаемся декодировать каждое сообщение в ответе
            if isinstance(result.analysis, str):
                decoded_analysis = ensure_correct_encoding(result.analysis)
                result.analysis = decoded_analysis
                
                logging.info(f"Длина ответа: {len(decoded_analysis)} символов")
                logging.info(f"\nНачало ответа:\n{decoded_analysis[:500]}...\n")
                logging.info(f"\nКонец ответа:\n...{decoded_analysis[-500:]}")
            else:
                logging.warning(f"Неожиданный тип ответа: {type(result.analysis)}")
                
        except Exception as e:
            logging.error(f"Ошибка при декодировании ответа: {str(e)}")
            logging.info(f"Оригинальный ответ: {result.analysis}")

        return result

async def main():
    analyzer = PromptAnalyzer()
    
    # Тестовый запрос
    test_query = """
    Подготовь правовое заключение о возможности расторжения договора подряда 
    по статье 715 ГК РФ в связи с нарушением подрядчиком сроков выполнения работ. 
    Какие доказательства нужны? Как правильно оформить расторжение?
    """
    
    logging.info("\n🚀 Начинаем тестирование формирования промпта DeepSeek")
    
    try:
        result = await analyzer.analyze_prompt_formation(test_query)
        logging.info("\n✅ Тестирование завершено успешно")
        
        # Сохраняем результат в отдельный файл
        save_result_to_file({
            "query": test_query,
            "analysis": result.analysis,
            "timestamp": result.timestamp
        })
        
    except Exception as e:
        logging.error(f"\n❌ Ошибка при тестировании: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 