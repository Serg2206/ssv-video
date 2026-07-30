
"""
narrated_video_generator.py - Современный бесплатный пайплайн генерации видео

Заменяет "текст на однотонном фоне" на полноценное озвученное видео:
  - озвучка транскрипции (edge-tts, бесплатно, без ключа)
  - ИИ-иллюстрации по смыслу сегмента (Pollinations.ai, бесплатно, без ключа)
  - субтитры, синхронные с озвучкой (по меткам слов от edge-tts)
  - опциональная фоновая музыка (собственный CC0-трек, без внешнего API)

Использует moviepy 2.x API (moviepy>=2.0).
"""
import os
import re
import shutil

from moviepy import (
    AudioFileClip, ImageClip, TextClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips, concatenate_audioclips
)

from video_modules.tts_engine import EdgeTTSNarrator
from video_modules.illustration_generator import IllustrationGenerator
from video_modules.subtitle_builder import group_words_into_subtitles


class NarratedVideoGenerator:
    """Генерирует озвученное видео с ИИ-иллюстрациями и субтитрами - полностью бесплатно."""

    def __init__(self, config):
        self.config = config
        self.video_cfg = config['video_generation']
        self.width = self.video_cfg['resolution']['width']
        self.height = self.video_cfg['resolution']['height']
        self.fps = self.video_cfg.get('fps', 30)

        self.narrator = EdgeTTSNarrator(config)
        self.illustrator = IllustrationGenerator(config)
        self.subtitles_cfg = config.get('subtitles', {})
        self.music_cfg = config.get('music', {})

        subtitle_font = self.subtitles_cfg.get('font')
        self.subtitle_font = subtitle_font if subtitle_font and os.path.exists(subtitle_font) else None

        self.tmp_dir = os.path.join(config['paths']['output_folder'], '_tmp_narrated')
        os.makedirs(self.tmp_dir, exist_ok=True)

    def generate(self, transcript, thumbnail_path=None, output_path="output.mp4"):
        segments = self._split_into_segments(transcript)
        print(f"  - Сегментов для озвучки: {len(segments)}")

        segment_clips = []

        if thumbnail_path and os.path.exists(thumbnail_path):
            thumb_duration = self.video_cfg.get('thumbnail_duration', 3)
            segment_clips.append(
                ImageClip(thumbnail_path)
                .resized((self.width, self.height))
                .with_duration(thumb_duration)
            )

        for idx, segment_text in enumerate(segments):
            print(f"  - Сегмент {idx + 1}/{len(segments)}: озвучка...")
            audio_path = os.path.join(self.tmp_dir, f"segment_{idx}.mp3")
            word_marks = self.narrator.generate(segment_text, audio_path)
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration

            print(f"  - Сегмент {idx + 1}/{len(segments)}: ИИ-иллюстрация...")
            image_path = os.path.join(self.tmp_dir, f"segment_{idx}.jpg")
            self.illustrator.generate(segment_text[:200], self.width, self.height, image_path)

            visual = (
                ImageClip(image_path)
                .resized((self.width, self.height))
                .with_duration(duration)
                .with_audio(audio_clip)
            )

            if self.subtitles_cfg.get('enabled', True) and word_marks:
                subtitle_clips = self._build_subtitle_clips(word_marks, duration)
                if subtitle_clips:
                    visual = CompositeVideoClip([visual] + subtitle_clips)

            segment_clips.append(visual)

        print("  - Объединение сегментов...")
        final_video = concatenate_videoclips(segment_clips, method="compose")
        final_video = self._apply_music(final_video)

        print("  - Экспорт видео...")
        final_video.write_videofile(
            output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac'
        )

        self._cleanup()
        return output_path

    def _split_into_segments(self, text, max_chars=350):
        """Делит транскрипцию на смысловые фрагменты (абзацы, при необходимости - предложения)."""
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        if len(paragraphs) <= 1:
            paragraphs = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

        segments = []
        current = ""
        for part in paragraphs:
            if current and len(current) + len(part) + 1 > max_chars:
                segments.append(current.strip())
                current = part
            else:
                current = f"{current} {part}".strip()
        if current:
            segments.append(current.strip())
        return segments

    def _build_subtitle_clips(self, word_marks, segment_duration):
        subtitle_groups = group_words_into_subtitles(
            word_marks, self.subtitles_cfg.get('words_per_group', 4)
        )
        clips = []
        y_position = int(self.height * self.subtitles_cfg.get('position_y_ratio', 0.85))

        for text, start, end in subtitle_groups:
            end = min(end, segment_duration)
            if end <= start:
                continue
            txt_clip = TextClip(
                text=text,
                font=self.subtitle_font,
                font_size=self.subtitles_cfg.get('fontsize', 44),
                color=self.subtitles_cfg.get('color', 'white'),
                stroke_color=self.subtitles_cfg.get('stroke_color', 'black'),
                stroke_width=self.subtitles_cfg.get('stroke_width', 2),
                size=(int(self.width * 0.9), None),
                method='caption'
            ).with_start(start).with_end(end).with_position(('center', y_position))
            clips.append(txt_clip)

        return clips

    def _apply_music(self, video_clip):
        if not self.music_cfg.get('enabled', False):
            return video_clip

        track_path = self.music_cfg.get('track_path')
        if not track_path or not os.path.exists(track_path):
            print("  ! Фоновая музыка включена, но track_path не найден - пропускаю")
            return video_clip

        volume = self.music_cfg.get('volume', 0.12)
        music = AudioFileClip(track_path).with_volume_scaled(volume)

        if music.duration < video_clip.duration:
            loops = int(video_clip.duration // music.duration) + 1
            music = concatenate_audioclips([music] * loops)
        music = music.subclipped(0, video_clip.duration)

        mixed_audio = CompositeAudioClip([video_clip.audio, music])
        return video_clip.with_audio(mixed_audio)

    def _cleanup(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
