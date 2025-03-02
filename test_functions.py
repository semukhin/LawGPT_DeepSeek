#!/usr/bin/env python3
import sys
import importlib.util

"""
Тестовый скрипт для проверки работы функций DeepSeek API.
Проверяет:
1. Function calling
2. Поиск в ElasticSearch (search_law_chunks)
3. Поиск в интернете (search_web)
4. Глубокое исследование (deep_research)
5. Поиск в Гаранте (search_garant)
"""
import os
import sys
import asyncio
import json
import logging

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_functions.log", mode="w")
    ]
)

try:
    # Попытка прямого импорта
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Переменные окружения загружены из .env файла")
except ImportError:
    try:
        # Попытка найти модуль в системных путях
        spec = importlib.util.find_spec("dotenv")
        if spec:
            dotenv = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dotenv)
            dotenv.load_dotenv()
            print("✅ Переменные окружения загружены из .env файла (альтернативный метод)")
        else:
            raise ImportError("Модуль dotenv не найден")
    except Exception as e:
        print(f"⚠️ python-dotenv не установлен, используются только переменные окружения системы ({e})")
        print("Для установки: pip install python-dotenv")

# Добавляем путь к проекту для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Проверка наличия API ключа перед импортом модулей
try:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ API ключ DeepSeek не найден в переменных окружения")
        print("Установите переменную окружения DEEPSEEK_API_KEY или создайте файл .env с этой переменной")
except Exception as e:
    print(f"❌ Ошибка при проверке API ключа: {e}")

# Импортируем модули проекта
try:
    from app.services.deepseek_service import DeepSeekService
    from app.handlers.ai_request import AVAILABLE_FUNCTIONS, handle_function_call
    print("✅ Модули проекта успешно импортированы")
except Exception as e:
    print(f"❌ Ошибка при импорте модулей проекта: {e}")
    sys.exit(1)


