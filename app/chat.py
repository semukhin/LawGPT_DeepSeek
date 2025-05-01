from openai import OpenAI
import uuid
import os
import re
import logging
import asyncio
import json
from datetime import datetime
from pathlib import Path
import unicodedata

from fastapi import Request, UploadFile, File, Form, HTTPException, FastAPI, APIRouter, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import aiofiles
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Message, Thread, Document
from app.auth import get_current_user
from app.handlers.web_search import google_search
from app.handlers.ai_request import send_custom_request
from app.handlers.es_law_search import search_law_chunks
from app.handlers.user_doc_request import extract_text_from_any_document, process_uploaded_file
from app.utils import measure_time
from transliterate import translit
from app.utils.text_utils import decode_unicode
from app.utils.chat_utils import get_messages

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Папки для хранения файлов
UPLOAD_FOLDER = "uploads"
DOCX_FOLDER = "documents_docx"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCX_FOLDER, exist_ok=True)

# OAuth2 схема для авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Инициализация FastAPI
app = FastAPI(
    title="LawGPT Chat API",
    description=
    "API для обработки чатов с использованием DeepResearch и других источников.",
    version="2.0.0")

router = APIRouter()

# ===================== Модели запросов =====================


class ChatRequest(BaseModel):
    query: str


# ===================== Вспомогательные функции =====================


@measure_time
async def process_chat_uploaded_file(
        file: UploadFile) -> tuple[str, str, dict]:
    """
    Сохраняет загруженный файл и извлекает из него текст.

    Args:
        file: Загруженный файл от пользователя

    Returns:
        tuple[str, str, dict]: Кортеж из (путь_к_файлу, извлеченный_текст, метаданные_файла)
    """
    # Импортируем функцию из handlers, чтобы избежать рекурсии
    from app.handlers.user_doc_request import process_uploaded_file as handler_process_file

    file_path, extracted_text, file_metadata = await handler_process_file(file)

    # Логируем информацию о результате
    if file_path:
        logging.info("Файл сохранён: %s", file_path)
        if extracted_text:
            logging.info(
                "Извлечённый текст из файла: %s",
                extracted_text[:200])  # Показываем первые 200 символов

    return file_path, extracted_text, file_metadata


def fix_encoding(query: str) -> str:
    """Исправление кодировки запроса"""
    try:
        # Пробуем декодировать как UTF-8
        query.encode('utf-8').decode('utf-8')
        # Если успешно, применяем decode_unicode
        return decode_unicode(query)
    except UnicodeError:
        try:
            # Если не получилось, пробуем через latin1
            query = query.encode('latin1').decode('utf-8')
            # Применяем decode_unicode
            return decode_unicode(query)
        except Exception as e:
            logging.error(f"Ошибка при исправлении кодировки: {str(e)}")
            return query


