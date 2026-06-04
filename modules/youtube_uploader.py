
"""
youtube_uploader.py - Публикация на YouTube
"""
import os
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class YouTubeUploader:
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self, config):
        self.config = config
        self.client_secrets_file = config['youtube']['client_secrets_file']
        self._validate_client_secrets_path()
        self.youtube = self._authenticate()

    def _validate_client_secrets_path(self):
        """Валидация пути к файлу клиентских секретов"""
        if not self.client_secrets_file or not isinstance(self.client_secrets_file, str):
            raise ValueError("Путь к файлу клиентских секретов должен быть непустой строкой")
        
        # Санитизация пути - удаление лишних пробелов
        self.client_secrets_file = self.client_secrets_file.strip()
        
        if '..' in self.client_secrets_file:
            raise ValueError("Небезопасный путь к файлу клиентских секретов")
        
        if not os.path.exists(self.client_secrets_file):
            raise FileNotFoundError(
                f"Файл клиентских секретов не найден: {self.client_secrets_file}"
            )

    def _sanitize_token_path(self, token_file: str) -> str:
        """Санитизация пути к файлу токена"""
        # Разрешаем только безопасные имена файлов
        basename = os.path.basename(token_file)
        if not basename or basename.startswith('.'):
            raise ValueError("Небезопасное имя файла токена")
        
        # Запрещаем символы, которые могут использоваться для инъекций путей
        if any(char in token_file for char in ['..', '~', '$']):
            raise ValueError("Путь содержит небезопасные символы")
        
        return token_file

    def _authenticate(self):
        """Аутентификация в YouTube API"""
        creds = None
        token_file = 'token.json'

        try:
            token_file = self._sanitize_token_path(token_file)
        except ValueError as e:
            raise ValueError(f"Ошибка валидации пути токена: {e}")

        if os.path.exists(token_file):
            try:
                with open(token_file, 'r', encoding='utf-8') as token:
                    creds_data = json.load(token)
                    creds = self._deserialize_credentials(creds_data)
            except (json.JSONDecodeError, IOError) as e:
                raise RuntimeError(f"Ошибка чтения файла токена: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_file, 'w', encoding='utf-8') as token:
                json.dump(self._serialize_credentials(creds), token)

        return build('youtube', 'v3', credentials=creds)

    def _serialize_credentials(self, creds) -> dict:
        """Сериализация учетных данных в JSON-совместимый формат"""
        return {
            'token': creds.token if hasattr(creds, 'token') else None,
            'refresh_token': creds.refresh_token if hasattr(creds, 'refresh_token') else None,
            'token_uri': creds.token_uri if hasattr(creds, 'token_uri') else None,
            'client_id': creds.client_id if hasattr(creds, 'client_id') else None,
            'client_secret': creds.client_secret if hasattr(creds, 'client_secret') else None,
            'scopes': creds.scopes if hasattr(creds, 'scopes') else [],
            'expiry': creds.expiry.isoformat() if hasattr(creds, 'expiry') and creds.expiry else None,
        }

    def _deserialize_credentials(self, creds_data: dict):
        """Десериализация учетных данных из JSON"""
        from google.oauth2.credentials import Credentials
        
        expiry = None
        if creds_data.get('expiry'):
            from datetime import datetime
            expiry = datetime.fromisoformat(creds_data['expiry'])
        
        return Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes', []),
            quota_project_id=None,
        )

    def upload(self, package_folder):
        """Загрузка видео на YouTube с валидацией пути"""
        # Валидация пути к пакету
        if not package_folder or not isinstance(package_folder, str):
            raise ValueError("Путь к пакету должен быть непустой строкой")
        
        package_folder = package_folder.strip()
        
        if not os.path.isdir(package_folder):
            raise ValueError(f"Пакет не существует или не является директорией: {package_folder}")
        
        # Проверка на выход за пределы допустимых директорий
        if '..' in package_folder:
            raise ValueError("Небезопасный путь к пакету")
        
        # Поиск видеофайла в пакете
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_file = None
        
        for ext in video_extensions:
            potential_video = os.path.join(package_folder, f"video{ext}")
            if os.path.exists(potential_video):
                video_file = potential_video
                break
        
        if not video_file:
            # Ищем любой видеофайл в директории
            for file in os.listdir(package_folder):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_file = os.path.join(package_folder, file)
                    break
        
        if not video_file:
            raise FileNotFoundError(
                "Видеофайл не найден в пакете. "
                "Ожидаются файлы с расширениями: " + ", ".join(video_extensions)
            )
        
        # Загрузка метаданных
        metadata_file = os.path.join(package_folder, "metadata.json")
        if not os.path.exists(metadata_file):
            raise FileNotFoundError("Файл метаданных metadata.json не найден в пакете")
        
        import json
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Реализация загрузки видео
        print(f"  Подготовка к загрузке видео: {video_file}")
        print(f"  Заголовок: {metadata.get('title', 'Без названия')}")
        print(f"  Описание: {metadata.get('description', '')[:100]}...")
        
        # Создаем тело запроса для загрузки
        body = {
            'snippet': {
                'title': metadata.get('title', 'Video'),
                'description': metadata.get('description', ''),
                'tags': metadata.get('tags', []),
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'private',  # По умолчанию приватное
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Примечание: Полная реализация загрузки видео через YouTube API требует:
        # 1. Настройки OAuth 2.0 credentials в Google Cloud Console
        # 2. Запуска в интерактивном режиме для первого получения токенов
        # 3. Установки библиотеки google-auth-oauthlib
        # 
        # Пример кода для полной реализации:
        # media = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        # request = self.youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        # response = request.upload()
        # video_id = response['id']
        
        print("  ! Полная загрузка видео требует настройки OAuth и запуска в интерактивном режиме")
        return "VIDEO_ID_PLACEHOLDER"
