
"""
ai_generator.py - Генерация контента с помощью ИИ
Поддержка OpenAI, Anthropic Claude, Google Gemini и локальных моделей (Ollama)
"""
import os
from openai import OpenAI
from typing import Optional, Dict, Any


class AIGenerator:
    def __init__(self, config):
        self.config = config
        self.provider = config['ai']['provider']
        self.model = config['ai']['model']
        self.language = config['ai']['language']
        self.temperature = config['ai']['temperature']
        self.client = None
        
        # Инициализация клиента в зависимости от провайдера
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента для различных AI провайдеров"""
        if self.provider == "openai_gpt":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY не установлен в переменных окружения")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            
        elif self.provider == "anthropic_claude":
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY не установлен")
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("Установите anthropic: pip install anthropic")
                
        elif self.provider == "google_gemini":
            try:
                import google.generativeai as genai
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY не установлен")
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("Установите google-generativeai: pip install google-generativeai")
                
        elif self.provider == "ollama_local":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            api_key = os.getenv("OLLAMA_API_KEY", "ollama")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
            
        else:
            raise ValueError(f"Неподдерживаемый провайдер ИИ: {self.provider}. "
                           f"Доступные: openai_gpt, anthropic_claude, google_gemini, ollama_local")

    def _call_ai(self, system_prompt, user_prompt):
        """Универсальный метод для вызова ИИ с поддержкой разных провайдеров"""
        try:
            if self.provider == "anthropic_claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.config['ai'].get('max_tokens', 2000),
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return response.content[0].text.strip()
                
            elif self.provider == "google_gemini":
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.client.generate_content(full_prompt)
                return response.text.strip()
                
            else:  # OpenAI и Ollama
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
            raise Exception(f"Ошибка при вызове ИИ ({self.provider}): {e}")

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
        """Генерация всего контента с использованием параллельных запросов"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print("  - Генерация заголовка и тегов (параллельно)...")
        
        # Параллельное выполнение независимых задач
        futures = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Заголовок нужен первым для описания и тегов
            title_future = executor.submit(self.generate_title, transcript)
            
            # Главы можно генерировать независимо
            chapters_future = executor.submit(self.generate_chapters, transcript)
            
            # Дожидаемся заголовка
            title = title_future.result()
            print(f"  ✓ Заголовок: {title}")
            
            # Теперь запускаем описание и теги параллельно
            description_future = executor.submit(self.generate_description, transcript, title)
            tags_future = executor.submit(self.generate_tags, transcript, title)
            
            # Собираем все результаты
            results = {}
            for future in as_completed([description_future, tags_future, chapters_future]):
                if future is description_future:
                    results['description'] = future.result()
                    print("  ✓ Описание готово")
                elif future is tags_future:
                    results['tags'] = future.result()
                    print("  ✓ Теги готовы")
                elif future is chapters_future:
                    results['chapters'] = future.result()
                    print("  ✓ Главы готовы")
        
        return {
            'title': title,
            'description': results['description'],
            'tags': results['tags'],
            'chapters': results['chapters']
        }