# ===================== Эндпоинты чата =====================
@measure_time
@router.post("/api/chat/{thread_id}")
async def chat_in_thread(
        request: Request,
        thread_id: str,
        query: str = Form(None),
        file: UploadFile = File(None),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Основной эндпоинт для общения с ассистентом.

    Новая логика:
    1. Если загружен только файл (без текстового запроса) — просто извлекает текст и возвращает его.
    2. Если загружен файл с текстовым запросом — сначала возвращает распознанный текст, 
       а затем выполняет задание из запроса.
    3. Если только текстовый запрос без файла — обрабатывает запрос обычным способом.
    """
    # Проверка и обработка случая, когда query равен None
    if query is None and file is None:
        raise HTTPException(
            status_code=400,
            detail="Необходимо предоставить текстовый запрос или файл")

    # Если query None, но файл есть, устанавливаем пустой запрос
    query = query or ""

    # 1. Проверка и нормализация текста запроса
    try:
        # Исправляем кодировку запроса
        query = fix_encoding(query)

        # Нормализация Unicode для решения проблем с составными символами
        query = unicodedata.normalize('NFC', query)

        # Логируем запрос, ограничивая длину для читаемости
        log_query = query[:100] + "..." if len(query) > 100 else query
        logging.info(
            f"📥 Получен запрос: thread_id={thread_id}, query='{log_query}'")
    except Exception as e:
        logging.error(f"❌ Ошибка декодирования запроса: {str(e)}")
        # Попытка исправить кодировку, если она неправильная
        try:
            query = query.encode('latin1').decode('utf-8')
            logging.info(f"✅ Исправлена кодировка запроса")
        except Exception as e:
            logging.error(f"❌ Не удалось исправить кодировку: {str(e)}")
            query = ""  # Устанавливаем пустой запрос

    # 2. Проверка кодировки перед дальнейшей обработкой
    if isinstance(query, str):
        # Убедимся, что query действительно строка в UTF-8
        try:
            query.encode('utf-8').decode('utf-8')
        except UnicodeError:
            logging.warning(
                "⚠️ Проблема с кодировкой в тексте запроса, пытаемся исправить"
            )
            # Дополнительная попытка исправить кодировку
            try:
                query = query.encode('latin1').decode('utf-8',
                                                      errors='replace')
            except:
                pass

    # 3. Проверка и исправление thread_id
    # Если thread_id буквально равен 'thread_id' или не соответствует формату UUID
    uuid_pattern = re.compile(r'^thread_[0-9a-f]{32}$')
    if thread_id == 'thread_id' or (not uuid_pattern.match(thread_id)
                                    and not thread_id.startswith('existing_')):
        # Создаем новый thread_id
        new_thread_id = f"thread_{uuid.uuid4().hex}"
        logging.info(
            f"⚠️ Получен некорректный thread_id: {thread_id}. Создан новый: {new_thread_id}"
        )
        thread_id = new_thread_id

    # 4. Поиск или создание треда
    thread = db.query(Thread).filter_by(id=thread_id,
                                        user_id=current_user.id).first()
    if not thread:
        logging.info("🔑 Тред не найден. Создаем новый.")
        thread = Thread(id=thread_id, user_id=current_user.id)
        db.add(thread)
        db.commit()

    # 5. Обработка файла (если есть)
    if file:
        logging.info(f"📄 Обработка загруженного файла: {file.filename}")
        file_path, extracted_text, file_metadata = await process_chat_uploaded_file(
            file)

        # Создаем информативное сообщение о загруженном документе
        file_info = (
            f"Документ: {file.filename}\n"
            f"Размер: {file_metadata.get('file_size_formatted', 'неизвестно')}\n"
            f"Тип: {file_metadata.get('extension', 'неизвестно')}")

        # Формируем ответ с распознанным текстом
        text_preview = extracted_text[:5000] + "..." if len(
            extracted_text) > 5000 else extracted_text

        # Формируем информацию о сохраненном файле
        saved_filename = os.path.basename(file_metadata.get("recognized_text_file_txt", ""))
        download_url = f"/api/download/{saved_filename}"
        file_metadata.update({
            "download_url": download_url,
            "saved_filename": saved_filename,
            "file_size_formatted": file_metadata.get("file_size_formatted", ""),
            "char_count": file_metadata.get("char_count", 0),
            "word_count": file_metadata.get("word_count", 0)
        })

        # Формируем ссылку на скачивание с полной информацией
        download_link = (
            f"\n\n**Распознанный текст сохранен:**\n"
            f"- Имя файла: `{saved_filename}`\n"
            f"- Размер: {file_metadata.get('file_size_formatted')}\n"
            f"- Символов: {file_metadata.get('char_count')}\n"
            f"- Слов: {file_metadata.get('word_count')}\n"
            f"\n[Скачать распознанный текст]({download_url})"
        )

        recognized_text_response = (
            f"**Распознанный текст из файла {file.filename}:**\n\n"
            f"```\n{text_preview}\n```\n\n"
            f"*Распознано {file_metadata.get('char_count', 0)} символов, "
            f"{file_metadata.get('word_count', 0)} слов.*{download_link}")

        # Сохраняем сообщение пользователя и ответ с распознанным текстом
        db.add_all([
            Message(thread_id=thread_id, role="user", content=file_info),
            Message(thread_id=thread_id,
                    role="assistant",
                    content=recognized_text_response)
        ])
        db.commit()

        # Возвращаем результат с полными метаданными
        result = {
            "assistant_response": recognized_text_response,
            "recognized_text": extracted_text,
            "file_name": file.filename,
            "file_path": file_path,
            "file_metadata": file_metadata,
            "success": True,
            "text": extracted_text,
            "download_url": download_url,
            "saved_filename": saved_filename
        }

        # Если есть текстовый запрос (не пустой), обрабатываем его как обычное задание,
        # но с учетом контекста файла
        assistant_response = None
        if query.strip():
            logging.info(
                "💬 Обработка текстового запроса с учетом загруженного файла.")

            # Создаем запрос с учетом содержимого документа
            enhanced_query = f"{query}\n\nДокумент содержит:\n{extracted_text[:3000]}..."

            # Получаем ответ ассистента
            # Функция send_custom_request уже сохраняет сообщения в DB
            assistant_response = await send_custom_request(
                user_query=enhanced_query, thread_id=thread_id, db=db)

        # Обновляем first_message треда, если он пустой
        if not thread.first_message:
            thread.first_message = file.filename
            db.commit()

        # Если был обработан дополнительный запрос, добавляем его в результат
        if assistant_response:
            result["additional_response"] = assistant_response

        return result
    else:
        # 6. Обработка только текстового запроса (без файла)
        logging.info("💬 Обработка текстового запроса без файла.")

        # Передаем thread_id и db в send_custom_request
        assistant_response = await send_custom_request(user_query=query,
                                                       thread_id=thread_id,
                                                       db=db)

        # Обновляем first_message треда, если он пустой
        if not thread.first_message and query:
            thread.first_message = query[:100] + ('...'
                                                  if len(query) > 100 else '')
            db.commit()

        return {"assistant_response": assistant_response}


# ===================== Эндпоинты работы с тредами =====================


@measure_time
@router.post("/api/create_thread")
async def create_thread(current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Создает новый тред для пользователя."""
    import uuid
    new_thread_id = f"thread_{uuid.uuid4().hex}"
    thread = Thread(id=new_thread_id, user_id=current_user.id)
    db.add(thread)
    db.commit()
    logging.info(f"🆕 Создан новый тред: {new_thread_id}")
    return {"thread_id": new_thread_id}


@measure_time
@router.get("/api/chat/threads")
async def get_threads(current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    threads = db.query(Thread).filter_by(user_id=current_user.id).order_by(
        Thread.created_at.desc()).all()

    # Добавляем first_message в возвращаемые данные
    return {
        "threads": [{
            "id": t.id,
            "created_at": t.created_at,
            "first_message": t.first_message
        } for t in threads]
    }


@measure_time
@router.get("/api/messages/{thread_id}")
async def get_thread_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает сообщения из выбранного треда."""
    return await get_messages(thread_id=thread_id, db=db)


# ===================== Эндпоинты для загрузки и скачивания файлов =====================


@router.post("/api/download_recognized_text")
async def download_recognized_text(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """Скачивание распознанного текста с авторизацией."""
    try:
        # Логируем все заголовки для отладки
        headers_log = {k: v for k, v in request.headers.items()}
        logging.info(
            f"📥 Заголовки запроса download_recognized_text: {headers_log}")

        # Определяем тип содержимого запроса
        content_type = request.headers.get("content-type", "")
        logging.info(f"📄 Тип содержимого запроса: {content_type}")

        # Получаем данные в зависимости от типа содержимого
        file_path = None

        if "application/json" in content_type:
            # Для JSON запросов
            try:
                body_data = await request.json()
                logging.info(
                    f"📥 Тело запроса download_recognized_text (JSON): {body_data}"
                )
                file_path = body_data.get("file_path")

                # Проверяем, нет ли у нас прямого пути к output_documents
                if file_path and not os.path.exists(file_path):
                    possible_paths = [
                        os.path.join("output_documents", file_path),
                        os.path.join("output_documents",
                                     os.path.basename(file_path))
                    ]

                    for possible_path in possible_paths:
                        if os.path.exists(possible_path):
                            file_path = possible_path
                            logging.info(
                                f"✅ Найден альтернативный путь: {file_path}")
                            break

            except json.JSONDecodeError as e:
                logging.error(f"❌ Ошибка декодирования JSON: {str(e)}")
                raise HTTPException(status_code=400,
                                    detail="Неверный формат JSON")

        elif "multipart/form-data" in content_type:
            # Для multipart/form-data запросов
            form_data = await request.form()
            logging.info(
                f"📥 Тело запроса download_recognized_text (form-data): {form_data}"
            )

            # Проверяем, пришел ли файл или путь к файлу
            if "file_path" in form_data:
                file_path = form_data.get("file_path")
            elif "file_content" in form_data and "file_name" in form_data:
                # Если получаем контент файла и имя, создаем временный файл и возвращаем его
                original_filename = form_data.get("file_name", "recognized_text.txt")
                name_without_ext, _ = os.path.splitext(original_filename)
                txt_filename = f"{name_without_ext}.txt"
                return await create_and_return_file(
                    form_data.get("file_content"), txt_filename)
        else:
            # Пытаемся прочитать тело запроса как обычные данные
            raw_body = await request.body()
            logging.info(
                f"📥 Тело запроса как сырые данные (размер: {len(raw_body)} байт)"
            )

            # Если указан URL-параметр file_path
            file_path = request.query_params.get("file_path")

        logging.info(f"📄 Запрошенный файл: {file_path}")

        if not file_path:
            logging.error("❌ Отсутствует путь к файлу")
            raise HTTPException(status_code=400,
                                detail="Отсутствует путь к файлу")

        # Проверяем варианты путей к файлу
        possible_paths = [
            file_path,
            file_path.lstrip('/'),
            os.path.join(os.getcwd(), file_path.lstrip('/')),
            os.path.join("output_documents", os.path.basename(file_path)),
            os.path.join("output_documents", file_path.lstrip('/'))
        ]

        found = False
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                found = True
                logging.info(f"✅ Файл найден: {file_path}")
                break

        if not found:
            # Специальная обработка для документов в output_documents
            # Попробуем найти файлы с похожими именами в output_documents
            try:
                base_name = os.path.basename(file_path)
                output_dir = "output_documents"
                if os.path.exists(output_dir):
                    all_files = os.listdir(output_dir)
                    # Найдем файлы, которые содержат базовое имя
                    matching_files = [f for f in all_files if base_name in f]
                    if matching_files:
                        file_path = os.path.join(output_dir, matching_files[0])
                        found = True
                        logging.info(f"✅ Найден похожий файл: {file_path}")
            except Exception as e:
                logging.warning(f"⚠️ Ошибка при поиске похожих файлов: {e}")

        if not found:
            logging.error(
                f"❌ Файл не найден: {file_path} (проверены пути: {possible_paths})"
            )
            raise HTTPException(status_code=404,
                                detail=f"Файл не найден: {file_path}")

        # Определяем тип контента по расширению
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext.lower() == '.txt':
            content_type = 'text/plain'
        else:
            content_type = 'application/octet-stream'

        # Определяем имя файла для заголовка Content-Disposition
        filename = os.path.basename(file_path)
        logging.info(f"📤 Отправка файла: {filename} (тип: {content_type})")

        # Возвращаем FileResponse
        return FileResponse(path=file_path,
                            media_type=content_type,
                            filename=filename)
    except json.JSONDecodeError as e:
        logging.error(f"❌ Ошибка декодирования JSON: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400,
                            detail="Некорректный JSON в теле запроса")
    except Exception as e:
        logging.error(f"❌ Ошибка при скачивании файла: {str(e)}",
                      exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Ошибка при скачивании файла: {str(e)}")


@measure_time
@router.post("/api/upload_file")
async def upload_file(file: UploadFile = File(...),
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    """Загружает файл и сохраняет в базе данных."""
    if not file.filename.lower().endswith(
        ('.pdf', '.doc', '.docx', '.xlsx', '.jpg', '.jpeg', '.tif', '.tiff')):
        raise HTTPException(
            status_code=400,
            detail=
            "Поддерживаются только файлы .pdf, .doc, .docx, .xlsx, .jpg, .jpeg, .tif, .tiff"
        )

    file_path, extracted_text, file_metadata = await process_uploaded_file(file
                                                                           )

    # Save full extracted text to a .txt file
    extracted_filename = os.path.basename(file_path)
    filename_no_ext, _ = os.path.splitext(extracted_filename)
    txt_file_path = os.path.join("uploads", f"{filename_no_ext}_full_text.txt")
    async with aiofiles.open(txt_file_path, 'w', encoding='utf-8') as f:
        await f.write(extracted_text)

    download_url = f"/api/download/{filename_no_ext}_full_text.txt"

    # Создаем file_metadata, если его нет
    file_metadata = {
        "file_size_formatted": f"{os.path.getsize(file_path) / 1024:.1f} КБ",
        "extension": os.path.splitext(file.filename)[1].lower(),
        "char_count": len(extracted_text),
        "word_count": len(extracted_text.split()),
        "download_url": download_url
    }

    new_document = Document(user_id=current_user.id,
                            file_path=file_path,
                            download_url=download_url)
    db.add(new_document)
    db.commit()

    logging.info("📥 Файл '%s' успешно загружен.", file.filename)
    return {
        "message": "Файл успешно загружен.",
        "file_path": file_path,
        "download_url": download_url,
        "file_metadata": file_metadata
    }


@router.get("/api/download/{filename}")
async def download_file(filename: str, request: Request):
    """
    Позволяет скачать файл с распознанным текстом.
    Не требует авторизации, доступ по прямой ссылке.
    """
    # Проверяем в нескольких директориях
    possible_paths = [
        os.path.join(UPLOAD_FOLDER, filename),
        os.path.join("output_documents", filename),
        os.path.join(os.getcwd(), UPLOAD_FOLDER, filename),
        os.path.join(os.getcwd(), "output_documents", filename)
    ]

    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break

    if not file_path:
        logging.error(f"❌ Файл не найден: {filename} (проверены пути: {possible_paths})")
        raise HTTPException(status_code=404, detail=f"Файл не найден: {filename}")

    logging.info(f"📤 Отправка файла '{filename}' на скачивание из {file_path}")
    
    # Убеждаемся, что файл будет скачан с расширением .txt
    download_filename = filename
    if not download_filename.lower().endswith('.txt'):
        download_filename = os.path.splitext(filename)[0] + '.txt'

    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type="text/plain"
    )


@router.post("/api/download_recognized_text")
async def create_and_return_file(
        file_content: str,
        file_name: str = "recognized_text.txt") -> FileResponse:
    """
    Создает текстовый файл с переданным содержимым и возвращает его для скачивания.
    Сохраняет оригинальное имя файла, только расширение меняет на .txt
    """
    try:
        # Обрабатываем имя файла, сохраняя исходное название
        filename_base, file_ext = os.path.splitext(file_name)

        # Гарантируем расширение .txt для файла с текстом
        if not file_ext or file_ext.lower() != '.txt':
            download_filename = f"{filename_base}.txt"
        else:
            download_filename = file_name

        # Избегаем пробелов в имени файла
        download_filename = download_filename.replace(" ", "_")

        # Путь к файлу временного хранения (с добавлением временной метки для уникальности)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        internal_filename = f"{timestamp}_{download_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, internal_filename)

        # Добавляем имя файла в логи для отладки
        logging.info(f"📄 Внутреннее имя файла: {internal_filename}")
        logging.info(f"📄 Имя файла для пользователя: {download_filename}")

        # Декодируем содержимое файла, если оно закодировано
        try:
            decoded_content = file_content
            # Проверяем, не закодирован ли текст в URL encoding
            if isinstance(file_content, str) and '%' in file_content[:100]:
                from urllib.parse import unquote
                decoded_content = unquote(file_content)

            # Сохраняем текст в файл
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(decoded_content)
        except Exception as encoding_error:
            logging.error(
                f"❌ Ошибка при декодировании или записи текста: {str(encoding_error)}"
            )
            # Сохраняем текст как есть, если возникла ошибка декодирования
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(file_content)

        logging.info(f"📄 Создан файл для скачивания: {file_path}")

        # Возвращаем файл для скачивания с явным указанием имени для пользователя
        return FileResponse(
            path=file_path,
            filename=download_filename,  # Используем оригинальное имя без временной метки
            media_type="text/plain"
        )
    except Exception as e:
        logging.error(f"❌ Ошибка при создании файла для скачивания: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Ошибка при создании файла: {str(e)}")


async def download_recognized_text(
    request: Request,
    file_content: str = Form(None),
    file_name: str = Form("recognized_text.txt"),
    current_user: User = Depends(get_current_user)):
    """
    Создает текстовый файл с распознанным текстом и возвращает его для скачивания
    Требует аутентификацию пользователя
    """
    # Проверка аутентификации
    if not current_user:
        logging.warning(
            f"⚠️ Попытка скачивания файла без авторизации: {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    if file_content:
        # Гарантируем, что файл сохраняется с расширением .txt
        filename_base, _ = os.path.splitext(file_name)
        txt_file_name = f"{filename_base}.txt"
        return await create_and_return_file(file_content, txt_file_name)
    else:
        raise HTTPException(status_code=400,
                            detail="Отсутствует содержимое файла")


# ===================== Подключение роутера =====================

app.include_router(router)