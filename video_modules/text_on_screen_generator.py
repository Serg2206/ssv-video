
"""
text_on_screen_generator.py - Генерация видео с текстом на экране
Версия 2.0: с поддержкой TTS-озвучки и аудио
"""
import os
from moviepy.editor import (
    VideoClip, ImageClip, TextClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip
)


class TextOnScreenGenerator:
    def __init__(self, config):
        self.config = config
        self.video_config = config['video_generation']
        self.tts_config = config.get('tts', {})

    def generate(self, transcript, thumbnail_path=None, audio_path=None, output_path="output.mp4"):
        """Генерация видео с текстом на экране"""
        print("  - Подготовка текстовых фрагментов...")
        text_chunks = self._split_text(transcript)
        
        # Генерация аудио из текста, если не предоставлено
        if not audio_path and self.tts_config.get('engine'):
            from modules.tts_generator import TTSGenerator
            tts = TTSGenerator(self.config)
            audio_path = tts.generate(transcript, "audio_tts.mp3")
        
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
        
        # Добавление аудио (если есть)
        if audio_path and os.path.exists(audio_path):
            print("  - Добавление аудио дорожки...")
            try:
                audio = AudioFileClip(audio_path)
                final_video = final_video.set_audio(audio)
                
                # Корректировка длительности видео под аудио
                if audio.duration > final_video.duration:
                    print(f"  - Увеличение длительности видео до {audio.duration:.1f}с...")
                    # Добавление черного экрана в конец, если аудио длиннее
                    extra_duration = audio.duration - final_video.duration
                    if extra_duration > 0:
                        black_screen = VideoClip(
                            make_frame=lambda t: [[20, 25, 30]] * int(self.video_config['resolution']['height']) * int(self.video_config['resolution']['width']),
                            duration=extra_duration
                        ).set_fps(self.video_config['fps'])
                        final_video = concatenate_videoclips([final_video, black_screen], method="compose")
                
                final_video = final_video.set_duration(audio.duration)
            except Exception as e:
                print(f"  ! Ошибка добавления аудио: {e}. Видео будет без звука.")
        
        print("  - Экспорт видео...")
        final_video.write_videofile(
            output_path,
            fps=self.video_config['fps'],
            codec='libx264',
            audio_codec='aac' if audio_path else None
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
            make_frame=lambda t: [[bg_color] * width for _ in range(height)],
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
