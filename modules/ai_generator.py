
"""
ai_generator.py - Генерация контента с помощью ИИ
"""
import os
from openai import OpenAI


class AIGenerator:
    def __init__(self, config):
        self.config = config
        self.provider = config['ai']['provider']
        self.model = config['ai']['model']
        self.language = config['ai']['language']
        self.temperature = config['ai']['temperature']
        
        # Инициализация клиента
        if self.provider == "openai_gpt":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY не установлен в переменных окружения")
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Неподдерживаемый провайдер ИИ: {self.provider}")

    def _call_ai(self, system_prompt, user_prompt):
        """Универсальный метод для вызова ИИ"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Ошибка при вызове ИИ: {e}")

    def generate_title(self, transcript):
        """Генерация SEO-оптимизированного заголовка"""
        system_prompt = f"Ты - эксперт по SEO для YouTube. Создай привлекательный заголовок на языке {self.language}."
        user_prompt = f"На основе следующей транскрипции создай короткий (до 100 символов) SEO-оптимизированный заголовок:\n\n{transcript[:1000]}"
        return self._call_ai(system_prompt, user_prompt)

    def generate_description(self, transcript, title):
        """Генерация описания видео"""
        system_prompt = f"Ты - эксперт по созданию описаний для YouTube на языке {self.language}."
        user_prompt = f"Создай подробное описание для видео с заголовком '{title}' на основе транскрипции:\n\n{transcript[:2000]}"
        return self._call_ai(system_prompt, user_prompt)

    def generate_tags(self, transcript, title):
        """Генерация тегов"""
        system_prompt = f"Ты - эксперт по SEO-тегам для YouTube на языке {self.language}."
        user_prompt = f"Создай список из 10-15 релевантных тегов для видео '{title}' на основе транскрипции:\n\n{transcript[:1000]}\n\nВерни теги через запятую."
        tags_str = self._call_ai(system_prompt, user_prompt)
        return [tag.strip() for tag in tags_str.split(',')]

    def generate_chapters(self, transcript):
        """Генерация глав (timestamps)"""
        system_prompt = f"Ты - эксперт по структурированию видеоконтента на языке {self.language}."
        user_prompt = f"Создай главы (timestamps) для видео на основе транскрипции. Формат: 'ЧЧ:ММ:СС - Название главы':\n\n{transcript[:3000]}"
        chapters_str = self._call_ai(system_prompt, user_prompt)
        return [line.strip() for line in chapters_str.split('\n') if line.strip()]

    def generate_all(self, transcript):
        """Генерация всего контента"""
        print("  - Генерация заголовка...")
        title = self.generate_title(transcript)
        
        print("  - Генерация описания...")
        description = self.generate_description(transcript, title)
        
        print("  - Генерация тегов...")
        tags = self.generate_tags(transcript, title)
        
        print("  - Генерация глав...")
        chapters = self.generate_chapters(transcript)
        
        return {
            'title': title,
            'description': description,
            'tags': tags,
            'chapters': chapters
        }
