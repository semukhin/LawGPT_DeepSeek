#!/usr/bin/env python3
"""
Скрипт для инициализации статистики DeepResearch.
Создает директорию и начальный файл статистики.
"""
import os
import json
import sys
from datetime import datetime

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем аудит
try:
    from app.handlers.deepresearch_audit import deepresearch_audit
except ImportError:
    print("Не удалось импортировать модуль deepresearch_audit.")
    print("Убедитесь, что скрипт запускается из корня проекта.")
    sys.exit(1)

def initialize_stats():
    """Инициализирует статистику DeepResearch."""
    stats_dir = "deepresearch_audit"
    stats_file = os.path.join(stats_dir, "usage_stats.json")
    
    print(f"Создание директории для статистики: {stats_dir}")
    os.makedirs(stats_dir, exist_ok=True)
    
    if not os.path.exists(stats_file):
        print(f"Создание начального файла статистики: {stats_file}")
        
        initial_stats = {
            "methods": {},
            "modules": {},
            "total_calls": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(initial_stats, f, ensure_ascii=False, indent=2)
        
        print("✅ Файл статистики успешно создан")
    else:
        print(f"✅ Файл статистики уже существует: {stats_file}")
        
    # Вызываем метод save_stats для обновления статистики
    deepresearch_audit.save_stats()
    print("✅ Статистика DeepResearch инициализирована")

if __name__ == "__main__":
    initialize_stats()
