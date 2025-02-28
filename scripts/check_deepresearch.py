#!/usr/bin/env python3
"""
Скрипт для проверки полноты использования и корректности работы DeepResearch.
Запускайте этот скрипт периодически для анализа использования функциональности.
"""
import os
import sys
import importlib
import inspect
import json
import argparse
import asyncio
from datetime import datetime
import logging

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Получаем путь к проекту
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

# Импортируем нужные модули
from app.handlers.deepresearch_audit import deepresearch_audit
from app.services.deepresearch_service import DeepResearchService

def discover_deepresearch_modules():
    """Находит все модули и классы, связанные с DeepResearch."""
    import app
    
    deepresearch_modules = []
    
    for root, dirs, files in os.walk(os.path.dirname(app.__file__)):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                module_path = os.path.join(root, file)
                module_name = module_path.replace(os.path.dirname(app.__file__) + os.sep, '')
                module_name = module_name.replace(os.sep, '.').replace('.py', '')
                module_name = f"app.{module_name}"
                
                try:
                    module = importlib.import_module(module_name)
                    has_deepresearch = False
                    
                    # Ищем DeepResearch в коде модуля
                    with open(module_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'DeepResearch' in content or 'deepresearch' in content.lower():
                            has_deepresearch = True
                    
                    if has_deepresearch:
                        deepresearch_modules.append(module_name)
                        
                        # Получаем все классы и методы связанные с DeepResearch
                        for name, obj in inspect.getmembers(module):
                            if name == "DeepResearchService" or "DeepResearch" in name:
                                if inspect.isclass(obj):
                                    for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                                        if not method_name.startswith('_'):
                                            print(f"Найден метод DeepResearch: {module_name}.{name}.{method_name}")
                
                except ImportError as e:
                    logging.warning(f"Не удалось импортировать модуль {module_name}: {e}")
    
    return deepresearch_modules

def run_test_queries():
    """Запускает тестовые запросы для проверки DeepResearch."""
    service = DeepResearchService()
    
    test_queries = [
        "Предоставь информацию о законе о защите прав потребителей",
        "Какие изменения в ГК РФ произошли за последний год?",
        "Как подать иск о защите интеллектуальной собственности?",
        # Можно добавить больше запросов для разных сценариев
    ]
    
    async def run_tests():
        for query in test_queries:
            try:
                logging.info(f"Тестовый запрос: {query}")
                result = await service.research(query)
                logging.info(f"Успешный результат, длина анализа: {len(result.analysis)}")
            except Exception as e:
                logging.error(f"Ошибка при запросе '{query}': {e}")
    
    # Запускаем тесты
    asyncio.run(run_tests())

def check_unused_functionality():
    """Проверяет, какие функции DeepResearch не используются."""
    deepresearch_modules = discover_deepresearch_modules()
    
    # Проверяем статистику использования
    if os.path.exists('deepresearch_audit/usage_stats.json'):
        with open('deepresearch_audit/usage_stats.json', 'r') as f:
            stats = json.load(f)
        
        total_calls = stats.get('total_calls', 0)
        logging.info(f"Всего вызовов DeepResearch: {total_calls}")
        
        if total_calls == 0:
            logging.warning("⚠️ DeepResearch не использовался с момента включения аудита!")
        
        # Находим неиспользуемые методы
        unused = deepresearch_audit.get_unused_methods(deepresearch_modules)
        if unused:
            logging.warning("⚠️ Найдены неиспользуемые методы DeepResearch:")
            for module, methods in unused.items():
                for method in methods:
                    logging.warning(f"  - {module}.{method}")
        else:
            logging.info("✅ Все найденные методы DeepResearch используются")
    else:
        logging.warning("⚠️ Статистика использования DeepResearch не найдена. Запустите приложение с аудитом.")


def main():
    """Основная функция для проверки DeepResearch."""
    parser = argparse.ArgumentParser(description="Проверка функциональности DeepResearch")
    parser.add_argument("--discover", action="store_true", help="Обнаружить все модули DeepResearch")
    parser.add_argument("--check-unused", action="store_true", help="Проверить неиспользуемые функции")
    parser.add_argument("--stats", action="store_true", help="Показать статистику использования")
    
    args = parser.parse_args()
    
    if args.discover:
        logging.info("Обнаружение модулей DeepResearch...")
        modules = discover_deepresearch_modules()
        logging.info(f"Найдено {len(modules)} модулей DeepResearch: {', '.join(modules)}")
    
    if args.check_unused:  
        logging.info("Проверка неиспользуемых функций...")
        check_unused_functionality()
    
    if args.stats:
        logging.info("Статистика использования DeepResearch:")
        deepresearch_audit.print_stats()
    
    # Если никаких аргументов не указано, выполняем все проверки
    if not (args.discover or args.check_unused or args.stats): 
        logging.info("Выполнение всех проверок...")
        discover_deepresearch_modules()
        check_unused_functionality()
        deepresearch_audit.print_stats()
        

if __name__ == "__main__":
    main()