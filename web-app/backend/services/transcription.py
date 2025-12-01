"""
Service de transcription avec Groq Whisper
"""
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Charger le .env depuis la racine du projet
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Essayer le .env local


class TranscriptionService:
    """Gère la transcription audio avec Groq"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        # Utiliser FFmpeg portable du projet
        possible_paths = [
            r"C:\Dev\Yt\ffmpeg\ffmpeg.exe",  # FFmpeg portable du projet
            "ffmpeg",  # Dans le PATH
        ]
        
        self.ffmpeg_path = "ffmpeg"
        for path in possible_paths:
            if os.path.exists(path):
                self.ffmpeg_path = path
                print(f"[Transcription] FFmpeg: {path}")
                break
    
    async def transcribe(
        self,
        video_path: str,
        language: str = "fr"
    ) -> dict:
        """
        Transcrire une vidéo
        
        Args:
            video_path: Chemin de la vidéo
            language: Langue (fr, en, etc.)
        
        Returns:
            dict avec text, segments, language
        """
        try:
            # Extraire l'audio
            audio_path = video_path.replace(".mp4", ".mp3").replace(".webm", ".mp3")
            await self._extract_audio(video_path, audio_path)
            
            # Transcrire avec Groq
            if self.api_key:
                result = await self._transcribe_with_groq(audio_path, language)
            else:
                result = {
                    "text": "[Transcription non disponible - GROQ_API_KEY manquante]",
                    "segments": [],
                    "language": language
                }
            
            # Nettoyer
            Path(audio_path).unlink(missing_ok=True)
            
            return result
            
        except Exception as e:
            print(f"Erreur transcription: {e}")
            return {
                "text": f"[Erreur: {str(e)}]",
                "segments": [],
                "language": language
            }
    
    async def _extract_audio(self, video_path: str, audio_path: str) -> bool:
        """Extraire l'audio d'une vidéo"""
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            "-y",
            audio_path
        ]
        
        try:
            print(f"[Transcription] Extraction audio: {video_path}")
            
            # Sur Windows, utiliser subprocess.run dans un thread pool
            def run_ffmpeg():
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minutes max
                )
                return result
            
            # Exécuter dans un thread pool pour ne pas bloquer
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_ffmpeg)
            
            if result.returncode == 0:
                print(f"[Transcription] Audio extrait: {audio_path}")
                return True
            else:
                print(f"[Transcription] Erreur extraction: {result.stderr[:500]}")
                return False
                
        except Exception as e:
            import traceback
            print(f"[Transcription] Exception extraction: {e}")
            print(traceback.format_exc())
            return False
    
    async def _transcribe_with_groq(self, audio_path: str, language: str) -> dict:
        """Transcrire avec l'API Groq"""
        try:
            from groq import Groq
            
            client = Groq(api_key=self.api_key)
            
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model="whisper-large-v3",
                    language=language,
                    response_format="verbose_json"
                )
            
            # Parser le résultat
            if hasattr(transcription, 'text'):
                text = transcription.text
                segments = []
                
                if hasattr(transcription, 'segments'):
                    segments = [
                        {
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "text": seg.get("text", "")
                        }
                        for seg in transcription.segments
                    ]
                
                return {
                    "text": text,
                    "segments": segments,
                    "language": language
                }
            
            return {
                "text": str(transcription),
                "segments": [],
                "language": language
            }
            
        except Exception as e:
            print(f"Groq error: {e}")
            return {
                "text": f"[Erreur Groq: {str(e)}]",
                "segments": [],
                "language": language
            }

