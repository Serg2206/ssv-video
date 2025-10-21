
"""
text_on_screen_generator.py - Генерация видео с текстом на экране
"""
import os
from moviepy.editor import (
    VideoClip, ImageClip, TextClip, CompositeVideoClip,
    concatenate_videoclips
)


class TextOnScreenGenerator:
    def __init__(self, config):
        self.config = config
        self.video_config = config['video_generation']

    def generate(self, transcript, thumbnail_path=None, output_path="output.mp4"):
        """Генерация видео с текстом на экране"""
        print("  - Подготовка текстовых фрагментов...")
        text_chunks = self._split_text(transcript)
        
        print("  - Создание видеоклипов...")
        clips = []
        
        # Добавление превью в начало (если есть)
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumb_duration = self.video_config.get('thumbnail_duration', 3)
            thumb_clip = ImageClip(thumbnail_path).set_duration(thumb_duration)
            clips.append(thumb_clip)
        
        # Создание клипов с текстом
        for chunk in text_chunks:
            clip = self._create_text_clip(chunk)
            clips.append(clip)
        
        print("  - Объединение клипов...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        print("  - Экспорт видео...")
        final_video.write_videofile(
            output_path,
            fps=self.video_config['fps'],
            codec='libx264',
            audio_codec='aac'
        )
        
        return output_path

    def _split_text(self, text, max_chars=200):
        """Разбиение текста на фрагменты"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_chars:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def _create_text_clip(self, text):
        """Создание клипа с текстом"""
        duration = self.video_config['duration_per_text_chunk']
        width = self.video_config['resolution']['width']
        height = self.video_config['resolution']['height']
        
        # Создание фона
        bg_color = tuple(self.video_config['background']['color'])
        background = VideoClip(
            make_frame=lambda t: [bg_color] * height * width,
            duration=duration
        ).set_fps(self.video_config['fps'])
        
        # Создание текста
        text_config = self.video_config['text']
        txt_clip = TextClip(
            text,
            fontsize=text_config['fontsize'],
            color=text_config['color'],
            font=text_config['font'],
            size=(width * 0.8, None),
            method='caption'
        ).set_duration(duration).set_position('center')
        
        return CompositeVideoClip([background, txt_clip])
