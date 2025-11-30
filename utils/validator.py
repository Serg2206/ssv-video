"""
Модуль валидации данных для SSV-Video с использованием Pydantic.

Предоставляет модели для валидации входных данных и конфигурации.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from pathlib import Path


class VideoQuality(str, Enum):
    """Качество видео."""
    LOW = "480p"
    MEDIUM = "720p"
    HIGH = "1080p"
    ULTRA = "4k"


class APIProvider(str, Enum):
    """Провайдер API."""
    OPENAI = "openai"
    PEXELS = "pexels"
    PIXABAY = "pixabay"


class VideoFormat(str, Enum):
    """Формат выходного видео."""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"


class ContentRequest(BaseModel):
    """Модель запроса на генерацию контента."""
    
    model_config = ConfigDict(extra='forbid')
    
    topic: str = Field(
        ..., 
        min_length=3, 
        max_length=200,
        description="Тема для генерации контента"
    )
    
    keywords: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Ключевые слова для поиска материалов"
    )
    
    language: str = Field(
        default="ru",
        pattern="^[a-z]{2}$",
        description="Код языка (ISO 639-1)"
    )
    
    duration: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Длительность видео в секундах (10-600)"
    )
    
    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Валидирует ключевые слова."""
        if not v:
            return v
        
        # Проверяем каждое ключевое слово
        for keyword in v:
            if not keyword or not keyword.strip():
                raise ValueError("Ключевые слова не могут быть пустыми")
            if len(keyword) > 50:
                raise ValueError(f"Ключевое слово слишком длинное: {keyword}")
        
        return [k.strip() for k in v]
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Валидирует тему."""
        v = v.strip()
        if not v:
            raise ValueError("Тема не может быть пустой")
        return v


class VideoGenerationConfig(BaseModel):
    """Конфигурация генерации видео."""
    
    model_config = ConfigDict(extra='forbid')
    
    quality: VideoQuality = Field(
        default=VideoQuality.HIGH,
        description="Качество видео"
    )
    
    format: VideoFormat = Field(
        default=VideoFormat.MP4,
        description="Формат выходного файла"
    )
    
    fps: int = Field(
        default=30,
        ge=24,
        le=60,
        description="Кадров в секунду (24-60)"
    )
    
    bitrate: Optional[str] = Field(
        default="2M",
        pattern="^[0-9]+[KM]$",
        description="Битрейт видео (например, '2M' или '500K')"
    )
    
    output_dir: Path = Field(
        default=Path("output"),
        description="Директория для сохранения видео"
    )
    
    add_watermark: bool = Field(
        default=False,
        description="Добавлять ли водяной знак"
    )
    
    add_subtitles: bool = Field(
        default=True,
        description="Добавлять ли субтитры"
    )


class APICredentials(BaseModel):
    """Учетные данные для API."""
    
    model_config = ConfigDict(extra='forbid')
    
    provider: APIProvider = Field(
        ...,
        description="Провайдер API"
    )
    
    api_key: str = Field(
        ...,
        min_length=10,
        description="API ключ"
    )
    
    api_url: Optional[str] = Field(
        default=None,
        description="Базовый URL API (опционально)"
    )
    
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Таймаут запроса в секундах (5-300)"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Максимальное количество повторов (0-10)"
    )
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Валидирует API ключ."""
        v = v.strip()
        if not v:
            raise ValueError("API ключ не может быть пустым")
        # Проверяем на placeholder значения
        if v.lower() in ['your_api_key', 'api_key_here', 'xxx']:
            raise ValueError("Необходимо указать настоящий API ключ")
        return v


class ScriptSegment(BaseModel):
    """Сегмент сценария видео."""
    
    model_config = ConfigDict(extra='forbid')
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Текст сегмента"
    )
    
    duration: float = Field(
        ...,
        ge=0.5,
        le=60.0,
        description="Длительность сегмента в секундах (0.5-60)"
    )
    
    keywords: List[str] = Field(
        default_factory=list,
        description="Ключевые слова для поиска визуального контента"
    )
    
    scene_type: str = Field(
        default="default",
        description="Тип сцены (default, intro, outro, transition)"
    )


class VideoScript(BaseModel):
    """Полный сценарий видео."""
    
    model_config = ConfigDict(extra='forbid')
    
    title: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Название видео"
    )
    
    description: str = Field(
        default="",
        max_length=5000,
        description="Описание видео"
    )
    
    segments: List[ScriptSegment] = Field(
        ...,
        min_length=1,
        description="Список сегментов сценария"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        max_length=15,
        description="Теги видео"
    )
    
    total_duration: Optional[float] = Field(
        default=None,
        description="Общая длительность видео"
    )
    
    @field_validator('segments')
    @classmethod
    def validate_segments(cls, v: List[ScriptSegment]) -> List[ScriptSegment]:
        """Валидирует сегменты."""
        if not v:
            raise ValueError("Сценарий должен содержать хотя бы один сегмент")
        
        # Проверяем общую длительность
        total_duration = sum(segment.duration for segment in v)
        if total_duration > 600:  # 10 минут
            raise ValueError(
                f"Общая длительность сценария ({total_duration:.1f}s) "
                "превышает максимум (600s)"
            )
        
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """Вычисляет общую длительность после инициализации."""
        if self.total_duration is None:
            self.total_duration = sum(
                segment.duration for segment in self.segments
            )


class VideoMetadata(BaseModel):
    """Метаданные видео."""
    
    model_config = ConfigDict(extra='forbid')
    
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(default="", max_length=5000)
    tags: List[str] = Field(default_factory=list, max_length=15)
    category: str = Field(default="Education")
    language: str = Field(default="ru", pattern="^[a-z]{2}$")
    duration: Optional[float] = Field(default=None, ge=0)
    created_at: Optional[str] = Field(default=None)
    file_path: Optional[Path] = Field(default=None)
    file_size: Optional[int] = Field(default=None, ge=0)
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Валидирует теги."""
        if not v:
            return v
        
        cleaned_tags = []
        for tag in v:
            tag = tag.strip()
            if tag and len(tag) <= 30:
                cleaned_tags.append(tag)
        
        return cleaned_tags[:15]  # Максимум 15 тегов


# Утилиты для валидации

def validate_file_path(path: Path, must_exist: bool = True) -> Path:
    """
    Валидирует путь к файлу.
    
    Args:
        path: Путь для валидации
        must_exist: Должен ли файл существовать
        
    Returns:
        Валидный путь
        
    Raises:
        ValueError: Если путь невалиден
    """
    if not isinstance(path, Path):
        path = Path(path)
    
    if must_exist and not path.exists():
        raise ValueError(f"Файл не существует: {path}")
    
    if must_exist and not path.is_file():
        raise ValueError(f"Путь не является файлом: {path}")
    
    return path


def validate_directory(path: Path, create: bool = False) -> Path:
    """
    Валидирует директорию.
    
    Args:
        path: Путь для валидации
        create: Создавать ли директорию, если не существует
        
    Returns:
        Валидный путь к директории
        
    Raises:
        ValueError: Если путь невалиден
    """
    if not isinstance(path, Path):
        path = Path(path)
    
    if not path.exists():
        if create:
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError(f"Директория не существует: {path}")
    
    if not path.is_dir():
        raise ValueError(f"Путь не является директорией: {path}")
    
    return path
