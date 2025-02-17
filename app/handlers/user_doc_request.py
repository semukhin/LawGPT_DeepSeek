import os
import subprocess
from docx import Document
import mammoth
import magic
import logging
import fitz 
import pytesseract
from pdf2image import convert_from_path


# Настройка Tesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


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
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext in [".pdf"]:
        return extract_text_from_pdf(file_path)
    elif ext in [".doc", ".docx"]:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {ext}")
