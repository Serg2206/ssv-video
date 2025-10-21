
"""
packager.py - Подготовка пакета для публикации
"""
import os
import json
import shutil
from datetime import datetime


class Packager:
    def __init__(self, config):
        self.config = config
        self.output_folder = config['paths']['output_folder']

    def create_package(self, input_filename, transcript, ai_content, thumbnail_path):
        """Создание пакета с результатами"""
        # Создание уникальной папки для пакета
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        package_name = f"{timestamp}_{os.path.splitext(input_filename)[0]}"
        package_folder = os.path.join(self.output_folder, package_name)
        os.makedirs(package_folder, exist_ok=True)

        # Сохранение файлов
        self._save_transcript(package_folder, transcript)
        self._save_metadata(package_folder, ai_content)
        self._save_thumbnail(package_folder, thumbnail_path)
        
        if self.config['open_science']['generate_readme']:
            self._save_readme(package_folder, ai_content)
        
        if self.config['open_science']['export_artifacts']:
            self._export_artifacts(package_folder, ai_content)

        return package_folder

    def _save_transcript(self, folder, transcript):
        """Сохранение транскрипции"""
        with open(os.path.join(folder, "transcript.txt"), 'w', encoding='utf-8') as f:
            f.write(transcript)

    def _save_metadata(self, folder, ai_content):
        """Сохранение метаданных"""
        metadata = {
            'title': ai_content['title'],
            'description': ai_content['description'],
            'tags': ai_content['tags'],
            'chapters': ai_content['chapters'],
            'generated_at': datetime.now().isoformat()
        }
        with open(os.path.join(folder, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _save_thumbnail(self, folder, thumbnail_path):
        """Копирование превью"""
        if thumbnail_path and os.path.exists(thumbnail_path):
            shutil.copy(thumbnail_path, os.path.join(folder, "thumbnail.png"))

    def _save_readme(self, folder, ai_content):
        """Создание README.md"""
        readme_content = f"""# {ai_content['title']}

## Описание
{ai_content['description']}

## Теги
{', '.join(ai_content['tags'])}

## Главы
{''.join([f'- {chapter}' + chr(10) for chapter in ai_content['chapters']])}

---
Сгенерировано с помощью ssv-video v2.0
"""
        with open(os.path.join(folder, "README.md"), 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def _export_artifacts(self, folder, ai_content):
        """Экспорт артефактов для open-science"""
        artifacts_folder = os.path.join(folder, "artifacts")
        os.makedirs(artifacts_folder, exist_ok=True)
        
        # Экспорт в JSON
        with open(os.path.join(artifacts_folder, "ai_content.json"), 'w', encoding='utf-8') as f:
            json.dump(ai_content, f, ensure_ascii=False, indent=2)
        
        # Экспорт в Markdown
        with open(os.path.join(artifacts_folder, "ai_content.md"), 'w', encoding='utf-8') as f:
            f.write(f"# {ai_content['title']}\n\n")
            f.write(f"## Описание\n{ai_content['description']}\n\n")
            f.write(f"## Теги\n{', '.join(ai_content['tags'])}\n\n")
            f.write(f"## Главы\n")
            for chapter in ai_content['chapters']:
                f.write(f"- {chapter}\n")
