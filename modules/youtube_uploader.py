
"""
youtube_uploader.py - Публикация на YouTube
Полная реализация с OAuth 2.0 и загрузкой видео
"""
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class YouTubeUploader:
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube'
    ]

    def __init__(self, config):
        self.config = config
        self.client_secrets_file = config['youtube']['client_secrets_file']
        self.youtube = None
        self.youtube_upload = None

    def authenticate(self):
        """Аутентификация в YouTube API"""
        creds = None
        token_file = 'token.pickle'

        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secrets_file):
                    print(f"  ! Файл {self.client_secrets_file} не найден!")
                    print("  Создайте credentials в Google Cloud Console:")
                    print("  https://console.cloud.google.com/apis/credentials")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, self.SCOPES)
                creds = flow.run_local_server(port=0, open_browser=True)

            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        # Инициализация клиентов API
        self.youtube = build('youtube', 'v3', credentials=creds)
        self.youtube_upload = build('youtube', 'v3', credentials=creds)
        
        print("  ✓ Аутентификация YouTube успешна")
        return True

    def upload(self, package_folder, video_path=None, title=None, description=None, tags=None, thumbnail_path=None):
        """Загрузка видео на YouTube"""
        if not self.youtube_upload:
            if not self.authenticate():
                return None
        
        # Поиск видеофайла в пакете
        if not video_path:
            video_path = os.path.join(package_folder, "video.mp4")
            if not os.path.exists(video_path):
                # Поиск других форматов
                for ext in ['mp4', 'mov', 'avi', 'mkv']:
                    test_path = os.path.join(package_folder, f"video.{ext}")
                    if os.path.exists(test_path):
                        video_path = test_path
                        break
        
        if not os.path.exists(video_path):
            print(f"  ! Видеофайл не найден: {video_path}")
            return None
        
        # Загрузка метаданных из пакета
        metadata_path = os.path.join(package_folder, "metadata.json")
        if os.path.exists(metadata_path) and not title:
            import json
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if not title:
                    title = metadata.get('title', 'SSVproff Video')
                if not description:
                    description = metadata.get('description', '')
                if not tags:
                    tags = metadata.get('tags', [])
        
        # Подготовка тела запроса
        body = {
            'snippet': {
                'title': title or 'SSVproff Video',
                'description': description or '',
                'tags': tags or ['SSVproff', 'медицина', 'хирургия'],
                'categoryId': '27'  # Образование
            },
            'status': {
                'privacyStatus': 'private',  # private, public, unlisted
                'madeForKids': False,
                'selfDeclaredMadeForKids': False
            }
        }
        
        print(f"  - Загрузка видео: {video_path}")
        print(f"  - Название: {title}")
        
        try:
            # Загрузка медиафайла
            media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
            
            request = self.youtube_upload.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  - Прогресс загрузки: {progress}%")
            
            video_id = response['id']
            print(f"  ✓ Видео загружено! ID: {video_id}")
            print(f"  Ссылка: https://www.youtube.com/watch?v={video_id}")
            
            # Загрузка превью (если есть)
            if thumbnail_path and os.path.exists(thumbnail_path):
                self._upload_thumbnail(video_id, thumbnail_path)
            
            return video_id
            
        except HttpError as e:
            print(f"  ! Ошибка YouTube API: {e}")
            if e.resp.status == 403:
                print("  Проверьте квоты API и права доступа в Google Cloud Console")
            return None
        except Exception as e:
            print(f"  ! Ошибка при загрузке: {e}")
            return None

    def _upload_thumbnail(self, video_id, thumbnail_path):
        """Загрузка пользовательского превью"""
        try:
            print(f"  - Загрузка превью: {thumbnail_path}")
            
            media = MediaFileUpload(thumbnail_path, mimetype='image/png')
            
            request = self.youtube_upload.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            response = request.execute()
            print(f"  ✓ Превью установлено!")
            return response
            
        except Exception as e:
            print(f"  ! Ошибка загрузки превью: {e}")
            return None

    def update_video_status(self, video_id, privacy_status='public'):
        """Изменение статуса приватности видео"""
        if not self.youtube:
            if not self.authenticate():
                return False
        
        try:
            request = self.youtube.videos().update(
                part='status',
                body={
                    'id': video_id,
                    'status': {
                        'privacyStatus': privacy_status
                    }
                }
            )
            response = request.execute()
            print(f"  ✓ Статус видео изменён на: {privacy_status}")
            return True
        except Exception as e:
            print(f"  ! Ошибка обновления статуса: {e}")
            return False
