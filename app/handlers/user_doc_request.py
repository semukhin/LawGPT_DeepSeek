import os
import subprocess
from docx import Document
import logging
import fitz 
import pytesseract
from pdf2image import convert_from_path
import time
from fastapi import UploadFile
import aiofiles
from transliterate import translit
from datetime import datetime

# Определение директории для загрузки файлов
UPLOAD_FOLDER = "uploads"  # Убедитесь, что эта директория существует

# Настройка Tesseract
pytesseract.pytesseract.tesseract_cmd = "/bin/tesseract"

MAX_EXTRACTED_TEXT_SIZE = 30000  # Максимальный размер текста, извлекаемого из файла



def is_valid_docx(file_path):
    """
    Проверяет, является ли файл корректным DOCX (ZIP-архивом).
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == b'PK\x03\x04'  # DOCX - это zip-архив, который начинается с PK (ZIP signature)
    except Exception:
        return False

def convert_doc_to_docx(doc_file_path):
    """
    Конвертирует .doc в .docx с помощью LibreOffice.
    """
    docx_file_path = doc_file_path.replace(".doc", ".docx")
    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "docx",
                doc_file_path,
                "--outdir",
                os.path.dirname(doc_file_path),
            ],
            check=True
        )
        if os.path.exists(docx_file_path):
            return docx_file_path
    except Exception as e:
        raise ValueError(f"Ошибка при конвертации .doc в .docx: {e}")

    raise ValueError("Не удалось конвертировать .doc в .docx.")


def extract_text_from_docx(docx_file_path):
    """
    Извлекает текст из .docx (или конвертированного .doc) и удаляет пустые строки.
    """
    if not os.path.exists(docx_file_path):
        raise ValueError(f"Файл не найден: {docx_file_path}")

    # 1. Проверяем, является ли файл ZIP-архивом (DOCX)
    if not is_valid_docx(docx_file_path):
        # Если не ZIP, может быть .doc (binary), тогда пробуем конвертировать:
        if docx_file_path.lower().endswith(".doc"):
            docx_file_path = convert_doc_to_docx(docx_file_path)
            if not is_valid_docx(docx_file_path):
                raise ValueError(f"Ошибка: файл {docx_file_path} не является корректным DOCX/DOC!")
        else:
            raise ValueError(f"Ошибка: файл {docx_file_path} не является DOCX/DOC или повреждён!")

    # 2. MIME-проверка (но теперь она необязательная)
    #    Можно вынести в try/except, чтобы не ломаться, если MIME = octet-stream
    try:
        import magic
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(docx_file_path)

        # Если MIME — "application/octet-stream", но файл ZIP → принимаем
        # Если MIME — "application/vnd.openxmlformats-officedocument.wordprocessingml.document" → тоже ок
        # Если MIME — "application/msword" → тоже ок
        # Иначе → warning
        valid_mimes = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/octet-stream"
        }
        if file_type not in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/octet-stream"
        ]:
            raise ValueError(f"Ошибка: файл {docx_file_path} не является DOCX/DOC. Определён как {file_type}")

    except Exception as e:
        logging.warning(f"⚠️ Ошибка при определении MIME: {str(e)}")

    # 3. Теперь читаем файл как DOCX
    try:
        document = Document(docx_file_path)
        full_text = "\n".join([p.text.strip() for p in document.paragraphs if p.text.strip()])
        if full_text.strip():
            return full_text
    except Exception as e:
        logging.error(f"Ошибка при обработке python-docx: {e}")

    # 4. Если python-docx не смог извлечь, пробуем Mammoth
    try:
        with open(docx_file_path, "rb") as docx_file:
            import mammoth
            result = mammoth.extract_raw_text(docx_file)
            return result.value.strip()
    except Exception as e:
        raise ValueError(f"Ошибка при обработке Mammoth: {e}")



def extract_text_from_scanned_pdf(file_path):
    """
    OCR для PDF, которые не содержат текстового слоя (сканы).
    """
    text = ""
    try:
        images = convert_from_path(file_path)
        for image in images:
            text += pytesseract.image_to_string(image, lang="rus")
    except Exception as e:
        logging.error(f"Ошибка OCR для PDF: {e}")
    return text

def extract_text_from_pdf(file_path):
    """
    Извлекает текст из PDF. Если текст отсутствует (скан), пробуем OCR.
    """
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text("text")
    except Exception as e:
        logging.error(f"Ошибка извлечения текста из PDF: {e}")

    if not text.strip():  # Если PDF пустой, пробуем OCR
        logging.info("📄 PDF без текста, пробуем OCR...")
        text = extract_text_from_scanned_pdf(file_path)

    return text

def extract_text_from_any_document(file_path: str) -> str:
    """
    Универсальная функция: если PDF → PDF-логика,
    если DOC/DOCX → docx-логика,
    иначе → ошибка.
    
    Ограничивает размер извлекаемого текста для предотвращения
    переполнения промта.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        start_time = time.time()
        
        # Выбираем подходящий метод извлечения
        if ext in [".pdf"]:
            extracted_text = extract_text_from_pdf(file_path)
        elif ext in [".doc", ".docx"]:
            extracted_text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Неподдерживаемый тип файла: {ext}")
        
        elapsed_time = time.time() - start_time
        logging.info(f"⏱️ Время извлечения текста: {elapsed_time:.2f} секунд")
        
        # Ограничиваем размер извлекаемого текста
        if extracted_text and len(extracted_text) > MAX_EXTRACTED_TEXT_SIZE:
            logging.info(f"📄 Текст документа слишком длинный ({len(extracted_text)} символов). Обрезаем до {MAX_EXTRACTED_TEXT_SIZE} символов.")
            
            # Поиск подходящей точки для обрезки (конец предложения)
            cutoff_point = MAX_EXTRACTED_TEXT_SIZE
            
            # Ищем конец предложения ближе к концу допустимого размера
            for i in range(MAX_EXTRACTED_TEXT_SIZE - 1, MAX_EXTRACTED_TEXT_SIZE - 200, -1):
                if i < len(extracted_text) and extracted_text[i] in ['.', '!', '?', '\n']:
                    cutoff_point = i + 1
                    break
            
            truncated_text = extracted_text[:cutoff_point] + f"\n\n... [текст документа обрезан, показано {cutoff_point} из {len(extracted_text)} символов]"
            logging.info(f"📄 Текст документа обрезан. Итоговый размер: {len(truncated_text)} символов")
            return truncated_text
        
        return extracted_text or "Не удалось извлечь текст из документа."
    
    except Exception as e:
        logging.error(f"❌ Ошибка при извлечении текста из документа: {str(e)}")
        return f"Ошибка при обработке документа: {str(e)}"


