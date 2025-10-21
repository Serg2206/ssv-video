
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
        """Генерация превью"""
        if self.generator == "local_template":
            return self._generate_local(title)
        elif self.generator == "api":
            return self._generate_api(title)
        else:
            raise ValueError(f"Неподдерживаемый генератор превью: {self.generator}")

    def _generate_local(self, title):
        """Генерация превью локально (шаблон)"""
        # Создание простого превью с текстом
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color=(20, 25, 30))
        draw = ImageDraw.Draw(img)
        
        # Попытка загрузить шрифт
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        # Добавление текста
        text = title[:50] + "..." if len(title) > 50 else title
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, (height - text_height) // 2)
        draw.text(position, text, fill=(255, 255, 255), font=font)
        
        # Сохранение
        os.makedirs(self.output_folder, exist_ok=True)
        output_path = os.path.join(self.output_folder, "thumbnail_temp.png")
        img.save(output_path)
        return output_path

    def _generate_api(self, title):
        """Генерация превью через API (заглушка)"""
        # TODO: Реализация через DALL-E или Stable Diffusion
        print("  ! API генерация превью не реализована, используется локальный шаблон")
        return self._generate_local(title)
