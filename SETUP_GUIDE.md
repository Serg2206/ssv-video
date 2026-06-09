# SSVproff Video Creator v2.0 - Руководство по настройке

## 🚀 Новые возможности версии 2.0

### 1. TTS-озвучка (Text-to-Speech)
Автоматическая генерация аудио из текста транскрипции.

**Поддерживаемые движки:**
- **gTTS** (Google Text-to-Speech) - онлайн, высокое качество, требует интернет
- **pyttsx3** - офлайн, быстрее, менее естественно

**Настройка в `video_config.yaml`:**
```yaml
tts:
  engine: "gtts"  # или 'pyttsx3'
  language: "ru"
  rate: 150
  volume: 0.9
```

### 2. DALL-E превью
Генерация профессиональных превью через OpenAI DALL-E 3.

**Настройка:**
```yaml
thumbnail:
  generator: "dalle"  # или 'local_template'
  style: "professional"
```

**Требуется:**
- Установить `OPENAI_API_KEY` в переменные окружения
- Файл `.env` с содержимым: `OPENAI_API_KEY=sk-...`

### 3. Полная загрузка на YouTube
Автоматическая публикация видео с превью и метаданными.

**Настройка:**
```yaml
youtube:
  client_secrets_file: "client_secret.json"
  default_privacy: "private"
  auto_upload: false
```

---

## 📋 Пошаговая установка

### Шаг 1: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 2: Настройка TTS

**Вариант A: gTTS (рекомендуется)**
- Не требует дополнительной настройки
- Просто установите `engine: "gtts"` в конфиге

**Вариант B: pyttsx3 (офлайн)**
```bash
# Для Linux
sudo apt-get install espeak espeak-data libespeak-dev

# Для macOS
brew install espeak

# Для Windows
# Устанавливается автоматически с pyttsx3
```

### Шаг 3: Настройка DALL-E (опционально)

1. Получите API ключ OpenAI: https://platform.openai.com/api-keys
2. Создайте файл `.env` в корне проекта:
```
OPENAI_API_KEY=sk-your-api-key-here
```
3. Измените в `video_config.yaml`:
```yaml
thumbnail:
  generator: "dalle"
```

### Шаг 4: Настройка YouTube API

1. **Создайте проект в Google Cloud Console:**
   - Перейдите на https://console.cloud.google.com/
   - Создайте новый проект

2. **Включите YouTube Data API v3:**
   - В меню выберите "APIs & Services" → "Library"
   - Найдите "YouTube Data API v3" и включите

3. **Создайте OAuth 2.0 credentials:**
   - "APIs & Services" → "Credentials"
   - "Create Credentials" → "OAuth client ID"
   - Тип приложения: "Desktop app"
   - Скачайте JSON-файл и сохраните как `client_secret.json` в корне проекта

4. **Настройте OAuth consent screen:**
   - "APIs & Services" → "OAuth consent screen"
   - Выберите "External" (для тестирования)
   - Заполните обязательные поля
   - Добавьте scopes: `youtube.upload`, `youtube`

5. **Первое использование:**
   - При первом запуске откроется браузер для авторизации
   - Войдите в ваш Google аккаунт и предоставьте права
   - Токен сохранится в `token.pickle`

---

## 🎬 Использование

### Быстрый старт

```python
from modules.tts_generator import TTSGenerator
from modules.thumbnail_generator import ThumbnailGenerator
from video_modules.text_on_screen_generator import TextOnScreenGenerator
from modules.youtube_uploader import YouTubeUploader
import yaml

# Загрузка конфигурации
with open('video_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 1. Генерация озвучки
tts = TTSGenerator(config)
audio_path = tts.generate("Ваш текст для озвучки", "my_audio.mp3")

# 2. Генерация превью
thumb = ThumbnailGenerator(config)
thumbnail_path = thumb.generate("Заголовок видео", "Описание")

# 3. Создание видео с аудио
video_gen = TextOnScreenGenerator(config)
video_path = video_gen.generate(
    transcript="Ваш полный текст...",
    thumbnail_path=thumbnail_path,
    audio_path=audio_path,
    output_path="final_video.mp4"
)

# 4. Загрузка на YouTube (опционально)
uploader = YouTubeUploader(config)
video_id = uploader.upload(
    package_folder="./output",
    video_path=video_path,
    thumbnail_path=thumbnail_path,
    title="Заголовок",
    description="Описание",
    tags=["тег1", "тег2"]
)
```

### Конфигурационные файлы

**`.env`** (переменные окружения):
```
OPENAI_API_KEY=sk-...
```

**`video_config.yaml`**:
```yaml
tts:
  engine: "gtts"
  language: "ru"

thumbnail:
  generator: "dalle"

video_generation:
  method: "text_on_screen_with_audio"
  duration_per_text_chunk: 5

youtube:
  client_secrets_file: "client_secret.json"
  default_privacy: "private"
  auto_upload: false
```

---

## 🔧 Решение проблем

### Ошибки TTS

**gTTS не работает:**
- Проверьте подключение к интернету
- Убедитесь, что IP не заблокирован Google
- Переключитесь на `pyttsx3`

**pyttsx3 нет русского голоса:**
```bash
# Linux
sudo apt-get install espeak-rus

# Проверка доступных голосов
python3 -c "import pyttsx3; e=pyttsx3.init(); print([v.name for v in e.getProperty('voices')])"
```

### Ошибки DALL-E

**"Invalid API key":**
- Проверьте `OPENAI_API_KEY` в `.env`
- Убедитесь, что на счету есть средства

**"Rate limit exceeded":**
- DALL-E 3 имеет лимиты запросов
- Подождите несколько минут или используйте локальный шаблон

### Ошибки YouTube

**"Insufficient permissions":**
- Проверьте scopes в `youtube_uploader.py`
- Пересоздайте `token.pickle` (удалите и запустите снова)

**"Quota exceeded":**
- YouTube API имеет дневной лимит (по умолчанию 10 000 единиц)
- Загрузка видео стоит ~1600 единиц
- Увеличьте квоту в Google Cloud Console

---

## 📊 Сравнение режимов

| Функция | Базовый (v1.0) | Продвинутый (v2.0) |
|---------|---------------|-------------------|
| Видео | Текст на экране | Текст + озвучка |
| Превью | Локальный шаблон | DALL-E AI |
| Аудио | Нет | gTTS/pyttsx3 |
| YouTube | Заглушка | Полная загрузка |
| Сложность | Низкая | Средняя |
| Качество | Базовое | Профессиональное |

---

## 💡 Советы для профессионального видео

1. **Оптимальная длительность чанка:** 4-6 секунд для комфортного чтения
2. **TTS язык:** Используйте `ru` для русского, `en` для английского
3. **Превью DALL-E:** Добавляйте в промпт стиль ("medical", "surgical", "modern")
4. **YouTube:** Загружайте как `private`, проверяйте, затем меняйте на `public`
5. **Аудио:** gTTS качественнее, но pyttsx3 быстрее для тестов

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи ошибок
2. Убедитесь, что все зависимости установлены
3. Проверьте переменные окружения
4. Перечитайте это руководство

**Готово к созданию профессионального контента для SSVproff!** 🎥
