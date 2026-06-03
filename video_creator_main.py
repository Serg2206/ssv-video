
#!/usr/bin/env python3
"""
video_creator_main.py - Скрипт для генерации видео из пакета ssv-video v2.1
Оптимизированная версия с улучшенной обработкой ошибок и логированием
"""
import os
import sys
import argparse
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Импорт модулей с обработкой ошибок
try:
    from video_modules.text_on_screen_generator import TextOnScreenGenerator
    from utils.logger import setup_logger, get_logger
    from utils.error_handler import safe_execute, SSVVideoError
    from utils.validator import validate_file_path, validate_directory
except ImportError as e:
    print(f"Критическая ошибка импорта: {e}")
    sys.exit(1)

# Настройка логгера
logger = setup_logger(
    name='ssv_video_creator',
    log_dir=Path('logs'),
    level=os.getenv('LOG_LEVEL', 'INFO'),
    console_output=True,
    json_output=True
)


def load_config(config_path: str = "video_config.yaml") -> Dict[str, Any]:
    """Загрузка конфигурации для генерации видео с валидацией"""
    try:
        config_file = Path(config_path)
        validate_file_path(config_file, must_exist=True)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Валидация обязательных секций
        required_sections = ['project', 'paths', 'video_generation']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Отсутствует обязательная секция: {section}")
        
        # Создание директорий если не существуют
        for path_key in ['input_folder', 'output_folder']:
            if path_key in config['paths']:
                validate_directory(Path(config['paths'][path_key]), create=True)
        
        logger.info(f"Конфигурация загружена: {config_path}")
        return config
        
    except FileNotFoundError:
        logger.error(f"Файл конфигурации не найден: {config_path}")
        print(f"Ошибка: Файл конфигурации '{config_path}' не найден.")
        print("Создайте файл конфигурации или используйте --config для указания пути.")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Ошибка парсинга YAML: {e}")
        print(f"Ошибка при парсинге YAML: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}", exc_info=True)
        print(f"Ошибка загрузки конфигурации: {e}")
        sys.exit(1)