# Оптимизация функции обработки файла в процессе загрузки
async def process_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Сохраняет загруженный файл и извлекает из него текст.
    Обрабатывает возможные ошибки и оптимизирует извлечение текста.
    
    Args:
        file: Загруженный файл от пользователя
        
    Returns:
        tuple[str, str]: Кортеж из (путь_к_файлу, извлеченный_текст)
    """
    start_time = time.time()
    
    # Проверка типа файла
    file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if file_extension not in ['.pdf', '.doc', '.docx']:
        raise ValueError(f"Неподдерживаемый тип файла: {file_extension}. Поддерживаются только .pdf, .doc, .docx")
    
    # Оптимизированное сохранение файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_filename = file.filename.replace(" ", "_")
    filename_no_ext, file_extension = os.path.splitext(original_filename)
    
    # Транслитерация имени файла
    try:
        transliterated_filename = translit(filename_no_ext, 'ru', reversed=True)
    except Exception as e:
        logging.warning(f"⚠️ Ошибка транслитерации имени файла: {str(e)}")
        # Если не удалось транслитерировать, используем оригинальное имя с базовой очисткой
        transliterated_filename = ''.join(c if c.isalnum() or c in '_-.' else '_' for c in filename_no_ext)

    new_filename = f"{timestamp}_{transliterated_filename}{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, new_filename)

    # Сохраняем файл
    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(await file.read())
        logging.info(f"📂 Файл сохранён: {file_path}")
    except Exception as e:
        logging.error(f"❌ Ошибка при сохранении файла: {str(e)}")
        raise ValueError(f"Ошибка при сохранении файла: {str(e)}")

    # Извлекаем текст из файла с обработкой ошибок
    try:
        extracted_text = extract_text_from_any_document(file_path)
        
        # Проверяем, что текст действительно извлечен
        if not extracted_text:
            logging.warning(f"⚠️ Не удалось извлечь текст из файла {file_path}")
            extracted_text = "Не удалось извлечь текст из документа. Возможно, документ пуст или защищен."
        
        elapsed_time = time.time() - start_time
        logging.info(f"⏱️ Общее время обработки файла: {elapsed_time:.2f} секунд")
        return file_path, extracted_text
        
    except Exception as e:
        logging.error(f"❌ Ошибка при извлечении текста из файла: {str(e)}")
        # Возвращаем частичную информацию о файле вместо текста
        file_info = f"Информация о файле: {file.filename}, размер: {os.path.getsize(file_path)} байт. Ошибка извлечения текста: {str(e)}"
        return file_path, file_info