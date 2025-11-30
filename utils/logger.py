"""
Модуль структурированного логирования для SSV-Video.

Предоставляет централизованную систему логирования с поддержкой
JSON формата, цветного вывода в консоль и ротации логов.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from colorama import Fore, Style, init

# Инициализация colorama для Windows
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Форматтер для цветного вывода логов в консоль."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует запись лога с цветовым выделением.
        
        Args:
            record: Запись лога для форматирования
            
        Returns:
            Отформатированная строка с ANSI цветовыми кодами
        """
        # Сохраняем оригинальное имя уровня
        levelname = record.levelname
        
        # Применяем цвет
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        
        # Форматируем сообщение
        formatted = super().format(record)
        
        # Восстанавливаем оригинальное имя уровня
        record.levelname = levelname
        
        return formatted


class JSONFormatter(logging.Formatter):
    """Форматтер для вывода логов в формате JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует запись лога в JSON формат.
        
        Args:
            record: Запись лога для форматирования
            
        Returns:
            JSON строка с информацией о логе
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Добавляем дополнительные поля из extra
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 
                              'funcName', 'levelname', 'levelno', 'lineno', 
                              'module', 'msecs', 'pathname', 'process', 
                              'processName', 'relativeCreated', 'thread', 
                              'threadName', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value
        
        # Добавляем информацию об исключении, если есть
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    name: str = 'ssv_video',
    log_dir: Optional[Path] = None,
    level: str = 'INFO',
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_output: bool = True,
    json_output: bool = True,
    colored_console: bool = True
) -> logging.Logger:
    """
    Настраивает и возвращает логгер с несколькими обработчиками.
    
    Args:
        name: Имя логгера
        log_dir: Директория для файлов логов (по умолчанию ./logs)
        level: Уровень логирования ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        max_bytes: Максимальный размер файла лога перед ротацией
        backup_count: Количество старых файлов логов для сохранения
        console_output: Выводить ли логи в консоль
        json_output: Создавать ли JSON файл логов
        colored_console: Использовать ли цветной вывод в консоль
        
    Returns:
        Настроенный логгер
        
    Example:
        logger = setup_logger('my_module', level='DEBUG')
        logger.info('Application started')
        logger.error('Error occurred', extra={'user_id': 123})
    """
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Удаляем существующие обработчики (чтобы избежать дублирования)
    logger.handlers.clear()
    
    # Создаем директорию для логов, если не существует
    if log_dir is None:
        log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. Консольный обработчик
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if colored_console:
            console_format = (
                f"{Fore.BLUE}[%(asctime)s]{Style.RESET_ALL} "
                f"%(levelname)s "
                f"{Fore.MAGENTA}%(name)s{Style.RESET_ALL} - "
                f"%(message)s"
            )
            console_formatter = ColoredFormatter(console_format, datefmt='%Y-%m-%d %H:%M:%S')
        else:
            console_format = '[%(asctime)s] %(levelname)s %(name)s - %(message)s'
            console_formatter = logging.Formatter(console_format, datefmt='%Y-%m-%d %H:%M:%S')
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 2. Файловый обработчик (текстовый формат с ротацией)
    log_file = log_dir / f'{name}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
    file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 3. JSON файловый обработчик (с ротацией)
    if json_output:
        json_log_file = log_dir / f'{name}.json.log'
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
    
    return logger


def log_function_call(logger: logging.Logger):
    """
    Декоратор для автоматического логирования вызовов функций.
    
    Args:
        logger: Логгер для записи информации
        
    Returns:
        Декоратор функции
        
    Example:
        logger = setup_logger('my_module')
        
        @log_function_call(logger)
        def process_data(data):
            return len(data)
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling function: {func_name}",
                extra={
                    'function': func_name,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"Function {func_name} completed successfully",
                    extra={'function': func_name}
                )
                return result
                
            except Exception as e:
                logger.error(
                    f"Function {func_name} raised an exception: {str(e)}",
                    extra={
                        'function': func_name,
                        'exception_type': type(e).__name__,
                        'exception_message': str(e)
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator


# Создаем глобальный логгер по умолчанию
default_logger = setup_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Получает логгер по имени или возвращает дефолтный.
    
    Args:
        name: Имя логгера (опционально)
        
    Returns:
        Логгер
        
    Example:
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info('Module initialized')
    """
    if name:
        return logging.getLogger(name)
    return default_logger
