
"""
thumbnail_generator.py - Генерация превью
Поддерживает: локальные шаблоны и DALL-E API
"""
import os
from PIL import Image, ImageDraw, ImageFont
import requests


class ThumbnailGenerator:
    def __init__(self, config):
        self.config = config
        self.style = config['thumbnail']['style']
        self.generator = config['thumbnail']['generator']
        self.output_folder = config['paths']['output_folder']
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

    def generate(self, title, description=""):
        """Генерация превью"""
        if self.generator == "local_template":
            return self._generate_local(title)
        elif self.generator == "dalle":
            return self._generate_dalle(title, description)
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

    def _generate_dalle(self, title, description=""):
        """Генерация превью через DALL-E API"""
        if not self.openai_api_key:
            print("  ! OPENAI_API_KEY не найден. Используем локальный шаблон.")
            return self._generate_local(title)
        
        print("  - Генерация превью через DALL-E...")
        
        # Формирование промпта для DALL-E
        prompt = (
            f"Professional YouTube thumbnail for medical/surgical journal. "
            f"Title: '{title}'. "
            f"Style: modern, clean, professional, high contrast, visually striking. "
            f"Include medical/surgical imagery if relevant. "
            f"Text should be minimal or absent (will be added later). "
            f"Resolution: 1280x720. Color scheme: blue, white, gray tones."
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",  # DALL-E 3 поддерживает 1024x1024, 1792x1024, 1024x1792
                "quality": "hd",
                "style": "vivid"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"  ! Ошибка DALL-E API: {response.status_code} - {response.text}")
                return self._generate_local(title)
            
            data = response.json()
            image_url = data['data'][0]['url']
            
            # Скачивание изображения
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code != 200:
                print("  ! Не удалось скачать изображение от DALL-E")
                return self._generate_local(title)
            
            # Сохранение
            os.makedirs(self.output_folder, exist_ok=True)
            output_path = os.path.join(self.output_folder, "thumbnail_dalle.png")
            with open(output_path, 'wb') as f:
                f.write(img_response.content)
            
            print(f"  ✓ Превью DALL-E сохранено: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"  ! Ошибка при генерации DALL-E: {e}. Используем локальный шаблон.")
            return self._generate_local(title)
