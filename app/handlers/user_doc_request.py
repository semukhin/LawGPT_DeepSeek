import os
import subprocess
import logging
import time
import re
import asyncio
import json
import aiofiles
import mimetypes
import tempfile
import shutil
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Any, Union

# Библиотеки для работы с документами
import docx
import pandas as pd
from docx.shared import Pt

# FastAPI компоненты
from fastapi import UploadFile, HTTPException, status

# Импорт сервиса Gemini для распознавания документов
try:
    from app.services.gemini_service import gemini_service
    logging.info("✅ Сервис Gemini успешно импортирован.")
except ImportError:
    logging.error("❌ Не удалось импортировать gemini_service. OCR может не работать.")
    gemini_service = None
except Exception as e:
    logging.error(f"❌ Ошибка при импорте gemini_service: {e}")
    gemini_service = None

# Импорт PyMuPDF (fitz) с обработкой исключений
try:
    import fitz
    logging.info("✅ PyMuPDF (fitz) успешно импортирован.")
except ImportError:
    logging.warning("⚠️ PyMuPDF (fitz) не найден. Обработка PDF будет ограничена.")
    fitz = None
except Exception as e:
    logging.error(f"❌ Ошибка при импорте PyMuPDF (fitz): {e}")
    fitz = None

# Импорт transliterate с подробным логированием
try:
    from transliterate import translit, get_available_language_codes
    logging.info("✅ Библиотека 'transliterate' успешно импортирована.")
    logging.info(f"📚 Доступные языки для транслитерации: {get_available_language_codes()}")
except ImportError as e:
    translit = None
    logging.warning(f"⚠️ Библиотека 'transliterate' не найдена: {str(e)}. Проверьте установку пакета.")
    logging.warning("⚠️ Имена файлов с кириллицей будут транслитерироваться вручную.")
except Exception as e:
    translit = None
    logging.error(f"❌ Ошибка при импорте 'transliterate': {e}. Будет использована ручная транслитерация.")

# Определение директорий для загрузки, временных файлов и обработанных результатов
UPLOAD_FOLDER = "uploads"
TEMP_FOLDER = "temp_processing"  # Используется для временных файлов
OUTPUT_FOLDER = "output_documents"  # Папка для сохранения распознанных файлов

# Создаем необходимые директории при импорте модуля
for folder in [UPLOAD_FOLDER, TEMP_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        try:
            os.makedirs(folder, exist_ok=True)
            logging.info(f"✅ Директория создана: {folder}")
        except Exception as e:
            logging.error(f"❌ Не удалось создать директорию {folder}: {str(e)}")

# Константы
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ максимальный размер файла
SUPPORTED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xlsx', '.jpeg', '.jpg', '.tiff', '.tif']

# Словарь для ручной транслитерации
MANUAL_TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'YO',
    'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'H', 'Ц': 'TS', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SCH', 'Ъ': '',
    'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'YU', 'Я': 'YA',
    ' ': '_', '-': '-', '.': '.'  # Добавляем разрешенные символы и замену пробелов
}

def safe_filename(filename: str) -> str:
    """
    Создает безопасное для файловой системы имя из строки, транслитерируя
    кириллицу и заменяя недопустимые символы.
    """
    filename_no_ext, file_extension = os.path.splitext(filename)
    
    # Гарантируем, что расширение будет .txt для файлов с распознанным текстом
    if not file_extension:
        file_extension = ".txt"
    
    # Принудительно преобразуем в .txt, если это файл с распознанным текстом
    if "_recognized" in filename_no_ext or "распознанный" in filename_no_ext.lower():
        file_extension = ".txt"

    if translit:
        try:
            transliterated_name = translit(filename_no_ext, 'ru', reversed=True)
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при транслитерации имени '{filename_no_ext}' с помощью библиотеки: {e}. Используем ручную транслитерацию.")
            transliterated_name = ''.join(MANUAL_TRANSLIT_MAP.get(c, c) for c in filename_no_ext)
    else:
        # Логируем процесс ручной транслитерации для сложных имен
        logging.info(f"🔤 Выполняем ручную транслитерацию для '{filename_no_ext}'")
        transliterated_name = ''.join(MANUAL_TRANSLIT_MAP.get(c, c) for c in filename_no_ext)
        logging.info(f"🔤 Результат транслитерации: '{transliterated_name}'")

    # Очистка от всех символов, кроме букв, цифр, _, - и .
    safe_name = ''.join(c if c.isalnum() or c in '_-.' else '_' for c in transliterated_name)

    # Убедимся, что не начинается или заканчивается на _ или . (кроме расширения)
    safe_name = re.sub(r'^[_.]+', '', safe_name)
    safe_name = re.sub(r'[_.]+$', '', safe_name)

    # Замена множественных подчеркиваний одним
    safe_name = re.sub(r'_{2,}', '_', safe_name)

    # Удаляем временные метки из имени файла для удобства пользователя
    safe_name = re.sub(r'^\d{8}_\d{6}_', '', safe_name)

    if not safe_name:  # Если после очистки имя стало пустым
        safe_name = "document"
    
    # Гарантируем, что имя файла будет уникальным
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = safe_name + file_extension.lower()
    
    logging.info(f"📄 Сформировано безопасное имя файла: {final_name}")
    return final_name


