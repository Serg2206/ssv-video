
"""
tts_engine.py - Бесплатная нейросетевая озвучка через Microsoft Edge TTS (edge-tts)

Не требует API-ключа и подписки. Голоса - те же нейросети, что использует
Microsoft Edge для чтения страниц вслух; для русского языка доступны
качественные голоса ru-RU-DmitryNeural (муж.) и ru-RU-SvetlanaNeural (жен.).
"""
import asyncio
from typing import Dict, List

import edge_tts


class EdgeTTSNarrator:
    """Генерирует закадровую озвучку и возвращает метки слов, синхронные с аудио."""

    def __init__(self, config: Dict):
        narration_cfg = config.get('narration', {})
        self.voice = narration_cfg.get('voice', 'ru-RU-DmitryNeural')
        self.rate = narration_cfg.get('rate', '+0%')
        self.volume = narration_cfg.get('volume', '+0%')

    def generate(self, text: str, output_path: str) -> List[Dict]:
        """
        Синтезирует речь и сохраняет её в output_path (mp3).

        Возвращает список меток слов вида
        {'text': str, 'start': float, 'end': float} (секунды от начала файла) -
        это позволяет строить субтитры, идеально совпадающие с озвучкой,
        без отдельного (платного или тяжёлого) шага распознавания речи.
        """
        return asyncio.run(self._generate_async(text, output_path))

    async def _generate_async(self, text: str, output_path: str) -> List[Dict]:
        communicate = edge_tts.Communicate(
            text, self.voice, rate=self.rate, volume=self.volume
        )
        word_marks: List[Dict] = []

        with open(output_path, 'wb') as audio_file:
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_file.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    word_marks.append({
                        'text': chunk['text'],
                        'start': chunk['offset'] / 1e7,
                        'end': (chunk['offset'] + chunk['duration']) / 1e7,
                    })

        return word_marks
