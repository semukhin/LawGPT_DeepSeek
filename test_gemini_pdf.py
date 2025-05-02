import asyncio
import os
from app.services.gemini_service import gemini_service
import google

async def main():
    # Замените путь на свой тестовый файл (PDF или изображение)
    test_file = "test.pdf"  # Можно указать test.png, test.jpg и т.д.
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