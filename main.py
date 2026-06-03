
#!/usr/bin/env python3
"""
main.py - Основной скрипт для генерации пакетов ssv-video v2.1
Оптимизированная версия с улучшенной обработкой ошибок и логированием
"""
import os
import sys
import argparse
import yaml
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any

# Импорт модулей с обработкой ошибок
try:
    from modules.ai_generator import AIGenerator
    from modules.thumbnail_generator import ThumbnailGenerator
    from modules.packager import Packager
    from modules.youtube_uploader import YouTubeUploader
    from utils import load_transcript_from_file, ensure_folder_exists
    from utils.logger import setup_logger, get_logger
    from utils.error_handler import safe_execute, SSVVideoError
    from utils.validator import validate_file_path, validate_directory
except ImportError as e:
    print(f"Критическая ошибка импорта: {e}")
    sys.exit(1)

# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logger = setup_logger(
    name='ssv_video_main',
    log_dir=Path('logs'),
    level=os.getenv('LOG_LEVEL', 'INFO'),
    console_output=True,
    json_output=True
)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Загрузка конфигурации из YAML файла с валидацией"""
    try:
        config_file = Path(config_path)
        validate_file_path(config_file, must_exist=True)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Валидация обязательных секций
        required_sections = ['project', 'paths', 'ai']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Отсутствует обязательная секция конфигурации: {section}")
        
        # Создание директорий если не существуют
        for path_key in ['input_folder', 'output_folder']:
            if path_key in config['paths']:
                validate_directory(Path(config['paths'][path_key]), create=True)
        
        logger.info(f"Конфигурация загружена: {config_path}", extra={'config': config_path})
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


def main():
    """Основная функция обработки видео пакета"""
    parser = argparse.ArgumentParser(
        description="SSV Video Package Generator v2.1 - Оптимизированная версия",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py --input_file transcript.txt
  python main.py --input_file input/video.txt --config custom_config.yaml
  python main.py --input_file video.txt --no-video-synthesis
        """
    )
    parser.add_argument(
        "--input_file", 
        required=True, 
        help="Путь к файлу транскрипции (.txt)"
    )
    parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)"
    )
    parser.add_argument(
        "--no-video-synthesis",
        action="store_true",
        help="Отключить генерацию видео даже если включена в конфиге"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Тестовый запуск без реальных API вызовов"
    )
    args = parser.parse_args()

    # Загрузка конфигурации
    config = load_config(args.config)
    
    # Проверка входного файла
    input_file = Path(args.input_file)
    try:
        validate_file_path(input_file, must_exist=True)
    except ValueError as e:
        logger.error(f"Ошибка валидации входного файла: {e}")
        print(f"Ошибка: Входной файл '{args.input_file}' не найден.")
        sys.exit(1)

    version = config['project'].get('version', '2.1')
    logger.info(f"Запуск SSV Video Package Generator v{version}", extra={
        'input_file': str(input_file),
        'config': args.config
    })
    
    print(f"\n{'='*60}")
    print(f"=== SSV Video Package Generator v{version} ===")
    print(f"{'='*60}")
    print(f"Обработка файла: {input_file.absolute()}")
    print(f"Конфигурация: {args.config}")
    if args.dry_run:
        print("РЕЖИМ: Тестовый запуск (dry-run)")
    print(f"{'='*60}\n")

    start_time = datetime.now()
    
    try:
        # 1. Загрузка транскрипции
        print("[1/5] Загрузка транскрипции...")
        logger.info("Загрузка транскрипции", extra={'file': str(input_file)})
        
        def load_transcript():
            return load_transcript_from_file(str(input_file))
        
        transcript = safe_execute(
            load_transcript,
            default_value=None,
            log_errors=False
        )
        
        if not transcript:
            raise SSVVideoError("Не удалось загрузить транскрипцию")
            
        logger.info(f"Транскрипция загружена успешно", extra={'length': len(transcript)})
        print(f"✓ Транскрипция загружена ({len(transcript)} символов)\n")

        # 2. Генерация контента с помощью ИИ
        print("[2/5] Генерация контента с помощью ИИ...")
        logger.info("Запуск AI генератора")
        
        def generate_ai_content():
            ai_gen = AIGenerator(config)
            return ai_gen.generate_all(transcript)
        
        ai_content = safe_execute(
            generate_ai_content,
            default_value=None,
            log_errors=False
        )
        
        if not ai_content:
            raise SSVVideoError("Не удалось сгенерировать AI контент")
            
        logger.info("AI контент сгенерирован успешно", extra={
            'title': ai_content.get('title', 'N/A')[:50],
            'tags_count': len(ai_content.get('tags', [])),
            'chapters_count': len(ai_content.get('chapters', []))
        })
        print("✓ Контент сгенерирован успешно")
        print(f"  Заголовок: {ai_content['title'][:70]}{'...' if len(ai_content['title']) > 70 else ''}")
        print(f"  Тегов: {len(ai_content['tags'])}, Глав: {len(ai_content['chapters'])}\n")

        # 3. Генерация превью
        print("[3/5] Генерация превью...")
        logger.info("Генерация превью")
        
        def generate_thumbnail():
            thumb_gen = ThumbnailGenerator(config)
            return thumb_gen.generate(ai_content['title'])
        
        thumbnail_path = safe_execute(
            generate_thumbnail,
            default_value=None,
            log_errors=False
        )
        
        if thumbnail_path:
            logger.info(f"Превью создано", extra={'path': thumbnail_path})
            print(f"✓ Превью сохранено: {thumbnail_path}\n")
        else:
            logger.warning("Не удалось создать превью")
            print("⚠ Превью не создано (продолжаем без него)\n")

        # 4. Подготовка пакета
        print("[4/5] Подготовка пакета...")
        logger.info("Создание пакета")
        
        def create_package():
            packager = Packager(config)
            return packager.create_package(
                input_filename=input_file.name,
                transcript=transcript,
                ai_content=ai_content,
                thumbnail_path=thumbnail_path
            )
        
        package_folder = safe_execute(
            create_package,
            default_value=None,
            log_errors=False
        )
        
        if not package_folder:
            raise SSVVideoError("Не удалось создать пакет")
            
        logger.info(f"Пакет создан", extra={'path': package_folder})
        print(f"✓ Пакет создан: {package_folder}\n")

        # 5. Публикация на YouTube (опционально)
        youtube_enabled = config.get('youtube', {}).get('enabled', False)
        if youtube_enabled and not args.dry_run:
            print("[5/5] Публикация на YouTube...")
            logger.info("Загрузка на YouTube")
            
            def upload_to_youtube():
                uploader = YouTubeUploader(config)
                return uploader.upload(package_folder)
            
            video_id = safe_execute(
                upload_to_youtube,
                default_value=None,
                log_errors=False
            )
            
            if video_id:
                logger.info(f"Видео опубликовано на YouTube", extra={'video_id': video_id})
                print(f"✓ Видео опубликовано: https://youtube.com/watch?v={video_id}\n")
            else:
                logger.warning("Не удалось опубликовать на YouTube")
                print("⚠ Публикация на YouTube не удалась\n")
        else:
            if youtube_enabled and args.dry_run:
                print("[5/5] Публикация на YouTube пропущена (dry-run режим)\n")
            else:
                print("[5/5] Публикация на YouTube отключена в конфигурации\n")
            logger.info("Публикация на YouTube отключена")

        # Опциональная генерация видео
        video_synthesis_enabled = config.get('video_synthesis', {}).get('enabled', False)
        if video_synthesis_enabled and not args.no_video_synthesis and not args.dry_run:
            print("[Дополнительно] Запуск генерации видео...")
            logger.info("Запуск синтеза видео")
            
            try:
                import subprocess
                video_output = config['video_synthesis'].get(
                    'output_filename_template', 
                    'final_{timestamp}_{input_name}.mp4'
                )
                video_output = video_output.format(
                    timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                    input_name=input_file.stem
                )
                
                result = subprocess.run([
                    sys.executable, 
                    "video_creator_main.py",
                    "--package_path", package_folder,
                    "--output_filename", video_output
                ], check=True, capture_output=True, text=True, timeout=600)
                
                logger.info(f"Видео создано успешно", extra={'output': video_output})
                print(f"✓ Видео создано: {video_output}\n")
                
            except subprocess.TimeoutExpired:
                logger.error("Таймаут при генерации видео (лимит 10 минут)")
                print("⚠ Ошибка: Таймаут при генерации видео (лимит 10 минут)\n")
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка генерации видео: {e.stderr}")
                print(f"⚠ Ошибка при генерации видео: {e.stderr}\n")
            except Exception as e:
                logger.error(f"Ошибка при генерации видео: {e}", exc_info=True)
                print(f"⚠ Ошибка при генерации видео: {e}\n")
        elif video_synthesis_enabled and (args.no_video_synthesis or args.dry_run):
            logger.info("Генерация видео пропущена по флагу пользователя")
            print("[Дополнительно] Генерация видео пропущена\n")

        # Завершение
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Обработка завершена успешно", extra={
            'elapsed_seconds': elapsed_time,
            'package_folder': package_folder
        })
        
        print(f"{'='*60}")
        print("=== Обработка завершена успешно ===")
        print(f"{'='*60}")
        print(f"Время выполнения: {elapsed_time:.2f} сек")
        print(f"Пакет сохранен: {package_folder}")
        print(f"{'='*60}\n")
        
        return package_folder

    except SSVVideoError as e:
        logger.error(f"Ошибка обработки: {e}", exc_info=True)
        print(f"\n!!! Ошибка обработки: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Процесс прерван пользователем")
        print("\n⚠ Процесс прерван пользователем")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n!!! Критическая ошибка: {e}")
        print("Подробности в логах: logs/ssv_video_main.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
