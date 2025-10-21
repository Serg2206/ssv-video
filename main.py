
#!/usr/bin/env python3
"""
main.py - Основной скрипт для генерации пакетов ssv-video v2.0
"""
import os
import sys
import argparse
import yaml
from dotenv import load_dotenv
from datetime import datetime

from modules.ai_generator import AIGenerator
from modules.thumbnail_generator import ThumbnailGenerator
from modules.packager import Packager
from modules.youtube_uploader import YouTubeUploader
from utils import load_transcript_from_file

load_dotenv()


def load_config(config_path="config.yaml"):
    """Загрузка конфигурации из YAML файла"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл конфигурации '{config_path}' не найден.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Ошибка при парсинге YAML: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SSV Video Package Generator v2.0")
    parser.add_argument("--input_file", required=True, help="Путь к файлу транскрипции")
    parser.add_argument("--config", default="config.yaml", help="Путь к файлу конфигурации")
    args = parser.parse_args()

    # Загрузка конфигурации
    config = load_config(args.config)
    
    # Проверка входного файла
    if not os.path.exists(args.input_file):
        print(f"Ошибка: Входной файл '{args.input_file}' не найден.")
        sys.exit(1)

    print(f"=== SSV Video Package Generator v{config['project']['version']} ===")
    print(f"Обработка файла: {args.input_file}")

    try:
        # 1. Загрузка транскрипции
        print("\n[1/5] Загрузка транскрипции...")
        transcript = load_transcript_from_file(args.input_file)
        print(f"Транскрипция загружена ({len(transcript)} символов)")

        # 2. Генерация контента с помощью ИИ
        print("\n[2/5] Генерация контента с помощью ИИ...")
        ai_gen = AIGenerator(config)
        ai_content = ai_gen.generate_all(transcript)
        print("Контент сгенерирован успешно")

        # 3. Генерация превью
        print("\n[3/5] Генерация превью...")
        thumb_gen = ThumbnailGenerator(config)
        thumbnail_path = thumb_gen.generate(ai_content['title'])
        print(f"Превью сохранено: {thumbnail_path}")

        # 4. Подготовка пакета
        print("\n[4/5] Подготовка пакета...")
        packager = Packager(config)
        package_folder = packager.create_package(
            input_filename=os.path.basename(args.input_file),
            transcript=transcript,
            ai_content=ai_content,
            thumbnail_path=thumbnail_path
        )
        print(f"Пакет создан: {package_folder}")

        # 5. Публикация на YouTube (опционально)
        if config.get('youtube', {}).get('enabled', False):
            print("\n[5/5] Публикация на YouTube...")
            uploader = YouTubeUploader(config)
            video_id = uploader.upload(package_folder)
            print(f"Видео опубликовано: https://youtube.com/watch?v={video_id}")
        else:
            print("\n[5/5] Публикация на YouTube отключена")

        # Опциональная генерация видео
        if config.get('video_synthesis', {}).get('enabled', False):
            print("\n[Дополнительно] Запуск генерации видео...")
            try:
                import subprocess
                video_output = config['video_synthesis'].get('output_filename_template', 'final_video.mp4')
                video_output = video_output.format(
                    timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                    input_name=os.path.splitext(os.path.basename(args.input_file))[0]
                )
                subprocess.run([
                    sys.executable, "video_creator_main.py",
                    "--package_path", package_folder,
                    "--output_filename", video_output
                ], check=True)
                print(f"Видео создано: {video_output}")
            except Exception as e:
                print(f"Ошибка при генерации видео: {e}")

        print("\n=== Обработка завершена успешно ===")
        return package_folder

    except Exception as e:
        print(f"\n!!! Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
