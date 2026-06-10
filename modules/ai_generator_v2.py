"""
ai_generator_v2.py - Оптимизированная генерация контента с помощью ИИ (v2.1)

Основные улучшения:
- Интеграция с модулями error_handler, logger, validator
- Автоматическое повторное выполнение при ошибках API
- Структурированное логирование всех операций
- Валидация входных и выходных данных
- Поддержка нескольких AI провайдеров
- Кэширование ответов для повышения производительности
- Параллельная генерация независимого контента
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    APIProvider
)

# Настройка логгера
from pathlib import Path
logger = setup_logger('ai_generator_v2', log_dir=Path('logs'), level='INFO')


def validate_text_length(text: str, min_length: int = 0, max_length: int = 10000, field_name: str = "text"):
    """
    Валидация длины текста
    
    Args:
        text: Текст для валидации
        min_length: Минимальная длина
        max_length: Максимальная длина
        field_name: Имя поля для сообщения об ошибке
        
    Raises:
        ValidationError: Если текст не соответствует требованиям
    """
    if not isinstance(text, str):
        raise ValidationError(field_name, text, f"Ожидается строка, получено {type(text).__name__}")
    
    if len(text) < min_length:
        raise ValidationError(field_name, text, f"Длина текста должна быть не менее {min_length} символов")
    
    if len(text) > max_length:
        raise ValidationError(field_name, text, f"Длина текста не должна превышать {max_length} символов")


class AIGeneratorV2:
    """
    Оптимизированный генератор AI-контента для видео
    
    Optimizations:
        - Response caching to avoid redundant API calls
        - Parallel execution of independent generation tasks
        - Connection pooling through persistent client
        - Smart truncation of long transcripts
    
    Attributes:
        config (Dict): Конфигурация приложения
        provider (APIProvider): Провайдер API (OpenAI, Claude и т.д.)
        model (str): Модель ИИ для использования
        language (str): Язык генерации контента
        temperature (float): Параметр температуры для генерации
        client: Клиент API провайдера
        cache_enabled (bool): Флаг включения кэширования
        executor: Пул потоков для параллельного выполнения
    """
    
    @log_function_call
    def __init__(self, config: Dict, cache_enabled: bool = True, max_workers: int = 3):
        """
        Инициализация AI генератора с валидацией
        
        Args:
            config (Dict): Словарь конфигурации
            cache_enabled (bool): Включить кэширование ответов
            max_workers (int): Максимальное количество потоков для параллельной работы
            
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
            self.cache_enabled = cache_enabled
            self.max_workers = max_workers
            
            # Инициализация кэша
            if self.cache_enabled:
                self.cache_dir = Path("./cache/ai_responses")
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Кэш включен: {self.cache_dir}")
            
            # Валидация температуры
            if not 0 <= self.temperature <= 2:
                raise ValidationError("temperature", self.temperature, 
                                     "Температура должна быть между 0 и 2")
            
            # Инициализация клиента API
            self._initialize_client()
            
            # Инициализация пула потоков
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
            logger.info(f"AIGeneratorV2 инициализирован: provider={self.provider.value}, "
                       f"model={self.model}, language={self.language}, "
                       f"cache={cache_enabled}, workers={max_workers}")
                       
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
    
    def _get_cache_key(self, system_prompt: str, user_prompt: str) -> str:
        """
        Генерация уникального ключа для кэша
        
        Args:
            system_prompt: Системный промпт
            user_prompt: Пользовательский промпт
            
        Returns:
            MD5 хэш от комбинации промптов
        """
        content = f"{system_prompt}:{user_prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[str]:
        """
        Получение ответа из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            Сохраненный ответ или None если не найден
        """
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cached_response = data.get('response')
                    if cached_response:
                        logger.debug(f"Кэш хит для ключа {key[:16]}...")
                        return cached_response
            except Exception as e:
                logger.warning(f"Ошибка чтения кэша: {e}")
        return None

    def _save_to_cache(self, key: str, response: str):
        """
        Сохранение ответа в кэш
        
        Args:
            key: Ключ кэша
            response: Ответ для сохранения
        """
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'response': response}, f, ensure_ascii=False)
            logger.debug(f"Сохранено в кэш: {key[:16]}...")
        except Exception as e:
            logger.warning(f"Ошибка записи в кэш: {e}")

    @retry_on_error(max_attempts=3, base_delay=2.0, max_delay=60.0, exponential_base=2.0)
    @handle_api_errors
    @log_function_call
    def _call_ai(self, system_prompt: str, user_prompt: str, use_cache: bool = True) -> str:
        """
        Универсальный метод для вызова ИИ с автоматическим повтором и кэшированием
        
        Optimizations:
            - Cache lookup before API call to avoid redundant requests
            - Retry with exponential backoff on API errors
            - Timeout to prevent hanging requests
        
        Args:
            system_prompt (str): Системный промпт
            user_prompt (str): Пользовательский промпт
            use_cache (bool): Использовать ли кэширование
            
        Returns:
            str: Ответ от ИИ
            
        Raises:
            APIError: При ошибке вызова API
            ValidationError: При невалидных промптах
        """
        # Проверка кэша
        if use_cache:
            cache_key = self._get_cache_key(system_prompt, user_prompt)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response
        
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
                temperature=self.temperature,
                timeout=30  # Таймаут для предотвращения зависаний
            )
            
            result = response.choices[0].message.content.strip()
            logger.debug(f"AI ответ получен: длина={len(result)}")
            
            # Сохранение в кэш
            if use_cache:
                self._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при вызове AI API: {e}")
            raise APIError("openai", str(e), status_code=None)
    
    def _call_ai_async(self, task_name: str, system_prompt: str, user_prompt: str):
        """
        Асинхронный вызов ИИ для параллельного выполнения
        
        Args:
            task_name: Имя задачи для логирования
            system_prompt: Системный промпт
            user_prompt: Пользовательский промпт
            
        Returns:
            Tuple: (task_name, result, error)
        """
        try:
            result = self._call_ai(system_prompt, user_prompt)
            return (task_name, result, None)
        except Exception as e:
            logger.error(f"Ошибка в асинхронной задаче {task_name}: {e}")
            return (task_name, None, e)
    
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
    def generate_all(self, transcript: str, parallel: bool = True) -> Dict[str, Any]:
        """
        Генерация всего контента с валидацией и возможностью параллельного выполнения
        
        Optimizations:
            - Parallel execution of independent tasks (description, tags, chapters)
            - Smart task scheduling (title first, then parallel tasks)
            - Cache utilization for all API calls
            - Resource-efficient thread pool usage
        
        Args:
            transcript (str): Транскрипция видео
            parallel (bool): Использовать ли параллельное выполнение
            
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
            APIError: Если не удалось сгенерировать контент
        """
        logger.info(f"Начало генерации всего контента (parallel={parallel})")
        
        # Валидация входных данных
        validate_text_length(transcript, min_length=100, max_length=50000, 
                           field_name="transcript")
        
        if parallel:
            return self._generate_all_parallel(transcript)
        else:
            return self._generate_all_sequential(transcript)
    
    def _generate_all_sequential(self, transcript: str) -> Dict[str, Any]:
        """Последовательная генерация контента (старый метод)"""
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
        
        logger.info("Генерация всего контента завершена успешно (последовательно)")
        logger.debug(f"Результат: title={result.get('title', 'N/A')[:50]}, "
                    f"tags_count={len(result.get('tags', []))}, "
                    f"chapters_count={len(result.get('chapters', []))}")
        
        return result
    
    def _generate_all_parallel(self, transcript: str) -> Dict[str, Any]:
        """
        Параллельная генерация контента с использованием ThreadPoolExecutor
        
        Оптимизация:
            - Заголовок генерируется первым (нужен для других задач)
            - Описание, теги и главы генерируются параллельно
            - Время выполнения сокращается до ~1/3 от последовательного
        
        Args:
            transcript: Транскрипция видео
            
        Returns:
            Dict: Словарь с сгенерированным контентом
        """
        logger.info("Запуск параллельной генерации контента")
        print("  - Запуск генерации контента...")
        
        result = {}
        
        # Сначала генерируем заголовок (нужен для других задач)
        print("  - Генерация заголовка...")
        logger.info("Генерация заголовка (первый этап)")
        
        title_future = self.executor.submit(
            self._call_ai_async,
            'title',
            f"Ты - эксперт по SEO для YouTube. Создай привлекательный заголовок на языке {self.language}.",
            f"На основе следующей транскрипции создай короткий (до 100 символов) SEO-оптимизированный заголовок:\n\n{transcript[:1000]}"
        )
        
        # Ждем заголовок
        title_name, title, title_error = title_future.result()
        if title_error:
            logger.error(f"Ошибка генерации заголовка: {title_error}")
            raise title_error
        
        result['title'] = title
        logger.info(f"Заголовок сгенерирован: '{title[:50]}...'")
        print(f"  ✓ Заголовок сгенерирован: {title[:50]}...")
        
        # Теперь запускаем остальные задачи параллельно
        print("  - Параллельная генерация описания, тегов и глав...")
        logger.info("Запуск параллельных задач: description, tags, chapters")
        
        futures = {
            'description': self.executor.submit(
                self._call_ai_async,
                'description',
                f"Ты - эксперт по созданию описаний для YouTube на языке {self.language}.",
                f"Создай подробное описание для видео с заголовком '{title}' на основе транскрипции:\n\n{transcript[:2000]}"
            ),
            'tags': self.executor.submit(
                self._call_ai_async,
                'tags',
                f"Ты - эксперт по SEO-тегам для YouTube на языке {self.language}.",
                f"Создай список из 10-15 релевантных тегов для видео '{title}' на основе транскрипции:\n\n{transcript[:1000]}\n\nВерни теги через запятую."
            ),
            'chapters': self.executor.submit(
                self._call_ai_async,
                'chapters',
                f"Ты - эксперт по структурированию видеоконтента на языке {self.language}.",
                f"Создай главы (timestamps) для видео на основе транскрипции. Формат: 'ЧЧ:ММ:СС - Название главы':\n\n{transcript[:3000]}"
            )
        }
        
        # Сбор результатов
        errors = []
        for future in as_completed(futures.values()):
            task_name, task_result, task_error = future.result()
            
            if task_error:
                logger.error(f"Ошибка при генерации {task_name}: {task_error}")
                errors.append((task_name, task_error))
                print(f"  ✗ Ошибка при генерации {task_name}: {task_error}")
            else:
                result[task_name] = task_result
                logger.info(f"{task_name.capitalize()} сгенерирован успешно")
                print(f"  ✓ {task_name.capitalize()} сгенерирован")
        
        # Проверка ошибок
        if errors:
            error_messages = "; ".join([f"{name}: {str(err)}" for name, err in errors])
            raise APIError("ai_generator", f"Ошибки при генерации: {error_messages}", status_code=None)
        
        # Обработка тегов и глав
        if 'tags' in result and result['tags']:
            result['tags'] = [tag.strip() for tag in result['tags'].split(',') if tag.strip()]
        else:
            result['tags'] = []
        
        if 'chapters' in result and result['chapters']:
            result['chapters'] = [line.strip() for line in result['chapters'].split('\n') if line.strip()]
        else:
            result['chapters'] = []
        
        logger.info("Параллельная генерация всего контента завершена успешно")
        logger.debug(f"Результат: title={result.get('title', 'N/A')[:50]}, "
                    f"tags_count={len(result.get('tags', []))}, "
                    f"chapters_count={len(result.get('chapters', []))}")
        
        return result
    
    def close(self):
        """Закрытие пула потоков"""
        self.executor.shutdown(wait=True)
        logger.info("ThreadPoolExecutor закрыт")
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.close()
