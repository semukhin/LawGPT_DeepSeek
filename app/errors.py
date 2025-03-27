from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime
import traceback

# Настройка логирования
logger = logging.getLogger(__name__)

async def universal_exception_handler(request: Request, exc: Exception):
    """Универсальный обработчик исключений"""
    # Логируем ошибку с трассировкой
    error_details = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Необработанное исключение: {error_details}")
    
    # Формируем сообщение об ошибке
    error_message = str(exc)
    
    # Возвращаем структурированную ошибку
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": error_message,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )

async def http_exception_handler_custom(request: Request, exc: StarletteHTTPException):
    """Обработчик HTTP исключений"""
    # Логируем HTTP ошибку
    logger.warning(f"HTTP ошибка {exc.status_code}: {exc.detail} на {request.url.path}")
    
    # Формируем ответ
    response = {
        "error": "HTTP Error",
        "status_code": exc.status_code,
        "message": exc.detail,
        "path": request.url.path,
        "timestamp": datetime.now().isoformat()
    }
    
    # Для API-запросов возвращаем JSON, для остальных - обычный обработчик
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=exc.status_code,
            content=response
        )
    else:
        # Используем стандартный обработчик
        return await http_exception_handler(request, exc)