from docx import Document

def extract_text_from_docx(docx_file_path):
    """
    Извлекает текст из .docx файла и удаляет пустые строки.
    """
    try:
        document = Document(docx_file_path)
        full_text = "\n".join([p.text.strip() for p in document.paragraphs if p.text.strip()])
        return full_text
    except Exception as e:
        raise ValueError(f"Ошибка при обработке документа: {e}")
