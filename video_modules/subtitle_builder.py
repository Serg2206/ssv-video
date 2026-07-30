
"""
subtitle_builder.py - Сборка субтитров по меткам слов озвучки

Metки слов приходят напрямую от edge-tts (see tts_engine.py), поэтому
субтитры получаются идеально синхронными с озвучкой без отдельного
шага распознавания речи (whisper и т.п.).
"""
from typing import Dict, List, Tuple


def group_words_into_subtitles(
    word_marks: List[Dict], words_per_group: int = 4
) -> List[Tuple[str, float, float]]:
    """Группирует метки слов в короткие субтитровые фразы с точным таймингом.

    Возвращает список (текст, начало_сек, конец_сек).
    """
    subtitles = []
    for i in range(0, len(word_marks), words_per_group):
        group = word_marks[i:i + words_per_group]
        if not group:
            continue
        text = ' '.join(w['text'] for w in group)
        start = group[0]['start']
        end = group[-1]['end']
        subtitles.append((text, start, end))
    return subtitles
