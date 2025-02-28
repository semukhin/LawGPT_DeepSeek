"""
Модуль для аудита и мониторинга использования DeepResearch.
Позволяет отслеживать все вызовы и использования функций.
"""
import logging
import functools
import inspect
import json
import os
import time
import asyncio
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional

# Настроим логирование для аудита
audit_logger = logging.getLogger('deepresearch.audit')
audit_logger.setLevel(logging.INFO)

# Создаем специальный обработчик для аудита
audit_file_handler = logging.FileHandler('deepresearch_audit.log')
audit_file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
audit_logger.addHandler(audit_file_handler)

class DeepResearchAudit:
    """Класс для отслеживания использования DeepResearch."""
    
    def __init__(self, audit_dir: str = "deepresearch_audit"):
        """
        Инициализирует аудит DeepResearch.
        
        Args:
            audit_dir: Директория для сохранения аудит-файлов
        """
        self.audit_dir = audit_dir
        os.makedirs(audit_dir, exist_ok=True)
        self.usage_stats = {
            "methods": {},
            "modules": {},
            "total_calls": 0,
            "start_time": datetime.now().isoformat()
        }
    
    def audit_method(self, method: Callable) -> Callable:
        """
        Декоратор для аудита методов DeepResearch.
        
        Args:
            method: Метод для аудита
            
        Returns:
            Обернутый метод с аудитом
        """
        method_name = method.__name__
        module_name = method.__module__
        
        @functools.wraps(method)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            audit_logger.info(f"Вызов метода DeepResearch: {module_name}.{method_name}")
            
            # Запись в статистику
            self._update_stats(module_name, method_name)
            
            try:
                result = await method(*args, **kwargs)
                end_time = time.time()
                elapsed = end_time - start_time
                
                # Логирование успешного вызова
                audit_logger.info(
                    f"Успешное выполнение {module_name}.{method_name} за {elapsed:.2f} сек"
                )
                
                return result
            except Exception as e:
                audit_logger.error(
                    f"Ошибка при выполнении {module_name}.{method_name}: {str(e)}"
                )
                raise
        
        @functools.wraps(method)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            audit_logger.info(f"Вызов метода DeepResearch: {module_name}.{method_name}")
            
            # Запись в статистику
            self._update_stats(module_name, method_name)
            
            try:
                result = method(*args, **kwargs)
                end_time = time.time()
                elapsed = end_time - start_time
                
                # Логирование успешного вызова
                audit_logger.info(
                    f"Успешное выполнение {module_name}.{method_name} за {elapsed:.2f} сек"
                )
                
                return result
            except Exception as e:
                audit_logger.error(
                    f"Ошибка при выполнении {module_name}.{method_name}: {str(e)}"
                )
                raise
        
        if asyncio.iscoroutinefunction(method):
            return async_wrapper
        return sync_wrapper
    
    def _update_stats(self, module_name: str, method_name: str) -> None:
        """Обновляет статистику использования."""
        # Обновляем счетчик модуля
        if module_name not in self.usage_stats["modules"]:
            self.usage_stats["modules"][module_name] = 0
        self.usage_stats["modules"][module_name] += 1
        
        # Обновляем счетчик метода
        method_key = f"{module_name}.{method_name}"
        if method_key not in self.usage_stats["methods"]:
            self.usage_stats["methods"][method_key] = 0
        self.usage_stats["methods"][method_key] += 1
        
        # Обновляем общий счетчик
        self.usage_stats["total_calls"] += 1
        
        # Сохраняем статистику каждые 10 вызовов
        if self.usage_stats["total_calls"] % 10 == 0:
            self.save_stats()
    
    def save_stats(self) -> None:
        """Сохраняет статистику использования в файл."""
        stats_path = os.path.join(self.audit_dir, "usage_stats.json")
        self.usage_stats["last_update"] = datetime.now().isoformat()
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.usage_stats, f, ensure_ascii=False, indent=2)
    
    def get_unused_methods(self, module_list: List[str]) -> Dict[str, List[str]]:
        """
        Определяет неиспользуемые методы DeepResearch.
        
        Args:
            module_list: Список модулей для проверки
            
        Returns:
            Словарь с неиспользуемыми методами по модулям
        """
        unused = {}
        
        for module_name in module_list:
            try:
                module = __import__(module_name, fromlist=['*'])
                module_methods = [
                    name for name, obj in inspect.getmembers(module) 
                    if inspect.isfunction(obj) or inspect.ismethod(obj)
                ]
                
                # Проверяем, какие методы не использовались
                unused_methods = []
                for method_name in module_methods:
                    method_key = f"{module_name}.{method_name}"
                    if method_key not in self.usage_stats["methods"]:
                        unused_methods.append(method_name)
                
                if unused_methods:
                    unused[module_name] = unused_methods
            except ImportError:
                audit_logger.warning(f"Не удалось импортировать модуль {module_name}")
        
        return unused
    
    def print_stats(self) -> None:
        """Выводит статистику использования."""
        total_calls = self.usage_stats["total_calls"]
        module_stats = self.usage_stats["modules"]
        method_stats = self.usage_stats["methods"]
        
        print("\n===== Статистика использования DeepResearch =====")
        print(f"Всего вызовов: {total_calls}")
        print("\nИспользование по модулям:")
        for module, count in sorted(module_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_calls) * 100 if total_calls > 0 else 0
            print(f"  {module}: {count} вызовов ({percentage:.1f}%)")
        
        print("\nТоп-10 используемых методов:")
        for method, count in sorted(method_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / total_calls) * 100 if total_calls > 0 else 0
            print(f"  {method}: {count} вызовов ({percentage:.1f}%)")

# Создаем глобальный экземпляр аудита
deepresearch_audit = DeepResearchAudit()

# Декоратор для простого использования
def audit_deepresearch(func):
    """Декоратор для аудита функций DeepResearch."""
    return deepresearch_audit.audit_method(func)

if __name__ == "__main__":
    # Тестируем аудит
    print("Тестирование модуля аудита DeepResearch")
    
    # Тестовая функция
    @audit_deepresearch
    def test_function():
        print("Эта функция выполняется с аудитом")
        return "Test completed"
    
    # Запуск тестовой функции
    result = test_function()
    print(f"Результат выполнения: {result}")
    
    # Показываем статистику
    deepresearch_audit.print_stats()