
"""
tts_generator.py - Генерация озвучки (Text-to-Speech)
Поддерживает: gTTS (Google TTS, онлайн) и pyttsx3 (офлайн)
"""
import os
from gtts import gTTS
import pyttsx3


class TTSGenerator:
    def __init__(self, config):
        self.config = config
        self.tts_engine = config.get('tts', {}).get('engine', 'gtts')  # 'gtts' или 'pyttsx3'
        self.language = config.get('tts', {}).get('language', 'ru')
        self.output_folder = config['paths']['output_folder']
        
        # Инициализация офлайн-движка (если выбран)
        self.engine = None
        if self.tts_engine == 'pyttsx3':
            self.engine = pyttsx3.init()
            self._configure_pyttsx3()

    def _configure_pyttsx3(self):
        """Настройка параметров pyttsx3"""
        voices = self.engine.getProperty('voices')
        # Попытка найти русский голос
        ru_voice = None
        for voice in voices:
            if 'ru' in voice.languages or 'Russian' in voice.name:
                ru_voice = voice.id
                break
        
        if ru_voice:
            self.engine.setProperty('voice', ru_voice)
        
        self.engine.setProperty('rate', 150)  # Скорость речи
        self.engine.setProperty('volume', 0.9)  # Громкость

    def generate(self, text, output_filename="audio.mp3"):
        """Генерация аудио из текста"""
        os.makedirs(self.output_folder, exist_ok=True)
        output_path = os.path.join(self.output_folder, output_filename)
        
        print(f"  - Генерация озвучки (движок: {self.tts_engine})...")
        
        if self.tts_engine == 'gtts':
            return self._generate_gtts(text, output_path)
        elif self.tts_engine == 'pyttsx3':
            return self._generate_pyttsx3(text, output_path)
        else:
            raise ValueError(f"Неподдерживаемый TTS-движок: {self.tts_engine}")

    def _generate_gtts(self, text, output_path):
        """Генерация через Google TTS (онлайн, высокое качество)"""
        try:
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(output_path)
            print(f"  ✓ Озвучка сохранена: {output_path}")
            return output_path
        except Exception as e:
            print(f"  ! Ошибка gTTS: {e}. Попробуйте pyttsx3 для офлайн-режима.")
            raise

    def _generate_pyttsx3(self, text, output_path):
        """Генерация через pyttsx3 (офлайн, быстрее, но менее естественно)"""
        try:
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            print(f"  ✓ Озвучка сохранена: {output_path}")
            return output_path
        except Exception as e:
            print(f"  ! Ошибка pyttsx3: {e}")
            raise

    def generate_from_transcript(self, transcript_path, output_filename="audio.mp3"):
        """Генерация озвучки из файла транскрипции"""
        with open(transcript_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.generate(text, output_filename)