def is_valid_docx_sync(file_path):
    """
    Проверяет, является ли файл корректным DOCX (ZIP-архивом). Синхронная функция.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == b'PK\x03\x04'  # DOCX - это zip-архив
    except Exception:
        return False


async def convert_doc_to_docx_async(doc_file_path: str) -> str:
    """
    Конвертирует .doc в .docx с помощью LibreOffice в отдельном потоке.
    Сохраняет результат во временную папку.
    Возвращает путь к временному .docx файлу.
    """
    # Генерируем имя для временного docx файла во временной папке
    temp_docx_filename = f"{os.path.basename(doc_file_path)}_{int(time.time())}.docx"
    temp_docx_file_path = os.path.join(TEMP_FOLDER, temp_docx_filename)

    try:
        logging.info(f"🛠️ Конвертация .doc в .docx: {doc_file_path} -> {temp_docx_file_path}")

        # Выполняем LibreOffice в отдельном потоке, чтобы не блокировать event loop
        await asyncio.to_thread(
            subprocess.run,
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "docx",
                doc_file_path,
                "--outdir",
                TEMP_FOLDER,  # Указываем временную папку для вывода
            ],
            check=True,  # Вызовет CalledProcessError при неудаче
            capture_output=True,  # Захватываем stdout/stderr для логов
            text=True  # Декодировать вывод как текст
        )

        # LibreOffice создает файл с тем же именем, но с расширением .docx, в outdir
        expected_output_path = os.path.join(TEMP_FOLDER, os.path.splitext(os.path.basename(doc_file_path))[0] + '.docx')

        # Переименовываем файл в наше сгенерированное имя для уникальности
        if os.path.exists(expected_output_path):
            os.rename(expected_output_path, temp_docx_file_path)
            logging.info(f"✅ .doc успешно конвертирован в .docx: {temp_docx_file_path}")
            # Проверка на пустой файл после конвертации
            if os.path.getsize(temp_docx_file_path) == 0:
                raise ValueError(f"Конвертированный файл {temp_docx_file_path} пуст.")
            return temp_docx_file_path
        else:
            raise FileNotFoundError(f"LibreOffice не создал ожидаемый выходной файл: {expected_output_path}")

    except FileNotFoundError:
        # Это исключение subprocess.run, если libreoffice не найден
        raise RuntimeError("Ошибка конвертации: Убедитесь, что LibreOffice установлен и доступен в PATH.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Ошибка subprocess при конвертации .doc: {e.stdout} {e.stderr}")
        raise ValueError(f"Ошибка конвертации .doc в .docx. Подробности в логах.")
    except Exception as e:
        logging.error(f"❌ Непредвиденная ошибка при конвертации .doc: {str(e)}")
        raise ValueError(f"Непредвиденная ошибка при конвертации .doc в .docx: {str(e)}")


async def extract_text_from_docx_async(file_path: str) -> str:
    """
    Извлекает текст из .docx (или конвертированного .doc) в отдельном потоке.
    Использует python-docx, с fallback на mammoth.
    """
    temp_file_to_cleanup = None  # Переменная для хранения пути к временному файлу, если он создается (из .doc)

    try:
        # 1. Если это .doc, сначала конвертируем его асинхронно во временный .docx
        if file_path.lower().endswith(".doc"):
            temp_file_to_cleanup = await convert_doc_to_docx_async(file_path)
            docx_file_path_to_read = temp_file_to_cleanup
        else:
            docx_file_path_to_read = file_path  # Работаем напрямую с исходным .docx

        if not os.path.exists(docx_file_path_to_read):
            raise FileNotFoundError(f"Файл не найден для извлечения текста: {docx_file_path_to_read}")

        # 2. Проверяем, является ли файл корректным ZIP-архивом (DOCX)
        # Эта проверка быстрая, можно оставить синхронной или обернуть в to_thread для единообразия
        if not await asyncio.to_thread(is_valid_docx_sync, docx_file_path_to_read):
            raise ValueError(f"Файл {os.path.basename(file_path)} не является корректным DOCX или повреждён!")

        # 3. Опциональная MIME-проверка (в отдельном потоке, если magic установлен)
        try:
            import magic
            # Инициализация magic может быть медленной, но from_file быстрая
            mime = magic.Magic(mime=True)
            file_type = await asyncio.to_thread(mime.from_file, docx_file_path_to_read)

            # Проверяем MIME, но не делаем критическую ошибку, если ZIP-заголовок OK
            valid_mimes_pattern = r"application/vnd\.openxmlformats-officedocument\.wordprocessingml\.document|application/msword|application/octet-stream"
            if not re.match(valid_mimes_pattern, file_type):
                logging.warning(f"⚠️ MIME-тип файла {os.path.basename(file_path)} ({file_type}) не соответствует ожидаемым для DOCX/DOC, но ZIP-заголовок корректен. Попробуем извлечь текст.")

        except ImportError:
            logging.warning("⚠️ Библиотека 'python-magic' или libmagic не найдена. MIME-проверка пропущена.")
        except Exception as e:
            logging.warning(f"⚠️ Ошибка при MIME-проверке файла {os.path.basename(file_path)}: {str(e)}. Проверка пропущена.")

        # 4. Теперь читаем файл как DOCX в отдельном потоке
        try:
            # python-docx может быть блокирующим при чтении больших файлов
            document = await asyncio.to_thread(docx.Document, docx_file_path_to_read)
            full_text = "\n".join(
                [p.text.strip() for p in document.paragraphs if p.text.strip()])
            if full_text.strip():
                logging.info(f"✅ Текст успешно извлечен из DOCX с помощью python-docx.")
                return full_text
            logging.warning(f"⚠️ python-docx извлек пустой текст из {os.path.basename(file_path)}. Попробуем Mammoth.")
        except Exception as e:
            logging.error(f"❌ Ошибка при обработке python-docx: {e}. Попробуем Mammoth.", exc_info=True)

        # 5. Если python-docx не смог извлечь, пробуем Mammoth в отдельном потоке
        try:
            with open(docx_file_path_to_read, "rb") as docx_file:
                import mammoth
                # mammoth.extract_raw_text может быть блокирующим
                result = await asyncio.to_thread(mammoth.extract_raw_text, docx_file)
                if result.value.strip():
                    logging.info(f"✅ Текст успешно извлечен из DOCX с помощью Mammoth.")
                    return result.value.strip()
                else:
                    logging.warning(f"⚠️ Mammoth извлек пустой текст из {os.path.basename(file_path)}.")
                    return ""  # Вернуть пустую строку, если текст не извлечен
        except ImportError:
            logging.warning("⚠️ Библиотека 'mammoth' не найдена. Не удалось использовать как запасной вариант.")
            raise ValueError(f"Не удалось извлечь текст из DOCX/DOC файла {os.path.basename(file_path)}. Не найден Mammoth.")
        except Exception as e:
            logging.error(f"❌ Ошибка при обработке Mammoth: {e}", exc_info=True)
            raise ValueError(f"Ошибка при извлечении текста из DOCX/DOC файла {os.path.basename(file_path)} с помощью Mammoth: {e}")

    finally:
        # Очистка временного файла, если он был создан
        if temp_file_to_cleanup and os.path.exists(temp_file_to_cleanup):
            try:
                await cleanup_file(temp_file_to_cleanup)
            except Exception as e:
                logging.error(f"❌ Ошибка при удалении временного файла {temp_file_to_cleanup}: {e}")


async def extract_text_from_xlsx_async(file_path):
    """
    Извлекает текст из Excel файла (.xlsx) в отдельном потоке.
    Ограничивает количество строк для извлечения.
    """
    try:
        logging.info(f"📊 Начинаем обработку Excel файла: {file_path}")
        start_time = time.time()

        # pandas.read_excel может быть блокирующим
        excel_data = await asyncio.to_thread(pd.ExcelFile, file_path)
        sheets = await asyncio.to_thread(lambda x: x.sheet_names, excel_data)  # Вызов свойства в потоке

        extracted_text = f"Excel-документ содержит {len(sheets)} листов:\n\n"

        for sheet_name in sheets:
            try:
                # pandas.read_excel может быть блокирующим
                df = await asyncio.to_thread(pd.read_excel, excel_data, sheet_name)
                sheet_text = f"== Лист: {sheet_name} ==\n"

                # Получаем размер таблицы
                rows, cols = df.shape
                sheet_text += f"Размер таблицы: {rows} строк x {cols} столбцов\n\n"

                # Добавляем заголовки столбцов
                headers = df.columns.tolist()
                sheet_text += "ЗАГОЛОВКИ: " + " | ".join(str(h)
                                                        for h in headers) + "\n\n"

                # Добавляем данные (ограничиваем количество строк)
                max_rows = min(50, rows)  # Ограничиваем до 50 строк
                for i in range(max_rows):
                    row_data = df.iloc[i].tolist()
                    sheet_text += "СТРОКА " + str(i + 1) + ": " + " | ".join(
                        str(cell) if pd.notna(cell) else "" for cell in row_data) + "\n"  # Обработка NaN/None

                if rows > max_rows:
                    sheet_text += f"\n... [и ещё {rows - max_rows} строк не показаны]\n"

                extracted_text += sheet_text + "\n\n"
            except pd.errors.EmptyDataError:
                sheet_text = f"== Лист: {sheet_name} ==\nЛист пуст.\n\n"
                extracted_text += sheet_text
                logging.warning(f"⚠️ Лист '{sheet_name}' в Excel файле пуст.")
            except Exception as sheet_e:
                logging.error(f"❌ Ошибка при обработке листа '{sheet_name}': {sheet_e}")
                extracted_text += f"== Лист: {sheet_name} ==\nОшибка при обработке листа: {sheet_e}\n\n"

        elapsed_time = time.time() - start_time
        logging.info(f"✅ Excel обработан за {elapsed_time:.2f} секунд")

        return extracted_text

    except FileNotFoundError:
        logging.error(f"❌ Файл Excel не найден: {file_path}")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"❌ Ошибка парсинга Excel файла: {str(e)}")
        raise ValueError(f"Ошибка при чтении Excel файла. Возможно, формат некорректен.") from e
    except Exception as e:
        logging.error(f"❌ Непредвиденная ошибка при обработке Excel файла: {str(e)}")
        raise ValueError(f"Непредвиденная ошибка при обработке Excel файла: {str(e)}")


async def extract_text_from_pdf_async(file_path: str) -> str:
    """
    Извлекает текст из PDF. Использует Gemini для OCR (сканы) и PyMuPDF
    для текстового слоя как запасной вариант (в отдельном потоке).
    """
    try:
        logging.info(f"📄 Начинаем обработку PDF файла: {file_path}")

        # Читаем PDF файл в байты асинхронно
        async with aiofiles.open(file_path, mode="rb") as pdf_file:
            pdf_bytes = await pdf_file.read()

        # Проверяем доступность Gemini сервиса
        if gemini_service and hasattr(gemini_service, "extract_text_from_pdf"):
            # Используем сервис Gemini для извлечения текста
            logging.info("🌐 Отправляем PDF в Gemini Service для OCR/извлечения текста...")
            try:
                gemini_result = await gemini_service.extract_text_from_pdf(pdf_bytes)

                if gemini_result.get("success"):
                    logging.info(f"✅ Текст успешно извлечен из PDF с помощью Gemini API. Символов: {len(gemini_result.get('text', ''))}")
                    return gemini_result.get("text", "")
                else:
                    error_message = gemini_result.get("error", "Неизвестная ошибка Gemini Service")
                    logging.warning(f"⚠️ Gemini Service не смог извлечь текст из PDF: {error_message}. Пробуем PyMuPDF...")
            except Exception as e:
                logging.error(f"❌ Ошибка при вызове Gemini API для PDF: {str(e)}")
                logging.warning("⚠️ Пробуем извлечь текст через PyMuPDF...")
        else:
            logging.warning("⚠️ Gemini сервис недоступен. Используем PyMuPDF для извлечения текста.")

        # Извлекаем текст напрямую через PyMuPDF (в отдельном потоке)
        if fitz:
            try:
                def get_text_sync(pdf_path):
                    doc = fitz.open(pdf_path)
                    text = ""
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        text += page.get_text()
                    doc.close()
                    return text

                text = await asyncio.to_thread(get_text_sync, file_path)

                if text.strip():
                    logging.info(f"✅ Текст успешно извлечен из PDF с помощью PyMuPDF. Символов: {len(text)}")
                    return text
                else:
                    logging.warning("⚠️ PyMuPDF не смог извлечь текст из PDF (возможно, сканированный документ).")
                    return "Не удалось извлечь текст из PDF. Возможно, это сканированный документ без текстового слоя."
            except Exception as mupdf_error:
                logging.error(f"❌ Ошибка при использовании PyMuPDF: {str(mupdf_error)}", exc_info=True)
                return f"Не удалось извлечь текст из PDF с помощью PyMuPDF: {str(mupdf_error)}"
        else:
            logging.error("❌ Ни Gemini, ни PyMuPDF не доступны для извлечения текста из PDF.")
            return "Не удалось извлечь текст из PDF: библиотека PyMuPDF не найдена, а Gemini сервис недоступен."

    except FileNotFoundError:
        logging.error(f"❌ PDF файл не найден: {file_path}")
        raise
    except Exception as e:
        logging.error(f"❌ Непредвиденная ошибка при обработке PDF: {str(e)}", exc_info=True)
        raise ValueError(f"Непредвиденная ошибка при обработке PDF: {str(e)}")


async def extract_text_from_image_async(file_path: str) -> str:
    """
    Извлекает текст из изображений (JPEG, TIFF) с помощью Gemini OCR.
    """
    try:
        logging.info(f"🖼️ Начинаем обработку изображения: {file_path}")

        # Определяем MIME тип файла
        mime_type, _ = mimetypes.guess_type(file_path)

        if not mime_type:
            # Если не удалось определить MIME тип, пробуем по расширению
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext in ['.tif', '.tiff']:
                mime_type = 'image/tiff'
            else:
                # Если даже по расширению не ясно, используем общий тип изображения
                mime_type = 'image/jpeg'  # Предполагаем jpeg как наиболее распространенный
            logging.warning(f"⚠️ Не удалось определить MIME тип изображения {os.path.basename(file_path)}. Используем: {mime_type}")

        # Читаем файл изображения в байты асинхронно
        async with aiofiles.open(file_path, mode="rb") as img_file:
            img_bytes = await img_file.read()

        # Проверяем размер изображения
        file_size_mb = len(img_bytes) / (1024 * 1024)
        logging.info(f"📏 Размер файла изображения: {file_size_mb:.2f} МБ")

        # Если размер изображения больше 4 МБ, уменьшаем его для ускорения обработки
        if file_size_mb > 4.0:
            try:
                from PIL import Image
                import io

                logging.info(f"🔄 Изображение слишком большое, уменьшаем для ускорения обработки...")
                img = Image.open(io.BytesIO(img_bytes))

                # Определяем новый размер, сохраняя пропорции
                width, height = img.size
                max_dimension = 2000  # Максимальный размер любой стороны

                if width > max_dimension or height > max_dimension:
                    if width > height:
                        new_width = max_dimension
                        new_height = int(height * (max_dimension / width))
                    else:
                        new_height = max_dimension
                        new_width = int(width * (max_dimension / height))

                    # Изменяем размер
                    img = img.resize((new_width, new_height), Image.LANCZOS)

                    # Сохраняем в памяти
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=85)
                    img_bytes = buffer.getvalue()

                    # Обновляем MIME-тип
                    mime_type = "image/jpeg"

                    logging.info(f"✅ Изображение успешно уменьшено до {new_width}x{new_height}, новый размер: {len(img_bytes) / (1024 * 1024):.2f} МБ")
            except Exception as e:
                logging.warning(f"⚠️ Не удалось уменьшить размер изображения: {str(e)}")

        # Проверяем доступность Gemini сервиса
        if gemini_service and hasattr(gemini_service, "extract_text_from_image"):
            # Используем Gemini API для OCR с повторными попытками
            logging.info(f"🌐 Отправляем изображение ({mime_type}) в Gemini Service для OCR...")
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    timeout = 60.0 + (retry_count * 30.0)  # Увеличиваем таймаут с каждой попыткой
                    logging.info(f"🔄 Попытка OCR {retry_count + 1} из {max_retries} с таймаутом {timeout} сек...")

                    gemini_result = await gemini_service.extract_text_from_image(img_bytes, mime_type, custom_timeout=timeout)

                    if gemini_result.get("success"):
                        logging.info(f"✅ Текст успешно извлечен из изображения с помощью Gemini API. Символов: {len(gemini_result.get('text', ''))}")
                        return gemini_result.get("text", "")

                    # Проверяем, является ли ошибка таймаутом
                    error_message = gemini_result.get("error", "")
                    if "таймаут" in error_message.lower() or "timeout" in error_message.lower():
                        logging.warning(f"⏱️ Таймаут при попытке {retry_count + 1}: {error_message}")
                        retry_count += 1
                        # Небольшая пауза между попытками
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Если это не таймаут, а другая ошибка, прекращаем попытки
                        logging.error(f"❌ Ошибка при извлечении текста из изображения: {error_message}")
                        return f"Не удалось извлечь текст из изображения: {error_message}"

                except Exception as e:
                    logging.error(f"❌ Ошибка при вызове Gemini API для OCR: {str(e)}")
                    retry_count += 1
                    await asyncio.sleep(1)  # Пауза перед следующей попыткой

            # Если все попытки исчерпаны
            error_message = gemini_result.get("error", "Превышено количество попыток")
            logging.error(f"❌ Не удалось выполнить OCR после {max_retries} попыток: {error_message}")
            return f"Не удалось извлечь текст из изображения после {max_retries} попыток: {error_message}"
        else:
            logging.error("❌ Сервис Gemini недоступен для OCR изображений.")
            return "Не удалось извлечь текст из изображения: сервис Gemini недоступен."

    except Exception as e:
        logging.error(f"❌ Ошибка при вызове Gemini API для изображения: {str(e)}")
        return f"Ошибка OCR с помощью Gemini: {str(e)}"
    except FileNotFoundError:
        logging.error(f"❌ Файл изображения не найден: {file_path}")
        return f"Файл изображения не найден: {file_path}"
    except Exception as e:
        logging.error(f"❌ Непредвиденная ошибка при обработке изображения: {str(e)}", exc_info=True)
        raise ValueError(f"Непредвиденная ошибка при обработке изображения: {str(e)}")


async def cleanup_file(file_path: str):
    """Асинхронно и безопасно удаляет файл."""
    if file_path and os.path.exists(file_path):
        try:
            # Удаление файла может быть блокирующей операцией на некоторых ОС или ФС
            await asyncio.to_thread(os.remove, file_path)
            logging.info(f"🗑️ Временный файл удален: {file_path}")
        except Exception as e:
            # Логируем ошибку, но не останавливаем выполнение
            logging.error(f"❌ Не удалось удалить файл {file_path}: {e}")


async def extract_text_from_any_document(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Универсальная функция извлечения текста из различных типов документов.
    Возвращает извлеченный текст и метаданные.
    Ошибки извлечения обрабатываются здесь и возвращаются как часть текста.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Словарь для хранения метаданных файла
    local_file_metadata = {
        "original_filename": os.path.basename(file_path),
        "file_size_bytes": 0,  # Будет заполнено в process_uploaded_file
        "file_size_formatted": "",  # Будет заполнено в process_uploaded_file
        "extension": ext,
        "processing_time_seconds": 0,
        "extraction_success": False,
        "char_count": 0,
        "word_count": 0,
        "page_count": 0,  # Может быть заполнено для PDF/DOCX если парсеры поддерживают
        "recognized_text_file_docx": None,  # Путь к сохраненному docx
        "recognized_text_file_txt": None,  # Путь к сохраненному txt
        "download_url_docx": None,
        "download_url_txt": None,
        "timestamp": datetime.now().isoformat()
    }

    extracted_text = ""
    extraction_successful = False
    error_message = ""
    start_time = time.time()

    try:
        if not os.path.exists(file_path):
            error_message = f"Ошибка: файл не найден по пути {file_path}"
            logging.error(f"❌ {error_message}")
            # Не бросаем исключение, возвращаем ошибку в тексте
            return error_message, local_file_metadata

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            error_message = f"Ошибка: загруженный файл пуст (0 байт): {file_path}"
            logging.error(f"❌ {error_message}")
            return error_message, local_file_metadata

        local_file_metadata["file_size_bytes"] = file_size
        # Форматированный размер файла
        if file_size < 1024:
            local_file_metadata["file_size_formatted"] = f"{file_size} байт"
        elif file_size < 1024 * 1024:
            local_file_metadata["file_size_formatted"] = f"{file_size/1024:.1f} КБ"
        else:
            local_file_metadata["file_size_formatted"] = f"{file_size/(1024*1024):.1f} МБ"

        logging.info(f"🔍 Начинаем извлечение текста из {ext} файла: {file_path}")

        # Выбираем подходящий асинхронный метод извлечения по расширению
        if ext == ".pdf":
            extracted_text = await extract_text_from_pdf_async(file_path)
        elif ext in [".doc", ".docx"]:
            # extract_text_from_docx_async управляет конвертацией и очисткой временного файла .doc -> .docx
            extracted_text = await extract_text_from_docx_async(file_path)
        elif ext == ".xlsx":
            extracted_text = await extract_text_from_xlsx_async(file_path)
        elif ext in [".jpg", ".jpeg", ".tif", ".tiff"]:
            extracted_text = await extract_text_from_image_async(file_path)
        else:
            error_message = (
                f"Неподдерживаемый тип файла: {ext}. "
                f"Поддерживаются: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
            logging.error(f"❌ {error_message}")
            # Возвращаем ошибку в тексте, не бросаем HTTPException здесь
            return error_message, local_file_metadata

        # Проверяем, является ли результат текстом ошибки от под-функций
        if extracted_text and extracted_text.startswith("Не удалось извлечь текст из"):
            error_message = extracted_text  # Сохраняем сообщение об ошибке
            extracted_text = ""  # Обнуляем текст, так как это ошибка
            extraction_successful = False
        elif extracted_text and extracted_text.strip():
            extraction_successful = True
            logging.info("✅ Извлечение текста успешно.")
        else:
            extraction_successful = False
            error_message = "Из документа не удалось извлечь текст."
            logging.warning(f"⚠️ Извлеченный текст пуст для файла: {file_path}")

    except FileNotFoundError as e:
        error_message = f"Ошибка: Файл не найден во время обработки - {e}"
        logging.error(f"❌ {error_message}", exc_info=True)
    except ValueError as e:  # Ошибки конвертации, парсинга, неподдерживаемого типа и т.д.
        error_message = f"Ошибка обработки документа: {e}"
        logging.error(f"❌ {error_message}", exc_info=True)
    except Exception as e:
        # Любая другая непредвиденная ошибка
        error_message = f"Непредвиденная ошибка при извлечении текста: {e}"
        logging.error(f"❌ {error_message}", exc_info=True)

    elapsed_time = time.time() - start_time
    logging.info(f"⏱️ Извлечение текста завершено за {elapsed_time:.2f} секунд")

    # Обновляем метаданные на основе результата извлечения
    local_file_metadata["processing_time_seconds"] = elapsed_time
    local_file_metadata["extraction_success"] = extraction_successful
    local_file_metadata["char_count"] = len(extracted_text) if extracted_text else 0
    local_file_metadata["word_count"] = len(extracted_text.split()) if extracted_text else 0

    # Всегда сохраняем извлеченный текст (если он есть) или сообщение об ошибке в файл
    content_to_save = extracted_text if extracted_text else error_message

    if content_to_save:
            logging.info(f"📄 Сохраняем результат ({len(content_to_save)} символов) в текстовый файл.")

            # Создаем безопасное имя файла на основе оригинального
            original_filename = os.path.basename(file_path)
            safe_base_name = safe_filename(original_filename)  # safe_filename уже добавляет расширение

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_base_filename = f"{timestamp}_{os.path.splitext(safe_base_name)[0]}"

            # Создаем более понятное имя файла на основе оригинального, без технических префиксов
            safe_original_name = os.path.splitext(safe_base_name)[0]
            # Удаляем временную метку из имени файла для удобства пользователя
            clean_filename = safe_original_name.replace(timestamp + "_", "")
            # Добавляем суффикс для обозначения распознанного текста и транслитерируем имя
            txt_filename = f"{clean_filename}_recognized.txt"
            
            # Убедимся, что директория OUTPUT_FOLDER существует
            if not os.path.exists(OUTPUT_FOLDER):
                try:
                    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                    logging.info(f"✅ Директория создана: {OUTPUT_FOLDER}")
                except Exception as e:
                    logging.error(f"❌ Не удалось создать директорию {OUTPUT_FOLDER}: {str(e)}")
            
            txt_file_path = os.path.join(OUTPUT_FOLDER, txt_filename)
            
            try:
                # Добавляем заголовок для улучшения читаемости
                header = f"Распознанный текст документа: {safe_original_name}\n"
                header += f"Дата обработки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                header += "=" * 50 + "\n\n"
                
                # Полное содержимое с заголовком
                full_content = header + content_to_save
                
                # Логируем информацию о сохраняемом тексте для отладки
                logging.info(f"Сохраняемый текст: Длина={len(content_to_save)} символов, Заголовок={len(header)} символов")
                logging.info(f"Общая длина текста для сохранения: {len(full_content)} символов")
                
                # Сначала записываем данные в бинарном режиме для гарантии сохранения всех данных
                try:
                    # Логируем информацию о тексте перед сохранением
                    logging.info(f"📊 Текст для сохранения: {len(full_content)} символов")
                    
                    # Используем прямую бинарную запись для максимальной надежности
                    content_bytes = full_content.encode('utf-8')
                    
                    # Всегда используем метод с временным файлом для надежности
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                        temp_path = temp_file.name
                        temp_file.write(content_bytes)
                        temp_file.flush()
                        os.fsync(temp_file.fileno())
                    
                    # Копируем временный файл на место целевого после успешной записи
                    shutil.copy2(temp_path, txt_file_path)
                    
                    # Проверка успешности записи
                    file_size = os.path.getsize(txt_file_path)
                    expected_size = len(content_bytes)
                    
                    if file_size == expected_size:
                        logging.info(f"✅ Полный текст успешно сохранен: {file_size}/{expected_size} байт")
                        
                        # Добавляем информацию о файле в метаданные
                        local_file_metadata["recognized_text_file_txt"] = txt_file_path
                        local_file_metadata["download_url"] = f"/api/download/{os.path.basename(txt_file_path)}"
                        logging.info(f"✅ Результат сохранен в TXT: {txt_file_path} (размер: {file_size} байт)")
                    else:
                        logging.error(f"❌ Неполная запись: ожидалось {expected_size} байт, записано {file_size} байт")
                        
                        # Еще одна попытка с прямой записью
                        with open(txt_file_path, "wb") as f:
                            f.write(content_bytes)
                            f.flush()
                            os.fsync(f.fileno())
                            
                        # Проверяем размер снова
                        new_size = os.path.getsize(txt_file_path)
                        if new_size == expected_size:
                            logging.info(f"✅ Успешно сохранен полный текст: {new_size}/{expected_size} байт")
                            
                            # Добавляем информацию о файле в метаданные
                            local_file_metadata["recognized_text_file_txt"] = txt_file_path
                            local_file_metadata["download_url"] = f"/api/download/{os.path.basename(txt_file_path)}"
                            logging.info(f"✅ Результат сохранен в TXT: {txt_file_path} (размер: {new_size} байт)")
                        else:
                            logging.error(f"❌ Не удалось сохранить полный текст: {new_size}/{expected_size} байт")
                    
                    # Удаляем временный файл
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logging.warning(f"⚠️ Не удалось удалить временный файл {temp_path}: {e}")
                
                except Exception as e:
                    logging.error(f"❌ Ошибка при сохранении текста в файл: {e}")
                    raise
                
            except Exception as e:
                logging.error(f"❌ Ошибка при сохранении результата: {e}")
                error_message = f"Не удалось сохранить результат: {str(e)}"
                return error_message, local_file_metadata

    # Если был текст ошибки, добавляем его к извлеченному тексту
    if error_message:
        if extracted_text:
            extracted_text = f"{error_message}\n\nЧастично извлеченный текст:\n{extracted_text}"
        else:
            extracted_text = error_message

    return extracted_text, local_file_metadata


async def process_uploaded_file(file: UploadFile) -> Tuple[str, str, Dict[str, Any]]:
    """
    Сохраняет загруженный файл, извлекает из него текст и возвращает результат
    для API ответа, включая метаданные.
    """
    start_time = time.time()
    original_file_path = None  # Путь к сохраненному оригинальному файлу

    # Словарь для хранения метаданных файла
    file_metadata = {
        "original_filename": file.filename if file and file.filename else "unknown",
        "file_size_bytes": 0,
        "file_size_formatted": "",
        "extension": os.path.splitext(file.filename)[1].lower() if file and file.filename else "unknown",
        "processing_time_seconds": 0,
        "extraction_success": False,
        "char_count": 0,
        "word_count": 0,
        "page_count": 0,
        "recognized_text_file_docx": None,
        "recognized_text_file_txt": None,
        "download_url_docx": None,
        "download_url_txt": None,
        "timestamp": datetime.now().isoformat()
    }

    extracted_text_for_response = ""  # Текст, который будет возвращен API
    response_message = ""  # Сообщение для пользователя в случае ошибки или успеха

    # Проверяем, что файл предоставлен
    if not file or not file.filename:
        error_msg = "Ошибка: Файл не предоставлен или имя файла пустое"
        logging.error(f"❌ {error_msg}")
        # Бросаем HTTPException, так как это ошибка запроса клиента
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logging.info(f"📄 Получен файл: {file.filename}")

    try:
        # Проверка типа файла до сохранения
        file_extension = os.path.splitext(file.filename)[1].lower()
        file_metadata["extension"] = file_extension

        if file_extension not in SUPPORTED_EXTENSIONS:
            error_msg = (
                f"Неподдерживаемый тип файла: {file_extension}. "
                f"Поддерживаются только: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
            logging.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=error_msg
            )

        # Генерируем безопасное имя для сохранения оригинального файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_original_filename = safe_filename(file.filename)
        saved_filename = f"{timestamp}_{safe_original_filename}"
        original_file_path = os.path.join(UPLOAD_FOLDER, saved_filename)

        # Сохраняем загруженный файл асинхронно и проверяем размер
        file_content = await file.read()  # Читаем все содержимое в память
        file_size = len(file_content)

        file_metadata["file_size_bytes"] = file_size
        # Форматированный размер файла
        if file_size < 1024:
            file_metadata["file_size_formatted"] = f"{file_size} байт"
        elif file_size < 1024 * 1024:
            file_metadata["file_size_formatted"] = f"{file_size/1024:.1f} КБ"
        else:
            file_metadata["file_size_formatted"] = f"{file_size/(1024*1024):.1f} МБ"

        logging.info(f"📏 Размер файла: {file_metadata['file_size_formatted']}")

        if file_size == 0:
            error_msg = "Ошибка: Загруженный файл пуст (0 байт)."
            logging.error(f"❌ {error_msg}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        if file_size > MAX_FILE_SIZE:
            error_msg = (
                f"Файл слишком большой: {file_metadata['file_size_formatted']}. "
                f"Максимальный размер: {MAX_FILE_SIZE/(1024*1024)} МБ"
            )
            logging.error(f"❌ {error_msg}")
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=error_msg)

        # Проверяем существование директории перед сохранением
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Сохраняем файл асинхронно
        async with aiofiles.open(original_file_path, "wb") as buffer:
            await buffer.write(file_content)

        logging.info(
            f"📂 Файл сохранён: {original_file_path} "
            f"(размер: {file_metadata['file_size_formatted']})"
        )

        # Извлекаем текст из файла, обработка ошибок происходит внутри этой функции
        extracted_text, extraction_metadata = await extract_text_from_any_document(original_file_path)

        # Обновляем метаданные из результатов извлечения
        file_metadata.update(extraction_metadata)

        # Текст для ответа API - либо извлеченный, либо сообщение об ошибке
        extracted_text_for_response = extracted_text

        if file_metadata["extraction_success"]:
            response_message = "Текст успешно извлечен."
            logging.info(f"✅ Успешное извлечение текста. Символов: {len(extracted_text_for_response)}")
        else:
            response_message = extracted_text  # Сообщение об ошибке уже содержится в extracted_text
            logging.warning(f"⚠️ Извлечение текста завершилось с ошибкой/пустым результатом: {response_message}")

        # Форматируем извлеченный текст для лучшего отображения в ответе (если он есть)
        if file_metadata["extraction_success"] and extracted_text_for_response:
            # Удаляем лишние пробелы и переносы строк (асинхронно)
            def format_text_sync(text):
                formatted = re.sub(r'\n{3,}', '\n\n', text)  # Сжимаем множественные переносы
                formatted = re.sub(r'[ \t]{2,}', ' ', formatted)  # Сжимаем множественные пробелы/табы
                # Удаляем пробелы в начале и конце строк
                formatted = '\n'.join([line.strip() for line in formatted.split('\n')])
                return formatted.strip()  # Удаляем пробелы в начале/конце всего текста

            formatted_text = await asyncio.to_thread(format_text_sync, extracted_text_for_response)
            extracted_text_for_response = formatted_text
            file_metadata["char_count"] = len(extracted_text_for_response)
            file_metadata["word_count"] = len(extracted_text_for_response.split())

    except HTTPException:
        # Если уже была брошена HTTPException (напр., unsupported type, too large)
        raise
    except Exception as e:
        # Ловим любые другие исключения, не пойманные ранее
        elapsed_time = time.time() - start_time
        file_metadata["processing_time_seconds"] = round(elapsed_time, 2)
        error_msg = f"Непредвиденная ошибка при обработке файла {file_metadata['original_filename']}: {e}"
        logging.error(f"❌ {error_msg}", exc_info=True)
        # Возвращаем стандартный ответ с ошибкой
        extracted_text_for_response = error_msg
        response_message = error_msg  # Сообщение для пользователя
        file_metadata["extraction_success"] = False  # Убедимся, что успех = False

    finally:
        # Всегда пытаемся удалить оригинальный загруженный файл после обработки
        if original_file_path:
            await cleanup_file(original_file_path)
        # Очистка временных файлов из TEMP_FOLDER должна происходить внутри функций извлечения (.doc)
        # или как общая задача по расписанию, если остаются "зависшие" файлы.

    # Вычисляем общее время обработки
    total_elapsed_time = time.time() - start_time
    file_metadata["processing_time_seconds"] = round(total_elapsed_time, 2)
    
    # Проверяем полноту и целостность текста перед возвратом
    if file_metadata["extraction_success"] and extracted_text_for_response:
        # Проверяем, если файл слишком большой, то ожидаем более длинный текст
        file_size_mb = file_metadata["file_size_bytes"] / (1024 * 1024)
        text_length = len(extracted_text_for_response)
        
        # Примерная эвристика: для PDF ~1000 символов на страницу, ~10 страниц на 1MB
        expected_min_length = file_size_mb * 10000
        
        if text_length < expected_min_length and file_size_mb > 0.5:
            logging.warning(f"⚠️ Извлеченный текст может быть неполным: {text_length} символов при размере файла {file_size_mb:.2f} MB")
            logging.warning(f"⚠️ Ожидалось примерно {int(expected_min_length)} символов")
            
            # Проверяем файл с распознанным текстом на диске
            if file_metadata["recognized_text_file_txt"]:
                txt_path = os.path.join(OUTPUT_FOLDER, file_metadata["recognized_text_file_txt"])
                if os.path.exists(txt_path):
                    try:
                        with open(txt_path, 'r', encoding='utf-8') as f:
                            file_text = f.read()
                        
                        file_text_length = len(file_text)
                        logging.info(f"📏 Длина текста в файле: {file_text_length} символов")
                        
                        # Если в файле больше текста, чем в извлеченном - используем текст из файла
                        if file_text_length > text_length * 1.1:  # Если больше на 10%
                            logging.info(f"✅ Используем более полный текст из файла: +{file_text_length - text_length} символов")
                            extracted_text_for_response = file_text
                            file_metadata["char_count"] = file_text_length
                            file_metadata["word_count"] = len(file_text.split())
                    except Exception as e:
                        logging.error(f"❌ Ошибка при чтении файла с распознанным текстом: {e}")
        else:
            logging.info(f"✅ Длина текста соответствует ожидаемой: {text_length} символов")

    # Возвращаем путь к оригинальному файлу (может быть None, если ошибка до сохранения),
    # текст для ответа и метаданные
    return original_file_path, extracted_text_for_response, file_metadata