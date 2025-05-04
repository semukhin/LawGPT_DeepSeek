import asyncio
import os
import argparse
from app.services.gemini_service import gemini_service
import google

async def main():
    parser = argparse.ArgumentParser(description='Извлечение текста из PDF или изображения с помощью Gemini')
    parser.add_argument('file_path', type=str, nargs='?', default='test.pdf', help='Путь к файлу (PDF или изображение)')
    args = parser.parse_args()
    
    test_file = args.file_path
    if not os.path.isabs(test_file):
        # Если путь относительный, ищем относительно корня проекта
        test_file = os.path.join(os.path.dirname(__file__), test_file)
    if not os.path.exists(test_file):
        print(f"❌ Файл не найден: {test_file}")
        return
        
    ext = os.path.splitext(test_file)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.webp': 'image/webp',
    }
    with open(test_file, "rb") as f:
        file_bytes = f.read()
    if ext in image_exts:
        mime_type = mime_types.get(ext, 'image/png')
        print(f"Распознаётся изображение: {test_file} (mime: {mime_type})")
        result = await gemini_service.extract_text_from_image(file_bytes, mime_type=mime_type)
    else:
        print(f"Распознаётся PDF: {test_file}")
        result = await gemini_service.extract_text_from_pdf(file_bytes)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

print(google.__file__)