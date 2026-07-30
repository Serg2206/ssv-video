
#!/usr/bin/env python3
"""
video_creator_main.py - Скрипт для генерации видео из пакета ssv-video
"""
import os
import sys
import argparse
import yaml
import json


def load_config(config_path="video_config.yaml"):
    """Загрузка конфигурации для генерации видео"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл конфигурации '{config_path}' не найден.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Ошибка при парсинге YAML: {e}")
        sys.exit(1)


def load_package_metadata(package_path):
    """Загрузка метаданных из пакета ssv-video"""
    metadata_path = os.path.join(package_path, "metadata.json")
    if not os.path.exists(metadata_path):
        print(f"Ошибка: Файл метаданных не найден в {package_path}")
        sys.exit(1)
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="SSV Video Creator - Генерация видео из пакета")
    parser.add_argument("--package_path", required=True, help="Путь к папке пакета ssv-video")
    parser.add_argument("--output_filename", default="final_video.mp4", help="Имя выходного видеофайла")
    parser.add_argument("--config", default="video_config.yaml", help="Путь к файлу конфигурации")
    args = parser.parse_args()

    # Загрузка конфигурации
    config = load_config(args.config)
    
    # Проверка пакета
    if not os.path.exists(args.package_path):
        print(f"Ошибка: Папка пакета '{args.package_path}' не найдена.")
        sys.exit(1)

    print(f"=== SSV Video Creator v{config['project']['version']} ===")
    print(f"Обработка пакета: {args.package_path}")

    try:
        # Загрузка метаданных пакета
        print("\n[1/3] Загрузка метаданных пакета...")
        metadata = load_package_metadata(args.package_path)
        print(f"Метаданные загружены: {metadata.get('title', 'Без названия')}")

        # Генерация видео
        print("\n[2/3] Генерация видео...")
        method = config['video_generation'].get('method', 'narrated')
        if method == 'text_on_screen':
            from video_modules.text_on_screen_generator import TextOnScreenGenerator
            generator = TextOnScreenGenerator(config)
        else:
            from video_modules.narrated_video_generator import NarratedVideoGenerator
            generator = NarratedVideoGenerator(config)

        # Путь к превью и транскрипции
        thumbnail_path = os.path.join(args.package_path, "thumbnail.png")
        transcript_path = os.path.join(args.package_path, "transcript.txt")
        
        # Загрузка транскрипции
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        
        # Генерация видео
        output_path = os.path.join(config['paths']['output_folder'], args.output_filename)
        os.makedirs(config['paths']['output_folder'], exist_ok=True)
        
        generator.generate(
            transcript=transcript,
            thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
            output_path=output_path
        )
        
        print(f"\n[3/3] Видео создано: {output_path}")
        print("\n=== Генерация видео завершена успешно ===")

    except Exception as e:
        print(f"\n!!! Ошибка при генерации видео: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
