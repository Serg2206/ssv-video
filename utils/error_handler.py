"""
Модуль обработки ошибок для SSV-Video.

Предоставляет кастомные классы исключений и декораторы для
автоматического повтора при ошибках API с exponential backoff.
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional
import requests

logger = logging.getLogger(__name__)


# ===== Кастомные классы исключений =====

class SSVVideoError(Exception):
    """Базовый класс для всех исключений SSV-Video."""
    pass


class APIError(SSVVideoError):
    """Ошибка взаимодействия с внешним API."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[dict] = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class OpenAIAPIError(APIError):
    """Ошибка при работе с OpenAI API."""
    pass


class PexelsAPIError(APIError):
    """Ошибка при работе с Pexels API."""
    pass


class PixabayAPIError(APIError):
    """Ошибка при работе с Pixabay API."""
    pass


class ValidationError(SSVVideoError):
    """Ошибка валидации входных данных."""
    pass


class ConfigurationError(SSVVideoError):
    """Ошибка конфигурации приложения."""
    pass


class VideoGenerationError(SSVVideoError):
    """Ошибка при генерации видео."""
    pass


class FileOperationError(SSVVideoError):
    """Ошибка при работе с файлами."""
    pass


# ===== Декораторы для повтора =====

def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (APIError, requests.RequestException)
) -> Callable:
    """
    Декоратор для автоматического повтора функции при ошибках.
    
    Реализует exponential backoff с jitter для предотвращения
    проблем с rate limiting.
    
    Args:
        max_attempts: Максимальное количество попыток
        base_delay: Базовая задержка между попытками (секунды)
        max_delay: Максимальная задержка (секунды)
        exponential_base: База для экспоненциального увеличения
        exceptions: Кортеж типов исключений для перехвата
        
    Returns:
        Декорированная функция с логикой повтора
        
    Example:
        @retry_on_error(max_attempts=5, base_delay=2.0)
        def call_api():
            response = requests.get('https://api.example.com/data')
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Функция {func.__name__} failed after {max_attempts} attempts",
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    # Exponential backoff с jitter
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Добавляем jitter ±25%
                    import random
                    jitter = delay * 0.25 * (2 * random.random() - 1)
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}. "
                        f"Retrying in {actual_delay:.2f}s...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": actual_delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(actual_delay)
            
            # Этот код не должен быть достигнут, но на всякий случай
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def handle_api_errors(func: Callable) -> Callable:
    """
    Декоратор для централизованной обработки API ошибок.
    
    Преобразует requests.RequestException в соответствующие
    кастомные исключения для унифицированной обработки.
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Декорированная функция
        
    Example:
        @handle_api_errors
        def fetch_data_from_api(url: str):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
            
        except requests.Timeout as e:
            logger.error(f"API timeout in {func.__name__}: {str(e)}")
            raise APIError(
                f"API request timed out: {str(e)}",
                status_code=None,
                response_data=None
            )
            
        except requests.ConnectionError as e:
            logger.error(f"API connection error in {func.__name__}: {str(e)}")
            raise APIError(
                f"Failed to connect to API: {str(e)}",
                status_code=None,
                response_data=None
            )
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            response_data = None
            
            try:
                response_data = e.response.json() if e.response else None
            except ValueError:
                response_data = e.response.text if e.response else None
            
            logger.error(
                f"API HTTP error in {func.__name__}",
                extra={
                    "function": func.__name__,
                    "status_code": status_code,
                    "response": response_data
                }
            )
            
            raise APIError(
                f"API returned error status {status_code}: {str(e)}",
                status_code=status_code,
                response_data=response_data
            )
            
        except requests.RequestException as e:
            logger.error(f"General API error in {func.__name__}: {str(e)}")
            raise APIError(
                f"API request failed: {str(e)}",
                status_code=None,
                response_data=None
            )
            
    return wrapper


# ===== Утилиты для работы с ошибками =====

def safe_execute(func: Callable, default_value=None, log_errors: bool = True):
    """
    Безопасно выполняет функцию, возвращая default_value при ошибке.
    
    Args:
        func: Функция для выполнения
        default_value: Значение по умолчанию при ошибке
        log_errors: Логировать ли ошибки
        
    Returns:
        Результат func() или default_value при ошибке
        
    Example:
        result = safe_execute(
            lambda: risky_operation(),
            default_value=[],
            log_errors=True
        )
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(
                f"Error in safe_execute: {str(e)}",
                extra={"error_type": type(e).__name__, "error_message": str(e)}
            )
        return default_value
