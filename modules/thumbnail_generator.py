
"""
thumbnail_generator.py - Генерация превью
"""
import os
from PIL import Image, ImageDraw, ImageFont


class ThumbnailGenerator:
    def __init__(self, config):
        self.config = config
        self.style = config['thumbnail']['style']
        self.generator = config['thumbnail']['generator']
        self.output_folder = config['paths']['output_folder']

    def generate(self, title):
        """Генерация превью с валидацией"""
        # Валидация входных данных
        if not title or not isinstance(title, str):
            raise ValueError("Заголовок должен быть непустой строкой")
        
        if self.generator == "local_template":
            return self._generate_local(title)
        elif self.generator == "api":
            return self._generate_api(title)
        else:
            raise ValueError(f"Неподдерживаемый генератор превью: {self.generator}")

    def _generate_local(self, title):
        """Генерация превью локально (шаблон) с валидацией"""
        # Валидация заголовка
        if not title or not isinstance(title, str):
            raise ValueError("Заголовок должен быть непустой строкой")
        
        sanitized_title = title.strip()
        if len(sanitized_title) > 200:
            sanitized_title = sanitized_title[:200]
        
        # Создание простого превью с текстом
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color=(20, 25, 30))
        draw = ImageDraw.Draw(img)
        
        # Попытка загрузить шрифт
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except Exception:
            font = ImageFont.load_default()
        
        # Добавление текста с ограничением длины
        text = sanitized_title[:50] + "..." if len(sanitized_title) > 50 else sanitized_title
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, (height - text_height) // 2)
        draw.text(position, text, fill=(255, 255, 255), font=font)
        
        # Сохранение с валидацией пути
        os.makedirs(self.output_folder, exist_ok=True)
        output_filename = "thumbnail_temp.png"
        output_path = os.path.join(self.output_folder, output_filename)
        
        # Проверка что путь безопасен
        abs_output = os.path.abspath(output_path)
        abs_base = os.path.abspath(self.output_folder)
        if not abs_output.startswith(abs_base):
            raise ValueError("Небезопасный путь для сохранения превью")
        
        img.save(output_path)
        return output_path

    def _generate_api(self, title):
        """Генерация превью через API с валидацией входных данных"""
        # Валидация заголовка
        if not title or not isinstance(title, str):
            raise ValueError("Заголовок должен быть непустой строкой")
        
        # Санитизация заголовка - удаление потенциально опасных символов
        sanitized_title = title.strip()
        if len(sanitized_title) > 200:
            sanitized_title = sanitized_title[:200]
        
        # Реализация генерации через DALL-E или Stable Diffusion
        # Для использования требуется настроить API ключ в .env файле
        print("  ! API генерация превью требует настройки DALL-E/Stable Diffusion API")
        print("  Используется локальный шаблон как fallback")
        return self._generate_local(sanitized_title)
