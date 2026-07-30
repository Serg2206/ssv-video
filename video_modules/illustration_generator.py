
"""
illustration_generator.py - Бесплатная генерация иллюстраций через Pollinations.ai

Pollinations.ai не требует API-ключа и регистрации (в отличие от DALL-E/
Stable Diffusion API), поэтому подходит как генератор "из коробки" без
дополнительной настройки. При недоступности сети/сервиса используется
однотонный фон - пайплайн не падает.

Внимание: для медицинского/научного контента сгенерированные иллюстрации
носят иллюстративный, а не анатомически точный характер - перед публикацией
их стоит проверять (или отключить illustrations.enabled и использовать
собственные схемы).
"""
import os
import sys
import urllib.parse

import requests
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.error_handler import retry_on_error, handle_api_errors


class IllustrationGenerator:
    """Создаёт фоновые иллюстрации для сегментов видео через бесплатный Pollinations.ai."""

    BASE_URL = "https://image.pollinations.ai/prompt/{prompt}"

    def __init__(self, config):
        cfg = config.get('illustrations', {})
        self.enabled = cfg.get('enabled', True)
        self.style_suffix = cfg.get('style_suffix', '')
        self.fallback_color = tuple(cfg.get('fallback_color', [20, 25, 30]))
        self.timeout = cfg.get('timeout', 30)

    def generate(self, prompt: str, width: int, height: int, output_path: str) -> str:
        """Генерирует изображение по описанию; при ошибке - однотонный фон (без падения пайплайна)."""
        if self.enabled:
            try:
                self._fetch(prompt, width, height, output_path)
                return output_path
            except Exception as e:
                print(f"  ! Иллюстрация Pollinations недоступна ({e}), использую однотонный фон")

        return self._fallback(width, height, output_path)

    @retry_on_error(max_attempts=2, base_delay=1.5)
    @handle_api_errors
    def _fetch(self, prompt, width, height, output_path):
        full_prompt = f"{prompt}, {self.style_suffix}" if self.style_suffix else prompt
        url = self.BASE_URL.format(prompt=urllib.parse.quote(full_prompt))
        response = requests.get(
            url,
            params={"width": width, "height": height, "nologo": "true"},
            timeout=self.timeout
        )
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)

    def _fallback(self, width, height, output_path):
        img = Image.new('RGB', (width, height), color=self.fallback_color)
        img.save(output_path)
        return output_path
