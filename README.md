
# ssv-video v2.0

**Автоматизированный инструмент для создания готовых к публикации пакетов** для YouTube-канала **@SSVproff-22.06**.

Генерирует:
- **SEO-оптимизированные заголовок и описание** с помощью ИИ.
- **Превью в фирменном стиле SSVproff** (через API или локально).
- **Теги и главы (timestamps)**.
- **README.md** для синхронного GitHub-репозитория.
- **Поддержку open-science workflow** через экспорт артефактов (JSON, MD).
- *(Опционально)* **Автоматическую публикацию на YouTube** (требует настройки API).
- *(Опционально)* **Создание видеофайла** на основе пакета (экспериментальная функция `ssv-video-creator`).

Разработан профессором С.В. Сушковым для медицинского сообщества.

## Структура проекта

```
ssv-video/
├── main.py                 # Основной скрипт для генерации пакетов (v2.0)
├── video_creator_main.py   # Скрипт для генерации видео из пакета (ssv-video-creator)
├── requirements.txt        # Зависимости Python
├── config.yaml             # Конфигурация для генерации пакетов (v2.0)
├── video_config.yaml       # Конфигурация для генерации видео (ssv-video-creator)
├── .env.example            # Пример файла для переменных окружения (API-ключи)
├── README.md               # Этот файл
├── input/                  # Папка для входных файлов (транскрипции)
├── output/                 # Папка для результатов (пакеты, видео)
├── modules/                # Модули v2.0
│   ├── __init__.py
│   ├── ai_generator.py     # Генерация текста (Заголовок, Описание, Теги, Главы)
│   ├── thumbnail_generator.py # Генерация превью
│   ├── packager.py         # Подготовка пакета (README, архивация)
│   └── youtube_uploader.py # Публикация на YouTube
├── video_modules/          # Модули ssv-video-creator
│   ├── __init__.py
│   └── text_on_screen_generator.py # Генерация видео с текстом на экране
└── utils/                  # Вспомогательные утилиты
    └── __init__.py
```

## Установка

1.  Убедитесь, что у вас установлен **Python 3.10+** (https://python.org).
2.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/Serg2206/ssv-video.git
    cd ssv-video
    ```
3.  *(Рекомендуется)* Создайте виртуальное окружение:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # или
    venv\Scripts\activate     # Windows
    ```
4.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```
5.  Скопируйте `.env.example` в `.env` и укажите свои API-ключи:
    ```bash
    cp .env.example .env
    ```
    Отредактируйте `.env`, добавив свои ключи (например, `OPENAI_API_KEY`).
6.  Настройте `config.yaml` под свои нужды (язык, папки, ИИ-модель, стили, YouTube и т.д.).
7.  *(Опционально, для генерации видео)* Настройте `video_config.yaml` под свои нужды.

## Использование

### 1. Генерация пакета (v2.0)

1.  Поместите файл с транскрипцией (`.txt`) в папку `input/` (указанную в `config.yaml`).
2.  Убедитесь, что `config.yaml` настроен (включая `youtube.enabled: false`, если публикация не нужна).
3.  Запустите основной скрипт:
    ```bash
    python main.py --input_file "path/to/your/transcript.txt"
    ```
4.  Результаты (пакет) будут сохранены в папке `output/` в подпапке с уникальным именем.

### 2. Генерация видео из пакета (ssv-video-creator - экспериментально)

1.  Убедитесь, что `ssv-video` (v2.0) успешно сгенерировал пакет (например, `output/2024-.../`).
2.  Настройте `video_config.yaml` (метод генерации, разрешение, шрифты и т.д.).
3.  Запустите скрипт генерации видео:
    ```bash
    python video_creator_main.py --package_path "path/to/your/ssv_video_package_folder" --output_filename "my_final_video.mp4"
    ```
4.  Результат (видеофайл) будет сохранён в папке `output/`.

### 3. Автоматическая генерация видео после пакета (v2.0 + ssv-video-creator)

1.  В `config.yaml` установите `video_synthesis.enabled: true`.
2.  Убедитесь, что `video_config.yaml` настроен.
3.  Запустите `main.py` как обычно. После создания пакета, `video_creator_main.py` будет вызван автоматически.

## Вклад в развитие

Мы приветствуем вклад в развитие проекта! Пожалуйста, следуйте стандартным практикам GitHub (fork, pull request).

## Автор

Профессор С.В. Сушков для медицинского сообщества.