def load_package_metadata(package_path: Path) -> Dict[str, Any]:
    """Загрузка метаданных из пакета ssv-video с валидацией"""
    metadata_path = package_path / "metadata.json"
    
    try:
        validate_file_path(metadata_path, must_exist=True)
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Валидация обязательных полей
        required_fields = ['title']
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Отсутствует обязательное поле в метаданных: {field}")
        
        logger.info(f"Метаданные загружены: {metadata.get('title', 'Без названия')[:50]}")
        return metadata
        
    except FileNotFoundError:
        logger.error(f"Файл метаданных не найден: {metadata_path}")
        print(f"Ошибка: Файл метаданных не найден в {package_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        print(f"Ошибка: Некорректный формат metadata.json: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка загрузки метаданных: {e}", exc_info=True)
        print(f"Ошибка загрузки метаданных: {e}")
        sys.exit(1)


def main():
    """Основная функция генерации видео из пакета"""
    parser = argparse.ArgumentParser(
        description="SSV Video Creator v2.1 - Генерация видео из пакета",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python video_creator_main.py --package_path ./output/2024-05-21_package
  python video_creator_main.py --package_path ./output/my_package --output_filename my_video.mp4
  python video_creator_main.py --package_path ./output/package --config custom_video_config.yaml
        """
    )
    parser.add_argument(
        "--package_path", 
        required=True, 
        help="Путь к папке пакета ssv-video"
    )
    parser.add_argument(
        "--output_filename", 
        default="final_video.mp4", 
        help="Имя выходного видеофайла (по умолчанию: final_video.mp4)"
    )
    parser.add_argument(
        "--config", 
        default="video_config.yaml", 
        help="Путь к файлу конфигурации (по умолчанию: video_config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Тестовый запуск без реальной генерации видео"
    )
    args = parser.parse_args()

    # Загрузка конфигурации
    config = load_config(args.config)
    
    # Проверка пакета
    package_path = Path(args.package_path)
    try:
        validate_directory(package_path, create=False)
    except ValueError as e:
        logger.error(f"Ошибка валидации пути пакета: {e}")
        print(f"Ошибка: Папка пакета '{args.package_path}' не найдена.")
        sys.exit(1)

    version = config['project'].get('version', '2.1')
    logger.info(f"Запуск SSV Video Creator v{version}", extra={
        'package_path': str(package_path),
        'output_filename': args.output_filename
    })
    
    print(f"\n{'='*60}")
    print(f"=== SSV Video Creator v{version} ===")
    print(f"{'='*60}")
    print(f"Пакет: {package_path.absolute()}")
    print(f"Выходной файл: {args.output_filename}")
    if args.dry_run:
        print("РЕЖИМ: Тестовый запуск (dry-run)")
    print(f"{'='*60}\n")

    start_time = datetime.now()
    
    try:
        # Загрузка метаданных пакета
        print("[1/3] Загрузка метаданных пакета...")
        logger.info("Загрузка метаданных пакета")
        
        def load_metadata():
            return load_package_metadata(package_path)
        
        metadata = safe_execute(
            load_metadata,
            default_value=None,
            log_errors=False
        )
        
        if not metadata:
            raise SSVVideoError("Не удалось загрузить метаданные пакета")
            
        print(f"✓ Метаданные загружены: {metadata.get('title', 'Без названия')}")
        print(f"  Теги: {len(metadata.get('tags', []))}, Главы: {len(metadata.get('chapters', []))}\n")

        # Подготовка путей
        thumbnail_path = package_path / "thumbnail.png"
        transcript_path = package_path / "transcript.txt"
        
        # Проверка наличия транскрипции
        try:
            validate_file_path(transcript_path, must_exist=True)
        except ValueError as e:
            logger.error(f"Транскрипция не найдена: {e}")
            print(f"⚠ Ошибка: Файл транскрипции не найден в пакете")
            sys.exit(1)
        
        # Загрузка транскрипции
        print("[2/3] Загрузка транскрипции...")
        logger.info("Загрузка транскрипции")
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        
        if not transcript.strip():
            raise SSVVideoError("Файл транскрипции пуст")
            
        logger.info(f"Транскрипция загружена", extra={'length': len(transcript)})
        print(f"✓ Транскрипция загружена ({len(transcript)} символов)\n")

        # Генерация видео
        print("[3/3] Генерация видео...")
        logger.info("Запуск генерации видео")
        
        if args.dry_run:
            logger.info("Генерация видео пропущена (dry-run режим)")
            print("⚠ Генерация видео пропущена (dry-run режим)\n")
            output_path = None
        else:
            def generate_video():
                generator = TextOnScreenGenerator(config)
                
                # Создание выходной директории
                output_dir = Path(config['paths']['output_folder'])
                validate_directory(output_dir, create=True)
                
                output_path = output_dir / args.output_filename
                
                return generator.generate(
                    transcript=transcript,
                    thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
                    output_path=str(output_path)
                )
            
            output_path = safe_execute(
                generate_video,
                default_value=None,
                log_errors=False
            )
            
            if not output_path:
                raise SSVVideoError("Не удалось сгенерировать видео")
            
            logger.info(f"Видео создано успешно", extra={'path': output_path})
            print(f"✓ Видео создано: {output_path}\n")

        # Завершение
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Генерация видео завершена успешно", extra={
            'elapsed_seconds': elapsed_time,
            'output_path': output_path
        })
        
        print(f"{'='*60}")
        print("=== Генерация видео завершена успешно ===")
        print(f"{'='*60}")
        print(f"Время выполнения: {elapsed_time:.2f} сек")
        if output_path:
            print(f"Видео сохранено: {output_path}")
        print(f"{'='*60}\n")
        
        return output_path

    except SSVVideoError as e:
        logger.error(f"Ошибка генерации видео: {e}", exc_info=True)
        print(f"\n!!! Ошибка генерации видео: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем")
        print("\n⚠ Процесс прерван пользователем")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n!!! Критическая ошибка: {e}")
        print("Подробности в логах: logs/ssv_video_creator.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
