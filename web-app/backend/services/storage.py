"""
Service de stockage MinIO
Gère l'upload et le téléchargement des fichiers vers MinIO (S3-compatible)
"""
import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

# Configuration MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Buckets
BUCKET_PROJECTS = "projects"  # Projets complets (original, nosilence, etc.)
BUCKET_SHORTS = "shorts"      # Shorts générés
BUCKET_THUMBNAILS = "thumbnails"  # Miniatures
BUCKET_ASSETS = "assets"      # Assets (logo, etc.)


class StorageService:
    """Service de stockage MinIO"""
    
    def __init__(self):
        self.client: Optional[Minio] = None
        self._connected = False
    
    def connect(self) -> bool:
        """Se connecter à MinIO"""
        try:
            self.client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            
            # Créer les buckets s'ils n'existent pas
            for bucket in [BUCKET_PROJECTS, BUCKET_SHORTS, BUCKET_THUMBNAILS, BUCKET_ASSETS]:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    print(f"[MINIO] Bucket créé: {bucket}")
            
            self._connected = True
            print(f"[MINIO] Connecté à {MINIO_ENDPOINT}")
            return True
            
        except Exception as e:
            print(f"[MINIO] Erreur connexion: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Vérifie si connecté à MinIO"""
        if not self._connected or not self.client:
            return self.connect()
        return self._connected
    
    def upload_file(
        self, 
        local_path: str, 
        bucket: str, 
        object_name: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload un fichier vers MinIO
        
        Args:
            local_path: Chemin local du fichier
            bucket: Nom du bucket
            object_name: Nom de l'objet dans MinIO (ex: video_xxx/original.mp4)
            content_type: Type MIME (auto-détecté si non fourni)
        
        Returns:
            URL de l'objet ou None si erreur
        """
        if not self.is_connected():
            print(f"[MINIO] Non connecté, impossible d'uploader {local_path}")
            return None
        
        local_path = Path(local_path)
        if not local_path.exists():
            print(f"[MINIO] Fichier non trouvé: {local_path}")
            return None
        
        # Auto-détection du content-type
        if not content_type:
            ext = local_path.suffix.lower()
            content_types = {
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.json': 'application/json',
                '.txt': 'text/plain',
                '.ass': 'text/plain',
            }
            content_type = content_types.get(ext, 'application/octet-stream')
        
        try:
            self.client.fput_object(
                bucket,
                object_name,
                str(local_path),
                content_type=content_type
            )
            
            size_mb = local_path.stat().st_size / 1024 / 1024
            print(f"[MINIO] Uploadé: {bucket}/{object_name} ({size_mb:.2f} MB)")
            
            return f"{bucket}/{object_name}"
            
        except S3Error as e:
            print(f"[MINIO] Erreur upload {object_name}: {e}")
            return None
    
    def upload_project_file(self, project_folder: str, filename: str) -> Optional[str]:
        """
        Upload un fichier de projet vers MinIO
        
        Args:
            project_folder: Chemin du dossier projet (ex: /app/output/video_xxx)
            filename: Nom du fichier (ex: original.mp4)
        
        Returns:
            URL de l'objet ou None
        """
        project_folder = Path(project_folder)
        folder_name = project_folder.name
        local_path = project_folder / filename
        
        if not local_path.exists():
            return None
        
        object_name = f"{folder_name}/{filename}"
        return self.upload_file(str(local_path), BUCKET_PROJECTS, object_name)
    
    def upload_project_folder(self, project_folder: str) -> Dict[str, str]:
        """
        Upload tous les fichiers d'un projet vers MinIO
        
        Args:
            project_folder: Chemin du dossier projet
        
        Returns:
            Dict avec les URLs des fichiers uploadés
        """
        project_folder = Path(project_folder)
        folder_name = project_folder.name
        uploaded = {}
        
        # Fichiers principaux
        main_files = [
            'screen.mp4', 'webcam.mp4', 'config.json',
            'original.mp4', 'nosilence.mp4', 'illustrated.mp4',
            'thumbnail.png', 'transcription.json', 'transcription.txt',
            'seo.json', 'schedule.json'
        ]
        
        for filename in main_files:
            result = self.upload_project_file(project_folder, filename)
            if result:
                uploaded[filename] = result
        
        # Shorts
        shorts_dir = project_folder / "shorts"
        if shorts_dir.exists():
            for short_file in shorts_dir.glob("*.mp4"):
                object_name = f"{folder_name}/shorts/{short_file.name}"
                result = self.upload_file(str(short_file), BUCKET_SHORTS, object_name)
                if result:
                    uploaded[f"shorts/{short_file.name}"] = result
        
        # B-roll
        broll_dir = project_folder / "broll"
        if broll_dir.exists():
            for broll_file in broll_dir.glob("*.mp4"):
                object_name = f"{folder_name}/broll/{broll_file.name}"
                result = self.upload_file(str(broll_file), BUCKET_PROJECTS, object_name)
                if result:
                    uploaded[f"broll/{broll_file.name}"] = result
        
        print(f"[MINIO] Projet {folder_name}: {len(uploaded)} fichiers uploadés")
        return uploaded
    
    def get_presigned_url(
        self, 
        bucket: str, 
        object_name: str, 
        expires: int = 3600
    ) -> Optional[str]:
        """
        Obtenir une URL présignée pour télécharger un fichier
        
        Args:
            bucket: Nom du bucket
            object_name: Nom de l'objet
            expires: Durée de validité en secondes (défaut: 1h)
        
        Returns:
            URL présignée ou None
        """
        if not self.is_connected():
            return None
        
        try:
            url = self.client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            print(f"[MINIO] Erreur presigned URL: {e}")
            return None
    
    def list_project_files(self, folder_name: str) -> List[Dict]:
        """
        Lister tous les fichiers d'un projet
        
        Args:
            folder_name: Nom du dossier projet (ex: video_xxx)
        
        Returns:
            Liste des fichiers avec leurs métadonnées
        """
        if not self.is_connected():
            return []
        
        files = []
        
        try:
            # Fichiers dans projects/
            objects = self.client.list_objects(BUCKET_PROJECTS, prefix=f"{folder_name}/")
            for obj in objects:
                files.append({
                    'bucket': BUCKET_PROJECTS,
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None
                })
            
            # Shorts
            objects = self.client.list_objects(BUCKET_SHORTS, prefix=f"{folder_name}/")
            for obj in objects:
                files.append({
                    'bucket': BUCKET_SHORTS,
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None
                })
                
        except S3Error as e:
            print(f"[MINIO] Erreur listing: {e}")
        
        return files
    
    def delete_project(self, folder_name: str) -> bool:
        """
        Supprimer tous les fichiers d'un projet
        
        Args:
            folder_name: Nom du dossier projet
        
        Returns:
            True si succès
        """
        if not self.is_connected():
            return False
        
        try:
            # Supprimer de projects/
            objects = self.client.list_objects(BUCKET_PROJECTS, prefix=f"{folder_name}/", recursive=True)
            for obj in objects:
                self.client.remove_object(BUCKET_PROJECTS, obj.object_name)
            
            # Supprimer de shorts/
            objects = self.client.list_objects(BUCKET_SHORTS, prefix=f"{folder_name}/", recursive=True)
            for obj in objects:
                self.client.remove_object(BUCKET_SHORTS, obj.object_name)
            
            print(f"[MINIO] Projet {folder_name} supprimé")
            return True
            
        except S3Error as e:
            print(f"[MINIO] Erreur suppression: {e}")
            return False


# Instance globale
storage = StorageService()


