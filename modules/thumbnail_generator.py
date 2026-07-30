
"""
thumbnail_generator.py - Генерация превью

Поддерживает два режима:
  - "local_template": однотонный фон + заголовок (без сети)
  - "api": бесплатный ИИ-фон через Pollinations.ai (без API-ключа) + заголовок поверх
"""
import os
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont


class ThumbnailGenerator:
    def __init__(self, config):
        self.config = config
        self.style = config['thumbnail']['style']
        self.generator = config['thumbnail']['generator']
        self.api_provider = config['thumbnail'].get('api_provider', 'pollinations')
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
        """Генерация превью локально (однотонный фон + текст)"""
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color=(20, 25, 30))
        return self._draw_title(img, title)

    def _generate_api(self, title):
        """Генерация фона превью через бесплатный Pollinations.ai + наложение заголовка"""
        width, height = 1280, 720

        if self.api_provider != "pollinations":
            print(f"  ! Провайдер '{self.api_provider}' не поддерживается, использую локальный шаблон")
            return self._generate_local(title)

        os.makedirs(self.output_folder, exist_ok=True)
        bg_path = os.path.join(self.output_folder, "thumbnail_bg_temp.png")
        prompt = f"{title}, медицинская иллюстрация, обложка YouTube, кинематографично"
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

        try:
            response = requests.get(
                url, params={"width": width, "height": height, "nologo": "true"}, timeout=30
            )
            response.raise_for_status()
            with open(bg_path, 'wb') as f:
                f.write(response.content)
            img = Image.open(bg_path).convert('RGB').resize((width, height))
        except Exception as e:
            print(f"  ! Не удалось получить фон Pollinations ({e}), использую локальный шаблон")
            return self._generate_local(title)

        return self._draw_title(img, title)

    def _draw_title(self, img, title):
        """Накладывает заголовок с плашкой для читаемости поверх любого фона"""
        width, height = img.size
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except Exception:
            font = ImageFont.load_default()

        text = title[:50] + "..." if len(title) > 50 else title
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((width - text_width) // 2, height - text_height - 60)

        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [0, position[1] - 20, width, position[1] + text_height + 20],
            fill=(0, 0, 0, 140)
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text(position, text, fill=(255, 255, 255), font=font)

        os.makedirs(self.output_folder, exist_ok=True)
        output_path = os.path.join(self.output_folder, "thumbnail_temp.png")
        img.save(output_path)
        return output_path
