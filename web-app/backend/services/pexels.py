"""
Service Pexels pour télécharger des clips vidéo d'illustration
"""
import os
import aiohttp
import asyncio
from typing import Optional, List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env depuis la racine du projet
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


class PexelsService:
    """Service pour rechercher et télécharger des clips vidéo depuis Pexels"""
    
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY", "")
        self.base_url = "https://api.pexels.com"
        self.videos_url = f"{self.base_url}/videos/search"
    
    def is_configured(self) -> bool:
        """Vérifie si l'API Pexels est configurée"""
        return bool(self.api_key)
    
    async def search_videos(
        self,
        query: str,
        per_page: int = 5,
        orientation: str = "landscape",
        size: str = "medium"
    ) -> Optional[List[Dict]]:
        """
        Rechercher des vidéos sur Pexels
        
        Args:
            query: Mots-clés de recherche (en anglais de préférence)
            per_page: Nombre de résultats (1-80)
            orientation: landscape, portrait, square
            size: large, medium, small
            
        Returns:
            Liste de vidéos avec leurs URLs de téléchargement
        """
        if not self.api_key:
            print("[Pexels] API key non configurée")
            return None
        
        headers = {
            "Authorization": self.api_key
        }
        
        params = {
            "query": query,
            "per_page": min(per_page, 80),
            "orientation": orientation,
            "size": size
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.videos_url,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        print(f"[Pexels] Erreur API: {response.status}")
                        return None
                    
                    data = await response.json()
                    videos = data.get("videos", [])
                    
                    if not videos:
                        print(f"[Pexels] Aucune vidéo trouvée pour '{query}'")
                        return []
                    
                    # Extraire les informations utiles
                    results = []
                    for video in videos:
                        video_files = video.get("video_files", [])
                        
                        # Trouver la meilleure qualité HD (préférer 1080p ou 720p)
                        best_file = None
                        for vf in video_files:
                            quality = vf.get("quality", "")
                            width = vf.get("width", 0)
                            
                            if quality == "hd" and width >= 1280:
                                if best_file is None or width > best_file.get("width", 0):
                                    best_file = vf
                        
                        # Fallback sur la première vidéo HD disponible
                        if not best_file:
                            for vf in video_files:
                                if vf.get("quality") == "hd":
                                    best_file = vf
                                    break
                        
                        # Fallback sur n'importe quelle vidéo
                        if not best_file and video_files:
                            best_file = video_files[0]
                        
                        if best_file:
                            results.append({
                                "id": video.get("id"),
                                "width": best_file.get("width"),
                                "height": best_file.get("height"),
                                "duration": video.get("duration"),
                                "url": best_file.get("link"),
                                "file_type": best_file.get("file_type", "video/mp4"),
                                "user": video.get("user", {}).get("name", "Unknown"),
                                "thumbnail": video.get("image")
                            })
                    
                    print(f"[Pexels] {len(results)} vidéo(s) trouvée(s) pour '{query}'")
                    return results
                    
        except Exception as e:
            print(f"[Pexels] Erreur recherche: {e}")
            return None
    
    async def download_video(
        self,
        video_url: str,
        output_path: str,
        max_duration: Optional[float] = None
    ) -> bool:
        """
        Télécharger une vidéo Pexels
        
        Args:
            video_url: URL de la vidéo à télécharger
            output_path: Chemin de sortie du fichier
            max_duration: Durée max en secondes (optionnel, pour découper)
            
        Returns:
            True si téléchargé avec succès
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status != 200:
                        print(f"[Pexels] Erreur téléchargement: {response.status}")
                        return False
                    
                    # Télécharger en chunks
                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_file, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    print(f"[Pexels] Vidéo téléchargée: {output_path} ({output_file.stat().st_size} bytes)")
                    
                    # Si max_duration spécifié, découper la vidéo
                    if max_duration and max_duration > 0:
                        await self._trim_video(output_path, max_duration)
                    
                    return True
                    
        except Exception as e:
            print(f"[Pexels] Erreur téléchargement: {e}")
            return False
    
    async def _trim_video(self, video_path: str, max_duration: float) -> bool:
        """Découper une vidéo à une durée maximale"""
        import subprocess
        
        # Trouver FFmpeg
        ffmpeg_path = str(Path(__file__).parent.parent.parent.parent / "ffmpeg" / "ffmpeg.exe")
        if not Path(ffmpeg_path).exists():
            ffmpeg_path = "ffmpeg"
        
        temp_path = video_path + ".temp.mp4"
        
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-t", str(max_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            temp_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                # Remplacer le fichier original
                Path(video_path).unlink()
                Path(temp_path).rename(video_path)
                print(f"[Pexels] Vidéo découpée à {max_duration}s")
                return True
            else:
                print(f"[Pexels] Erreur découpage: {result.stderr[-200:]}")
                Path(temp_path).unlink(missing_ok=True)
                return False
        except Exception as e:
            print(f"[Pexels] Erreur découpage: {e}")
            Path(temp_path).unlink(missing_ok=True)
            return False
    
    async def search_and_download(
        self,
        query: str,
        output_path: str,
        max_duration: Optional[float] = None,
        orientation: str = "landscape"
    ) -> Optional[Dict]:
        """
        Rechercher et télécharger la meilleure vidéo pour un mot-clé
        
        Args:
            query: Mots-clés de recherche
            output_path: Chemin de sortie
            max_duration: Durée max en secondes
            orientation: landscape, portrait, square
            
        Returns:
            Informations sur la vidéo téléchargée ou None
        """
        # Rechercher des vidéos
        videos = await self.search_videos(query, per_page=3, orientation=orientation)
        
        if not videos:
            # Essayer avec un mot-clé plus générique
            generic_query = query.split()[0] if " " in query else query
            videos = await self.search_videos(generic_query, per_page=3, orientation=orientation)
        
        if not videos:
            print(f"[Pexels] Aucune vidéo trouvée pour '{query}'")
            return None
        
        # Prendre la première vidéo (meilleur match)
        video = videos[0]
        
        # Télécharger
        success = await self.download_video(
            video["url"],
            output_path,
            max_duration=max_duration
        )
        
        if success:
            video["local_path"] = output_path
            return video
        
        return None
    
    async def download_illustrations(
        self,
        illustrations: List[Dict],
        output_dir: str
    ) -> List[Dict]:
        """
        Télécharger plusieurs clips d'illustration
        
        Args:
            illustrations: Liste de {timestamp, duration, keyword, reason}
            output_dir: Dossier de sortie
            
        Returns:
            Liste des illustrations téléchargées avec leurs chemins locaux
        """
        if not self.api_key:
            print("[Pexels] API key non configurée - illustrations ignorées")
            return []
        
        results = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for i, illust in enumerate(illustrations):
            keyword = illust.get("keyword", "")
            duration = illust.get("duration", 3)
            
            if not keyword:
                continue
            
            # Nom de fichier sécurisé
            safe_keyword = "".join(c for c in keyword if c.isalnum() or c in " _-")[:30]
            filename = f"pexels_{i}_{safe_keyword.replace(' ', '_')}.mp4"
            file_path = str(output_path / filename)
            
            print(f"[Pexels] Téléchargement {i+1}/{len(illustrations)}: '{keyword}'")
            
            video_info = await self.search_and_download(
                query=keyword,
                output_path=file_path,
                max_duration=duration + 1,  # +1s de marge
                orientation="landscape"
            )
            
            if video_info:
                results.append({
                    **illust,
                    "local_path": file_path,
                    "pexels_id": video_info.get("id"),
                    "pexels_user": video_info.get("user"),
                    "downloaded": True
                })
            else:
                results.append({
                    **illust,
                    "downloaded": False,
                    "error": f"Aucune vidéo trouvée pour '{keyword}'"
                })
            
            # Petit délai entre les requêtes pour respecter les rate limits
            await asyncio.sleep(0.5)
        
        downloaded_count = sum(1 for r in results if r.get("downloaded"))
        print(f"[Pexels] {downloaded_count}/{len(illustrations)} illustrations téléchargées")
        
        return results



