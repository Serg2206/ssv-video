"""
ai_generator_v2.py - Улучшенная генерация контента с помощью ИИ (v2.1)

Основные улучшения:
- Интеграция с модулями error_handler, logger, validator
- Автоматическое повторное выполнение при ошибках API
- Структурированное логирование всех операций
- Валидация входных и выходных данных
- Поддержка нескольких AI провайдеров
"""

import os
from typing import Dict, List, Optional
from openai import OpenAI

# Импорт утилит из Phase 1
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.error_handler import (
    retry_on_error, 
    handle_api_errors, 
    APIError, 
    ValidationError,
    safe_execute
)
from utils.logger import setup_logger, log_function_call
from utils.validator import (
    ContentRequest,
    VideoMetadata,
    APICredentials,
    APIProvider,
    validate_text_length
)

# Настройка логгера
logger = setup_logger('ai_generator_v2', 'ai_generator_v2.log')


class AIGeneratorV2:
    """
    Улучшенный генератор AI-контента для видео
    
    Attributes:
        config (Dict): Конфигурация приложения
        provider (APIProvider): Провайдер API (OpenAI, Claude и т.д.)
        model (str): Модель ИИ для использования
        language (str): Язык генерации контента
        temperature (float): Параметр температуры для генерации
        client: Клиент API провайдера
    """
    
    @log_function_call
    def __init__(self, config: Dict):
        """
        Инициализация AI генератора с валидацией
        
        Args:
            config (Dict): Словарь конфигурации
            
        Raises:
            ValidationError: Если конфигурация невалидна
            APIError: Если не удается инициализировать клиент API
        """
        logger.info("Инициализация AIGeneratorV2")
        
        try:
            self.config = config
            self.provider = APIProvider(config['ai']['provider'])
            self.model = config['ai']['model']
            self.language = config['ai']['language']
            self.temperature = config['ai']['temperature']
            
            # Валидация температуры
            if not 0 <= self.temperature <= 2:
                raise ValidationError("temperature", self.temperature, 
                                     "Температура должна быть между 0 и 2")
            
            # Инициализация клиента API
            self._initialize_client()
            
            logger.info(f"AIGeneratorV2 инициализирован: provider={self.provider.value}, "
                       f"model={self.model}, language={self.language}")
                       
        except KeyError as e:
            logger.error(f"Отсутствует обязательный ключ конфигурации: {e}")
            raise ValidationError("config", config, f"Отсутствует ключ: {e}")
        except Exception as e:
            logger.error(f"Ошибка инициализации AIGeneratorV2: {e}")
            raise
    
    @handle_api_errors
    def _initialize_client(self):
        """
        Инициализация клиента API с проверкой учетных данных
        
        Raises:
            APIError: Если API ключ отсутствует или невалиден
        """
        if self.provider == APIProvider.OPENAI_GPT:
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                raise APIError(
                    "openai", 
                    "OPENAI_API_KEY не установлен в переменных окружения",
                    status_code=None
                )
            
            # Валидация API ключа через Pydantic
            credentials = APICredentials(
                provider=self.provider,
                api_key=api_key
            )
            
            self.client = OpenAI(api_key=credentials.api_key)
            logger.info("OpenAI клиент успешно инициализирован")
            
        else:
            raise APIError(
                str(self.provider), 
                f"Неподдерживаемый провайдер ИИ: {self.provider}",
                status_code=None
            )
    
    @retry_on_error(max_attempts=3, delay=2.0, backoff=2.0, jitter=True)
    @handle_api_errors
    @log_function_call
    def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        """
        Универсальный метод для вызова ИИ с автоматическим повтором
        
        Args:
            system_prompt (str): Системный промпт
            user_prompt (str): Пользовательский промпт
            
        Returns:
            str: Ответ от ИИ
            
        Raises:
            APIError: При ошибке вызова API
            ValidationError: При невалидных промптах
        """
        # Валидация промптов
        validate_text_length(system_prompt, max_length=2000, field_name="system_prompt")
        validate_text_length(user_prompt, max_length=10000, field_name="user_prompt")
        
        logger.debug(f"Вызов AI API: system_prompt_len={len(system_prompt)}, "
                    f"user_prompt_len={len(user_prompt)}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature
            )
            
            result = response.choices[0].message.content.strip()
            logger.debug(f"AI ответ получен: длина={len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при вызове AI API: {e}")
            raise APIError("openai", str(e), status_code=None)
    
    @log_function_call
    def generate_title(self, transcript: str) -> str:
        """
        Генерация SEO-оптимизированного заголовка
        
        Args:
            transcript (str): Транскрипция видео
            
        Returns:
            str: Сгенерированный заголовок
        """
        logger.info("Генерация заголовка")
        
        system_prompt = (
            f"Ты - эксперт по SEO для YouTube. "
            f"Создай привлекательный заголовок на языке {self.language}."
        )
        
        user_prompt = (
            f"На основе следующей транскрипции создай короткий "
            f"(до 100 символов) SEO-оптимизированный заголовок:\n\n"
            f"{transcript[:1000]}"
        )
        
        title = self._call_ai(system_prompt, user_prompt)
        
        # Валидация длины заголовка
        if len(title) > 100:
            logger.warning(f"Заголовок слишком длинный ({len(title)} символов), обрезаем")
            title = title[:97] + "..."
        
        logger.info(f"Заголовок сгенерирован: '{title[:50]}...'")
        return title
    
    @log_function_call
    def generate_description(self, transcript: str, title: str) -> str:
        """
        Генерация описания видео
        
        Args:
            transcript (str): Транскрипция видео
            title (str): Заголовок видео
            
        Returns:
            str: Сгенерированное описание
        """
        logger.info("Генерация описания")
        
        system_prompt = (
            f"Ты - эксперт по созданию описаний для YouTube "
            f"на языке {self.language}."
        )
        
        user_prompt = (
            f"Создай подробное описание для видео с заголовком '{title}' "
            f"на основе транскрипции:\n\n{transcript[:2000]}"
        )
        
        description = self._call_ai(system_prompt, user_prompt)
        logger.info(f"Описание сгенерировано: длина={len(description)}")
        
        return description
    
    @log_function_call
    def generate_tags(self, transcript: str, title: str) -> List[str]:
        """
        Генерация тегов
        
        Args:
            transcript (str): Транскрипция видео
            title (str): Заголовок видео
            
        Returns:
            List[str]: Список тегов
        """
        logger.info("Генерация тегов")
        
        system_prompt = (
            f"Ты - эксперт по SEO-тегам для YouTube "
            f"на языке {self.language}."
        )
        
        user_prompt = (
            f"Создай список из 10-15 релевантных тегов для видео '{title}' "
            f"на основе транскрипции:\n\n{transcript[:1000]}\n\n"
            f"Верни теги через запятую."
        )
        
        tags_str = self._call_ai(system_prompt, user_prompt)
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        logger.info(f"Теги сгенерированы: количество={len(tags)}")
        return tags
    
    @log_function_call
    def generate_chapters(self, transcript: str) -> List[str]:
        """
        Генерация глав (timestamps)
        
        Args:
            transcript (str): Транскрипция видео
            
        Returns:
            List[str]: Список глав с временными метками
        """
        logger.info("Генерация глав")
        
        system_prompt = (
            f"Ты - эксперт по структурированию видеоконтента "
            f"на языке {self.language}."
        )
        
        user_prompt = (
            f"Создай главы (timestamps) для видео на основе транскрипции. "
            f"Формат: 'ЧЧ:ММ:СС - Название главы':\n\n{transcript[:3000]}"
        )
        
        chapters_str = self._call_ai(system_prompt, user_prompt)
        chapters = [line.strip() for line in chapters_str.split('\n') if line.strip()]
        
        logger.info(f"Главы сгенерированы: количество={len(chapters)}")
        return chapters
    
    @log_function_call
    def generate_all(self, transcript: str) -> Dict[str, any]:
        """
        Генерация всего контента с валидацией
        
        Args:
            transcript (str): Транскрипция видео
            
        Returns:
            Dict: Словарь с сгенерированным контентом
            {
                'title': str,
                'description': str,
                'tags': List[str],
                'chapters': List[str]
            }
            
        Raises:
            ValidationError: Если транскрипция невалидна
        """
        logger.info("Начало генерации всего контента")
        
        # Валидация входных данных
        validate_text_length(transcript, min_length=100, max_length=50000, 
                           field_name="transcript")
        
        result = {}
        
        # Генерация заголовка
        def gen_title():
            result['title'] = self.generate_title(transcript)
            return result['title']
        
        title = safe_execute(gen_title, logger=logger, 
                           error_message="Ошибка генерации заголовка")
        
        if not title:
            raise APIError("ai_generator", "Не удалось сгенерировать заголовок", 
                         status_code=None)
        
        # Генерация описания
        def gen_description():
            result['description'] = self.generate_description(transcript, title)
            return result['description']
        
        safe_execute(gen_description, logger=logger,
                   error_message="Ошибка генерации описания")
        
        # Генерация тегов
        def gen_tags():
            result['tags'] = self.generate_tags(transcript, title)
            return result['tags']
        
        safe_execute(gen_tags, logger=logger,
                   error_message="Ошибка генерации тегов")
        
        # Генерация глав
        def gen_chapters():
            result['chapters'] = self.generate_chapters(transcript)
            return result['chapters']
        
        safe_execute(gen_chapters, logger=logger,
                   error_message="Ошибка генерации глав")
        
        logger.info("Генерация всего контента завершена успешно")
        logger.debug(f"Результат: title={result.get('title', 'N/A')[:50]}, "
                    f"tags_count={len(result.get('tags', []))}, "
                    f"chapters_count={len(result.get('chapters', []))}")
        
        return result
