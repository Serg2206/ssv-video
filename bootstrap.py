#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py — автономный установщик SSVproff Video Creator для Windows.

Что делает скрипт:
  1. Проверяет версию Python (требуется 3.8+).
  2. Создаёт изолированное виртуальное окружение (venv) в папке `.ssv_venv`.
  3. Устанавливает зависимости: moviepy, pillow, gTTS, imageio-ffmpeg, numpy.
     (imageio-ffmpeg ставит ffmpeg автоматически — отдельная установка не нужна.)
  4. Перезапускает сам себя внутри venv и генерирует ТЕСТОВОЕ видео.

Ключевая особенность:
  Весь текст на кадрах рисуется через Pillow (PIL), а НЕ через moviepy.TextClip.
  Это полностью обходит необходимость в ImageMagick — частая проблема Windows.

Запуск (в обычном Python с системы):
    python bootstrap.py

После успешного завершения тестовое видео появится в:
    output\ssvproff_bootstrap_test.mp4

Автор: команда SSVproff. Стандарт сценария — WSES (тактика -> диагноз).
"""

import os
import sys
import subprocess
import platform

# ----------------------------------------------------------------------------
# Константы окружения
# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(HERE, ".ssv_venv")
OUTPUT_DIR = os.path.join(HERE, "output")
MARKER_ENV = "SSV_BOOTSTRAP_IN_VENV"  # флаг, что мы уже внутри venv

# Зависимости, которые нужны для генерации видео без ImageMagick.
REQUIREMENTS = [
    "pip",                 # сначала обновим сам pip
    "wheel",
    "setuptools",
    "numpy",
    "pillow",
    "imageio-ffmpeg",      # тащит ffmpeg, не требует системной установки
    "moviepy==1.0.3",
    "gTTS",                # офлайн? нет — gTTS требует интернет для синтеза
]

MIN_PYTHON = (3, 8)


# ----------------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------------
def log(msg):
    print(f"[bootstrap] {msg}", flush=True)


def fail(msg, code=1):
    print(f"\n[ОШИБКА] {msg}\n", file=sys.stderr, flush=True)
    sys.exit(code)


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Требуется Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, "
            f"а у вас {platform.python_version()}.\n"
            "Скачайте свежий Python с https://www.python.org/downloads/ "
            "и при установке отметьте 'Add Python to PATH'."
        )
    log(f"Python {platform.python_version()} — OK ({platform.system()}).")


def venv_python_path():
    """Путь к python.exe внутри venv (Windows) или к bin/python (Unix)."""
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def create_venv():
    py = venv_python_path()
    if os.path.exists(py):
        log("Виртуальное окружение уже существует — пропускаю создание.")
        return
    log("Создаю виртуальное окружение (.ssv_venv)...")
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    except subprocess.CalledProcessError as e:
        fail(f"Не удалось создать venv: {e}")
    if not os.path.exists(py):
        fail("venv создан, но интерпретатор не найден. Проверьте установку Python.")
    log("Виртуальное окружение готово.")


def install_requirements():
    py = venv_python_path()
    log("Устанавливаю зависимости (это может занять несколько минут)...")
    # Обновим pip отдельно, чтобы избежать предупреждений на старых сборках.
    try:
        subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError:
        log("Не удалось обновить pip — продолжаю с текущей версией.")
    pkgs = [p for p in REQUIREMENTS if p not in ("pip",)]
    try:
        subprocess.run([py, "-m", "pip", "install", *pkgs], check=True)
    except subprocess.CalledProcessError as e:
        fail(
            f"Не удалось установить зависимости: {e}\n"
            "Проверьте подключение к интернету и повторите запуск."
        )
    log("Все зависимости установлены.")


def relaunch_in_venv():
    """Перезапускает текущий скрипт интерпретатором из venv."""
    py = venv_python_path()
    env = dict(os.environ)
    env[MARKER_ENV] = "1"
    log("Перезапуск внутри виртуального окружения для генерации видео...")
    result = subprocess.run([py, os.path.abspath(__file__)], env=env)
    sys.exit(result.returncode)


# ----------------------------------------------------------------------------
# Генерация тестового видео (выполняется ВНУТРИ venv)
# ----------------------------------------------------------------------------
def wrap_text(draw, text, font, max_width):
    """Перенос текста по словам под заданную ширину (в пикселях)."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = (current + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def find_font(size, bold=True):
    """Ищет подходящий TrueType-шрифт (Windows / Linux), иначе дефолтный."""
    from PIL import ImageFont
    candidates = []
    if os.name == "nt":
        win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        if bold:
            candidates += [
                os.path.join(win_fonts, "arialbd.ttf"),
                os.path.join(win_fonts, "segoeuib.ttf"),
                os.path.join(win_fonts, "calibrib.ttf"),
            ]
        candidates += [
            os.path.join(win_fonts, "arial.ttf"),
            os.path.join(win_fonts, "segoeui.ttf"),
        ]
    # Linux / прочее
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_slide(text, width, height, accent=False):
    """Рисует один кадр (слайд) через Pillow и возвращает numpy-массив RGB."""
    import numpy as np
    from PIL import Image, ImageDraw

    bg = (16, 20, 26)
    accent_color = (226, 55, 68)
    white = (255, 255, 255)
    grey = (154, 164, 174)

    img = Image.new("RGB", (width, height), bg)
    d = ImageDraw.Draw(img)

    f_brand = find_font(int(height * 0.028), bold=True)
    f_main = find_font(int(height * 0.034), bold=True)
    f_foot = find_font(int(height * 0.018), bold=False)

    # Верхняя фирменная полоса SSVproff (в безопасной зоне)
    d.text((int(width * 0.06), int(height * 0.05)), "SSVproff",
           font=f_brand, fill=accent_color)
    d.rectangle([0, int(height * 0.10), width, int(height * 0.105)],
                fill=accent_color)

    # Основной текст по центру, с переносом
    is_redflag = text.strip().upper().startswith("КРАСНЫЙ ФЛАГ")
    main_color = accent_color if (is_redflag or accent) else white
    max_w = int(width * 0.84)
    lines = wrap_text(d, text, f_main, max_w)
    line_h = (d.textbbox((0, 0), "Ag", font=f_main)[3]) + int(height * 0.012)
    total_h = line_h * len(lines)
    y = (height - total_h) // 2
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=f_main)
        lw = bbox[2] - bbox[0]
        # лёгкая обводка для контраста
        x = (width - lw) // 2
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            d.text((x + dx, y + dy), line, font=f_main, fill=(0, 0, 0))
        d.text((x, y), line, font=f_main, fill=main_color)
        y += line_h

    # Нижняя плашка
    footer = "⚕ Образовательный материал · стандарт WSES"
    fb = d.textbbox((0, 0), footer, font=f_foot)
    d.text(((width - (fb[2] - fb[0])) // 2, int(height * 0.92)),
           footer, font=f_foot, fill=grey)

    return np.array(img)


def generate_test_video():
    """Собирает короткое тестовое видео из кадров Pillow + (опц.) озвучка gTTS."""
    log("Импортирую библиотеки для генерации видео...")
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips
    except Exception as e:
        fail(f"Не удалось импортировать moviepy: {e}")

    width, height = 1080, 1920          # вертикальный формат Shorts (9:16)
    fps = 30
    per_slide = 4                       # секунд на слайд

    slides = [
        "SSVproff: тестовый ролик установлен успешно ✅",
        "Острая боль в животе: сначала угроза жизни, потом диагноз (WSES).",
        "КРАСНЫЙ ФЛАГ: кинжальная боль и доскообразный живот — перитонит.",
        "Окружение готово. Запускайте полную генерацию из README.",
    ]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log("Рисую кадры через Pillow (без ImageMagick)...")
    clips = []
    for i, text in enumerate(slides):
        frame = render_slide(text, width, height, accent=(i == 0))
        clip = ImageClip(frame).set_duration(per_slide)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # Опциональная озвучка через gTTS (нужен интернет).
    audio_path = None
    try:
        from gtts import gTTS
        log("Генерирую озвучку (gTTS, нужен интернет)...")
        narration = " ".join(slides)
        audio_path = os.path.join(OUTPUT_DIR, "_bootstrap_narration.mp3")
        gTTS(text=narration, lang="ru").save(audio_path)
        from moviepy.editor import AudioFileClip
        audio = AudioFileClip(audio_path)
        # Подгоняем длительность видео под озвучку, если та длиннее.
        if audio.duration > video.duration:
            last = clips[-1].set_duration(
                clips[-1].duration + (audio.duration - video.duration))
            clips[-1] = last
            video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(audio.set_duration(min(audio.duration, video.duration)))
    except Exception as e:
        log(f"Озвучка пропущена (это не критично): {e}")

    out_path = os.path.join(OUTPUT_DIR, "ssvproff_bootstrap_test.mp4")
    log("Кодирую видео (libx264)...")
    video.write_videofile(
        out_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac" if audio_path else None,
        verbose=False,
        logger=None,
    )

    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except OSError:
            pass

    log("==================================================")
    log("ГОТОВО! Тестовое видео создано:")
    log(f"  {out_path}")
    log("Если файл открывается и воспроизводится — установка прошла успешно.")
    log("==================================================")


# ----------------------------------------------------------------------------
# Точка входа
# ----------------------------------------------------------------------------
def main():
    # Если мы уже внутри venv — просто генерируем видео.
    if os.environ.get(MARKER_ENV) == "1":
        generate_test_video()
        return

    print("=" * 60)
    print("  SSVproff Video Creator — Windows Bootstrap")
    print("=" * 60)

    check_python_version()
    create_venv()
    install_requirements()
    relaunch_in_venv()


if __name__ == "__main__":
    main()
