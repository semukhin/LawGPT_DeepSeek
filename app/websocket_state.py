"""
Модуль для хранения общего состояния WebSocket подключений.
Используется для избежания циклических импортов между основными модулями.
"""
from typing import List
from fastapi import WebSocket

# Список для хранения активных WebSocket подключений
connected_clients: List[WebSocket] = []