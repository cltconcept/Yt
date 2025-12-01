"""
Service YouTube - Gestion de l'authentification OAuth2 et API YouTube
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("[YouTube] google-api-python-client non disponible. Installez: pip install google-api-python-client google-auth-oauthlib")

from dotenv import load_dotenv

load_dotenv()

# Scopes requis pour YouTube (inclure openid pour éviter l'erreur de scope change)
YOUTUBE_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]

# Chemin pour stocker les credentials
CREDENTIALS_PATH = Path(__file__).parent.parent / "data" / "youtube_credentials.json"

# Google OAuth - depuis env ou MongoDB
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')


class YouTubeService:
    _instance = None
    _credentials = None
    _youtube = None
    _analytics = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not GOOGLE_API_AVAILABLE:
            return
        
        # Créer le dossier data si nécessaire
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Charger les credentials si disponibles
        self._load_credentials()

    def _load_credentials(self):
        """Charger les credentials sauvegardées"""
        if CREDENTIALS_PATH.exists():
            try:
                with open(CREDENTIALS_PATH, 'r') as f:
                    creds_data = json.load(f)
                
                self._credentials = Credentials(
                    token=creds_data.get('token'),
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data.get('token_uri'),
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=creds_data.get('scopes')
                )
                
                # Vérifier si les credentials sont expirées
                if self._credentials.expired and self._credentials.refresh_token:
                    from google.auth.transport.requests import Request
                    self._credentials.refresh(Request())
                    self._save_credentials()
                
                self._init_services()
                print("[YouTube] Credentials chargées avec succès")
            except Exception as e:
                print(f"[YouTube] Erreur chargement credentials: {e}")
                self._credentials = None

    def _save_credentials(self):
        """Sauvegarder les credentials"""
        if self._credentials:
            creds_data = {
                'token': self._credentials.token,
                'refresh_token': self._credentials.refresh_token,
                'token_uri': self._credentials.token_uri,
                'client_id': self._credentials.client_id,
                'client_secret': self._credentials.client_secret,
                'scopes': self._credentials.scopes
            }
            with open(CREDENTIALS_PATH, 'w') as f:
                json.dump(creds_data, f)

    def _init_services(self):
        """Initialiser les services YouTube"""
        if self._credentials:
            try:
                self._youtube = build('youtube', 'v3', credentials=self._credentials)
                self._analytics = build('youtubeAnalytics', 'v2', credentials=self._credentials)
            except Exception as e:
                print(f"[YouTube] Erreur init services: {e}")

    def is_authenticated(self) -> bool:
        """Vérifier si l'utilisateur est authentifié"""
        # Recharger les credentials si pas chargées
        if self._credentials is None:
            self._load_credentials()
        return self._credentials is not None and self._youtube is not None

    def _get_client_config(self) -> Optional[Dict]:
        """Récupérer la config client OAuth depuis env ou MongoDB"""
        client_id = GOOGLE_CLIENT_ID
        client_secret = GOOGLE_CLIENT_SECRET
        
        # Essayer de récupérer depuis MongoDB si non défini
        if not client_id or not client_secret:
            try:
                from services.database import db
                client_id = db.get_api_key('GOOGLE_CLIENT_ID') or ''
                client_secret = db.get_api_key('GOOGLE_CLIENT_SECRET') or ''
            except:
                pass
        
        if not client_id or not client_secret:
            print("[YouTube] GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET non configuré")
            return None
        
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": []
            }
        }

    def get_auth_url(self, redirect_uri: str) -> Optional[str]:
        """Générer l'URL d'authentification OAuth2"""
        if not GOOGLE_API_AVAILABLE:
            return None
        
        client_config = self._get_client_config()
        if not client_config:
            return None
        
        try:
            flow = Flow.from_client_config(
                client_config,
                scopes=YOUTUBE_SCOPES,
                redirect_uri=redirect_uri
            )
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            return auth_url
        except Exception as e:
            print(f"[YouTube] Erreur génération URL auth: {e}")
            return None

    def authenticate(self, code: str, redirect_uri: str) -> bool:
        """Authentifier avec le code OAuth2"""
        if not GOOGLE_API_AVAILABLE:
            return False
        
        client_config = self._get_client_config()
        if not client_config:
            return False
        
        try:
            # Ne pas valider les scopes car Google ajoute openid/profile/email
            flow = Flow.from_client_config(
                client_config,
                scopes=YOUTUBE_SCOPES,
                redirect_uri=redirect_uri
            )
            # Désactiver la validation stricte des scopes
            flow.oauth2session._client.default_token_placement = 'query'
            flow.fetch_token(code=code)
            self._credentials = flow.credentials
            self._save_credentials()
            self._init_services()
            print("[YouTube] Authentification réussie")
            return True
        except Exception as e:
            # Si l'erreur est liée aux scopes, essayer avec les scopes étendus
            if "Scope has changed" in str(e):
                try:
                    extended_scopes = YOUTUBE_SCOPES + [
                        'openid',
                        'https://www.googleapis.com/auth/userinfo.profile',
                        'https://www.googleapis.com/auth/userinfo.email'
                    ]
                    flow = Flow.from_client_config(
                        client_config,
                        scopes=extended_scopes,
                        redirect_uri=redirect_uri
                    )
                    flow.fetch_token(code=code)
                    self._credentials = flow.credentials
                    self._save_credentials()
                    self._init_services()
                    print("[YouTube] Authentification réussie (scopes étendus)")
                    return True
                except Exception as e2:
                    print(f"[YouTube] Erreur authentification (retry): {e2}")
            print(f"[YouTube] Erreur authentification: {e}")
            return False

    def disconnect(self):
        """Déconnecter le compte YouTube"""
        self._credentials = None
        self._youtube = None
        self._analytics = None
        if CREDENTIALS_PATH.exists():
            CREDENTIALS_PATH.unlink()
        print("[YouTube] Déconnecté")

    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Récupérer les informations de la chaîne"""
        if not self.is_authenticated():
            return None
        
        try:
            response = self._youtube.channels().list(
                part='snippet,statistics,contentDetails,brandingSettings',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet'].get('description', ''),
                    'custom_url': channel['snippet'].get('customUrl', ''),
                    'thumbnail': channel['snippet']['thumbnails']['high']['url'],
                    'banner': channel.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl'),
                    'statistics': {
                        'subscribers': int(channel['statistics'].get('subscriberCount', 0)),
                        'views': int(channel['statistics'].get('viewCount', 0)),
                        'videos': int(channel['statistics'].get('videoCount', 0)),
                        'hidden_subscribers': channel['statistics'].get('hiddenSubscriberCount', False)
                    },
                    'uploads_playlist': channel['contentDetails']['relatedPlaylists']['uploads']
                }
            return None
        except Exception as e:
            print(f"[YouTube] Erreur get_channel_info: {e}")
            return None

    def get_recent_videos(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Récupérer les vidéos récentes"""
        if not self.is_authenticated():
            return []
        
        try:
            # D'abord récupérer la playlist des uploads
            channel = self.get_channel_info()
            if not channel:
                return []
            
            uploads_playlist = channel.get('uploads_playlist')
            if not uploads_playlist:
                return []
            
            # Récupérer les vidéos de la playlist
            response = self._youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist,
                maxResults=max_results
            ).execute()
            
            video_ids = [item['contentDetails']['videoId'] for item in response.get('items', [])]
            
            if not video_ids:
                return []
            
            # Récupérer les statistiques des vidéos
            videos_response = self._youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            videos = []
            for video in videos_response.get('items', []):
                # Déterminer si c'est un short (durée < 60s et ratio vertical)
                duration = video['contentDetails'].get('duration', 'PT0S')
                is_short = self._is_short(duration)
                
                videos.append({
                    'id': video['id'],
                    'title': video['snippet']['title'],
                    'description': video['snippet'].get('description', '')[:200],
                    'thumbnail': video['snippet']['thumbnails'].get('high', {}).get('url') or 
                                video['snippet']['thumbnails'].get('medium', {}).get('url'),
                    'published_at': video['snippet']['publishedAt'],
                    'duration': duration,
                    'is_short': is_short,
                    'statistics': {
                        'views': int(video['statistics'].get('viewCount', 0)),
                        'likes': int(video['statistics'].get('likeCount', 0)),
                        'comments': int(video['statistics'].get('commentCount', 0))
                    },
                    'url': f"https://www.youtube.com/watch?v={video['id']}"
                })
            
            return videos
        except Exception as e:
            print(f"[YouTube] Erreur get_recent_videos: {e}")
            return []

    def _is_short(self, duration: str) -> bool:
        """Vérifier si une vidéo est un Short basé sur la durée"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds <= 60
        return False

    def get_analytics(self, days: int = 28) -> Optional[Dict[str, Any]]:
        """Récupérer les analytics de la chaîne"""
        if not self.is_authenticated() or not self._analytics:
            return None
        
        try:
            channel = self.get_channel_info()
            if not channel:
                return None
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            response = self._analytics.reports().query(
                ids=f"channel=={channel['id']}",
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares',
                dimensions='day',
                sort='day'
            ).execute()
            
            # Traiter les données
            rows = response.get('rows', [])
            
            totals = {
                'views': 0,
                'watch_time_minutes': 0,
                'subscribers_gained': 0,
                'subscribers_lost': 0,
                'likes': 0,
                'comments': 0,
                'shares': 0
            }
            
            daily_data = []
            for row in rows:
                day_data = {
                    'date': row[0],
                    'views': row[1],
                    'watch_time': row[2],
                    'avg_duration': row[3],
                    'subs_gained': row[4],
                    'subs_lost': row[5],
                    'likes': row[6],
                    'comments': row[7],
                    'shares': row[8]
                }
                daily_data.append(day_data)
                
                totals['views'] += row[1]
                totals['watch_time_minutes'] += row[2]
                totals['subscribers_gained'] += row[4]
                totals['subscribers_lost'] += row[5]
                totals['likes'] += row[6]
                totals['comments'] += row[7]
                totals['shares'] += row[8]
            
            return {
                'period': f'{start_date} - {end_date}',
                'days': days,
                'totals': totals,
                'daily': daily_data
            }
        except Exception as e:
            print(f"[YouTube] Erreur get_analytics: {e}")
            return None

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: List[str] = None,
        category_id: str = "22",  # People & Blogs
        privacy: str = "private",
        is_short: bool = False,
        publish_at: str = None  # Format: "2025-12-01T18:00:00"
    ) -> Optional[Dict[str, Any]]:
        """Uploader une vidéo sur YouTube avec programmation optionnelle"""
        if not self.is_authenticated():
            return None
        
        if not Path(file_path).exists():
            print(f"[YouTube] Fichier non trouvé: {file_path}")
            return None
        
        try:
            # Ajouter #Shorts au titre si c'est un short
            if is_short and '#Shorts' not in title:
                title = f"{title} #Shorts"
            
            body = {
                'snippet': {
                    'title': title[:100],  # Max 100 caractères
                    'description': description[:5000],  # Max 5000 caractères
                    'tags': (tags or [])[:500],  # Max 500 tags
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': 'private' if publish_at else privacy,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Si programmation, ajouter publishAt
            if publish_at and privacy == 'public':
                # Convertir en format ISO 8601 avec timezone
                from datetime import datetime, timezone
                try:
                    dt = datetime.fromisoformat(publish_at)
                    # Ajouter timezone UTC+1 (Paris)
                    body['status']['publishAt'] = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    body['status']['privacyStatus'] = 'private'  # Doit être private pour programmer
                    print(f"[YouTube] Programmé pour: {body['status']['publishAt']}")
                except Exception as e:
                    print(f"[YouTube] Erreur date programmation: {e}")
            
            media = MediaFileUpload(
                file_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            request = self._youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"[YouTube] Upload: {int(status.progress() * 100)}%")
            
            video_id = response['id']
            scheduled_info = ""
            if publish_at:
                scheduled_info = f" (programmé pour {publish_at})"
            
            print(f"[YouTube] Vidéo uploadée: {video_id}{scheduled_info}")
            return {
                'id': video_id,
                'title': response['snippet']['title'],
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'status': response['status']['privacyStatus'],
                'scheduled_for': publish_at
            }
        except Exception as e:
            print(f"[YouTube] Erreur upload: {e}")
            return None

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Définir la miniature d'une vidéo"""
        if not self.is_authenticated():
            return False
        
        if not Path(thumbnail_path).exists():
            print(f"[YouTube] Miniature non trouvée: {thumbnail_path}")
            return False
        
        try:
            media = MediaFileUpload(
                thumbnail_path,
                mimetype='image/png',
                resumable=True
            )
            
            request = self._youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            response = request.execute()
            print(f"[YouTube] Miniature définie pour {video_id}")
            return True
        except Exception as e:
            print(f"[YouTube] Erreur miniature: {e}")
            return False


# Instance singleton
youtube_service = YouTubeService()