async def test_function_calling():
    """
    Тестирует механизм function calling DeepSeek API.
    """
    print("\n" + "=" * 50)
    print("ТЕСТ FUNCTION CALLING")
    print("=" * 50)
    
    # Проверяем наличие API ключа
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ API ключ не найден, тест пропущен")
        return
    
    # Создаем экземпляр сервиса
    try:
        deepseek = DeepSeekService(temperature=0.1)  # Низкая температура для более детерминированных ответов
    except Exception as e:
        print(f"❌ Не удалось создать экземпляр DeepSeekService: {e}")
        return
    
    # Подготовка примера запроса
    query = "Найди в законодательстве информацию о расторжении договора подряда"
    
    # Подготовка сообщений
    messages = [
        {
            "role": "system", 
            "content": """Ты - юридический ассистент, который отвечает на вопросы по российскому законодательству.
ОЧЕНЬ ВАЖНО: ты ДОЛЖЕН использовать доступные функции для ответа.
НЕ отвечай на юридические вопросы своими знаниями, обязательно используй функции.
Сначала вызови функцию search_law_chunks для поиска в законодательстве."""
        },
        {"role": "user", "content": query}
    ]
    
    print(f"Запрос: {query}")
    print(f"Доступные функции: {[f['name'] for f in AVAILABLE_FUNCTIONS]}")
    
    try:
        # Отправляем запрос
        print("\nОтправка запроса с function_call='auto'...")
        response = await deepseek.chat_with_functions(
            messages=messages,
            functions=AVAILABLE_FUNCTIONS,
            function_call="auto"
        )
        
        print("\nОтвет API:")
        print(f"Тип ответа: {type(response)}")
        
        if isinstance(response, dict) and 'choices' in response:
            choice = response['choices'][0]
            message = choice.get('message', {})
            
            print(f"Ключи сообщения: {list(message.keys())}")
            
            if 'function_call' in message:
                function_call = message['function_call']
                function_name = function_call.get('name')
                function_args = function_call.get('arguments', '{}')
                
                print(f"\n✅ Функция вызвана успешно: {function_name}")
                print(f"Аргументы: {function_args}")
                
                # Выполняем функцию
                try:
                    args = json.loads(function_args)
                    print(f"\nВыполнение функции {function_name}...")
                    result = await handle_function_call(function_name, args)
                    
                    print(f"Результат функции:")
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                    print(result_str[:500] + "..." if len(result_str) > 500 else result_str)
                    
                    # Добавляем результат функции в сообщения
                    messages.append({
                        "role": "assistant",
                        "content": message.get('content', ''),
                        "function_call": {
                            "name": function_name,
                            "arguments": function_args
                        }
                    })
                    
                    messages.append({
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
                    # Получаем финальный ответ
                    print("\nПолучение финального ответа...")
                    final_response = await deepseek.chat_completion(messages)
                    
                    if isinstance(final_response, dict) and 'choices' in final_response:
                        final_text = final_response['choices'][0]['message']['content']
                        print(f"\nФинальный ответ:")
                        print(final_text[:500] + "..." if len(final_text) > 500 else final_text)
                    else:
                        print(f"\nНеожиданный формат финального ответа: {type(final_response)}")
                
                except Exception as e:
                    print(f"\n❌ Ошибка при выполнении функции: {e}")
            else:
                print("\n❌ Function call не обнаружен в ответе")
                print(f"Содержимое сообщения:")
                print(message.get('content', 'Нет содержимого')[:500] + "..." if len(message.get('content', '')) > 500 else message.get('content', 'Нет содержимого'))
                
                # Пробуем с принудительным вызовом функции
                print("\nПробуем с принудительным вызовом функции...")
                try:
                    forced_response = await deepseek.chat_with_functions(
                        messages=messages,
                        functions=AVAILABLE_FUNCTIONS,
                        function_call={"name": "search_law_chunks"}
                    )
                    
                    if isinstance(forced_response, dict) and 'choices' in forced_response:
                        forced_choice = forced_response['choices'][0]
                        forced_message = forced_choice.get('message', {})
                        
                        if 'function_call' in forced_message:
                            forced_function_call = forced_message['function_call']
                            print(f"\n✅ Принудительный вызов функции успешен: {forced_function_call.get('name')}")
                        else:
                            print("\n❌ Принудительный вызов функции не сработал")
                except Exception as e:
                    print(f"\n❌ Ошибка при принудительном вызове функции: {e}")
        else:
            print(f"\n❌ Неожиданный формат ответа: {response}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста function calling: {e}")

async def test_search_law_chunks():
    """
    Тестирует функцию поиска в законодательстве (ElasticSearch).
    """
    print("\n" + "=" * 50)
    print("ТЕСТ ПОИСКА В ЗАКОНОДАТЕЛЬСТВЕ")
    print("=" * 50)
    
    query = "Расторжение договора подряда согласно статье 715 ГК РФ"
    print(f"Запрос: {query}")
    
    try:
        result = await handle_function_call("search_law_chunks", {"query": query})
        
        print("\nРезультат поиска в законодательстве:")
        if result.get("found"):
            print(f"✅ Найдено {result.get('chunks_count')} релевантных фрагментов")
            deep_research = result.get("deep_research_results", {})
            analysis = deep_research.get("analysis", "")
            print("\nАнализ результатов:")
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста поиска в законодательстве: {e}")

async def test_search_web():
    """
    Тестирует функцию поиска в интернете.
    """
    print("\n" + "=" * 50)
    print("ТЕСТ ПОИСКА В ИНТЕРНЕТЕ")
    print("=" * 50)
    
    query = "Обзор судебной практики по расторжению договоров поставки за 2023 год"
    print(f"Запрос: {query}")
    
    try:
        result = await handle_function_call("search_web", {"query": query})
        
        print("\nРезультат поиска в интернете:")
        if result.get("found"):
            print(f"✅ Найдено {result.get('sources_count')} релевантных источников")
            print("\nИсточники:")
            for i, source in enumerate(result.get("sources", []), 1):
                print(f"{i}. {source.get('title', 'Без названия')} - {source.get('url', 'Без URL')}")
            
            deep_research = result.get("deep_research_results", {})
            analysis = deep_research.get("analysis", "")
            print("\nАнализ результатов:")
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста поиска в интернете: {e}")

async def test_deep_research():
    """
    Тестирует функцию глубокого исследования.
    """
    print("\n" + "=" * 50)
    print("ТЕСТ ГЛУБОКОГО ИССЛЕДОВАНИЯ")
    print("=" * 50)
    
    query = "Анализ судебной практики по спорам о расторжении договоров подряда за 2022-2023 годы"
    print(f"Запрос: {query}")
    
    try:
        result = await handle_function_call("deep_research", {"query": query})
        
        print("\nРезультат глубокого исследования:")
        if result.get("found"):
            deep_research = result.get("deep_research_results", {})
            analysis = deep_research.get("analysis", "")
            print("\nАнализ результатов:")
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста глубокого исследования: {e}")

async def test_search_garant():
    """
    Тестирует функцию поиска в Гаранте.
    """
    print("\n" + "=" * 50)
    print("ТЕСТ ПОИСКА В ГАРАНТЕ")
    print("=" * 50)
    
    query = "Судебная практика по договорам подряда в 2023 году"
    print(f"Запрос: {query}")
    
    try:
        result = await handle_function_call("search_garant", {"query": query})
        
        print("\nРезультат поиска в Гаранте:")
        if result and isinstance(result, dict):
            docx_path = result.get("docx_file_path")
            document_url = result.get("document_url")
            
            if docx_path and document_url:
                print(f"✅ Документ найден:")
                print(f"Путь к DOCX: {docx_path}")
                print(f"URL документа: {document_url}")
                
                # Попытка извлечь текст из документа
                try:
                    from app.handlers.user_doc_request import extract_text_from_any_document
                    extracted_text = extract_text_from_any_document(docx_path)
                    print("\nИзвлеченный текст:")
                    print(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
                except Exception as e:
                    print(f"❌ Ошибка извлечения текста: {e}")
            else:
                print("❌ Не удалось получить путь к документу или URL")
        else:
            print(f"❌ Ошибка: {result}")
    
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста поиска в Гаранте: {e}")

async def main():
    """
    Основная функция для запуска всех тестов.
    """
    # Проверяем наличие API ключа
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ Ошибка: Переменная окружения DEEPSEEK_API_KEY не установлена")
        print("Создайте файл .env и добавьте в него строку:")
        print("DEEPSEEK_API_KEY=your_api_key")
        return
    
    print("🔍 Запуск тестов функций DeepSeek API")
    
    # Запускаем тесты
    await test_function_calling()
    await test_search_law_chunks()
    await test_search_web()
    await test_deep_research()
    await test_search_garant()  # Добавлен новый тест для Гаранта
    
    print("\n✅ Тестирование завершено")
    print("📋 Подробные логи сохранены в файле test_functions.log")

if __name__ == "__main__":
    asyncio.run(main())