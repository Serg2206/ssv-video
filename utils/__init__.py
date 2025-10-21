
"""
Вспомогательные утилиты для ssv-video
"""
import os


def load_transcript_from_file(filepath):
    """Загрузка транскрипции из файла"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Файл транскрипции не найден: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        raise ValueError("Файл транскрипции пуст")
    
    return content


def ensure_folder_exists(folder_path):
    """Создание папки, если она не существует"""
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
