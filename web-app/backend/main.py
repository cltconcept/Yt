"""
Backend FastAPI pour YouTube Pipeline
Gère la fusion vidéo, transcription et traitement
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import uuid
import shutil
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Charger le .env depuis la racine du projet
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Essayer le .env local

from services.video_merger import VideoMerger
from services.transcription import TranscriptionService
from services.openrouter import OpenRouterService
from services.openrouter import OpenRouterService

app = FastAPI(
    title="YouTube Pipeline API",
    description="API pour le traitement vidéo et transcription",
    version="2.0.0"
)

# CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3010",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3010"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import et inclusion des routers
try:
    from routers.projects import router as projects_router
    from routers.api_keys import router as api_keys_router
    from routers.youtube import router as youtube_router
    from routers.tiktok import router as tiktok_router
    from routers.instagram import router as instagram_router
    app.include_router(projects_router)
    app.include_router(api_keys_router)
    app.include_router(youtube_router)
    app.include_router(tiktok_router)
    app.include_router(instagram_router)
    print("[INIT] Routers projets, API keys, YouTube, TikTok et Instagram chargés")
except ImportError as e:
    print(f"[INIT] Routers non disponibles: {e}")

# Initialisation base de données
try:
    from services.database import db
    if db.is_connected():
        db.init_default_api_keys()
        print("[INIT] Base de données MongoDB connectée")
except Exception as e:
    print(f"[INIT] MongoDB non disponible: {e}")

# Dossiers - Utilise les chemins locaux dans le dossier backend
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print(f"[INIT] UPLOAD_DIR: {UPLOAD_DIR.absolute()}")
print(f"[INIT] OUTPUT_DIR: {OUTPUT_DIR.absolute()}")

# Servir les fichiers de sortie via route API (plus fiable que StaticFiles)
@app.get("/output/{file_path:path}")
async def get_output_file(file_path: str):
    """Servir un fichier de sortie ou lister le contenu d'un dossier"""
    full_path = OUTPUT_DIR / file_path
    
    # Si c'est un dossier, retourner la liste des fichiers
    if full_path.exists() and full_path.is_dir():
        files = []
        for item in sorted(full_path.iterdir()):
            size = item.stat().st_size if item.is_file() else 0
            files.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": size,
                "size_mb": round(size / 1024 / 1024, 2) if item.is_file() else 0,
                "url": f"/output/{file_path}/{item.name}" if file_path else f"/output/{item.name}"
            })
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dossier: {}</title>
            <style>
                body {{ font-family: monospace; background: #1a1a1a; color: #fff; padding: 20px; }}
                h1 {{ color: #fff; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
                th {{ background: #2a2a2a; }}
                a {{ color: #60a5fa; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .dir {{ color: #fbbf24; }}
                .file {{ color: #60a5fa; }}
                .delete-btn {{
                    background: #dc2626;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    margin-left: 10px;
                }}
                .delete-btn:hover {{
                    background: #b91c1c;
                }}
                .delete-btn:disabled {{
                    background: #666;
                    cursor: not-allowed;
                }}
            </style>
        </head>
        <body>
            <h1>📁 Dossier: {}</h1>
            <table>
                <tr>
                    <th>Nom</th>
                    <th>Type</th>
                    <th>Taille</th>
                    <th>Actions</th>
                </tr>
        """.format(file_path, file_path)
        
        import html as html_module
        for idx, file in enumerate(files):
            icon = "📁" if file["type"] == "directory" else "📄"
            size_str = f"{file['size_mb']} MB" if file["type"] == "file" else "-"
            delete_url = f"/output/{file_path}/{file['name']}" if file_path else f"/output/{file['name']}"
            escaped_name = html_module.escape(file['name'])
            escaped_url = html_module.escape(delete_url)
            html += f"""
                <tr data-idx="{idx}">
                    <td>{icon} <a href="{file['url']}" class="{file['type']}">{escaped_name}</a></td>
                    <td>{file['type']}</td>
                    <td>{size_str}</td>
                    <td>
                        <button class="delete-btn" data-url="{escaped_url}" data-name="{escaped_name}" data-idx="{idx}">🗑️ Supprimer</button>
                    </td>
                </tr>
            """
        
        html += """
            </table>
            <script>
                document.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', async function() {
                        const url = this.dataset.url;
                        const name = this.dataset.name;
                        const idx = this.dataset.idx;
                        
                        if (!confirm('Êtes-vous sûr de vouloir supprimer "' + name + '" ?')) {
                            return;
                        }
                        
                        this.disabled = true;
                        this.textContent = '⏳ Suppression...';
                        
                        try {
                            const response = await fetch(url, {
                                method: 'DELETE'
                            });
                            
                            if (response.ok) {
                                const row = document.querySelector('tr[data-idx="' + idx + '"]');
                                if (row) {
                                    row.style.opacity = '0.5';
                                    row.style.textDecoration = 'line-through';
                                }
                                this.textContent = '✓ Supprimé';
                                setTimeout(() => {
                                    location.reload();
                                }, 500);
                            } else {
                                const data = await response.json();
                                alert('Erreur: ' + (data.detail || 'Erreur inconnue'));
                                this.disabled = false;
                                this.textContent = '🗑️ Supprimer';
                            }
                        } catch (error) {
                            alert('Erreur: ' + error.message);
                            this.disabled = false;
                            this.textContent = '🗑️ Supprimer';
                        }
                    });
                });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    
    # Si c'est un fichier, le servir
    if full_path.exists() and full_path.is_file():
        # Déterminer le media_type selon l'extension
        filename = full_path.name
        if filename.endswith('.txt'):
            media_type = 'text/plain; charset=utf-8'
        elif filename.endswith('.json'):
            media_type = 'application/json; charset=utf-8'
        elif filename.endswith('.mp4'):
            media_type = 'video/mp4'
        elif filename.endswith('.webm'):
            media_type = 'video/webm'
        else:
            media_type = 'application/octet-stream'
        
        # Désactiver le cache pour les vidéos (nosilence.mp4 change souvent)
        headers = {}
        if filename.endswith('.mp4') or filename.endswith('.webm'):
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        
        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            filename=filename,
            headers=headers
        )
    raise HTTPException(status_code=404, detail="Fichier ou dossier non trouvé")


@app.delete("/output/{file_path:path}")
async def delete_output_file(file_path: str):
    """Supprimer un fichier ou un dossier"""
    full_path = OUTPUT_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Fichier ou dossier non trouvé")
    
    try:
        if full_path.is_dir():
            shutil.rmtree(full_path)
            return {"success": True, "message": f"Dossier {file_path} supprimé"}
        else:
            full_path.unlink()
            return {"success": True, "message": f"Fichier {file_path} supprimé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


# Services
video_merger = VideoMerger()
transcription_service = TranscriptionService()
openrouter_service = OpenRouterService()


# ===== NORMALISATION VIDÉO =====
def get_video_duration(video_path: str) -> float:
    """Obtenir la durée d'une vidéo avec ffprobe"""
    import subprocess
    try:
        cmd = [
            video_merger.ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0.0


async def normalize_video_files(screen_path: Path, webcam_path: Path, video_folder: Path) -> tuple:
    """
    Normalise les fichiers vidéo pour avoir :
    - Même durée (la plus courte)
    - 60fps CFR constant
    - Formats compatibles
    
    Retourne: (screen_mp4_path, webcam_mp4_path)
    """
    import subprocess
    
    print(f"[NORMALIZE] Analyse des fichiers sources...")
    
    # Obtenir les durées
    screen_duration = get_video_duration(str(screen_path))
    webcam_duration = get_video_duration(str(webcam_path)) if webcam_path else 0
    
    print(f"[NORMALIZE] Durée screen: {screen_duration:.2f}s")
    if webcam_path:
        print(f"[NORMALIZE] Durée webcam: {webcam_duration:.2f}s")
    
    # Prendre la durée la plus courte si les deux existent
    if webcam_path and webcam_duration > 0:
        target_duration = min(screen_duration, webcam_duration)
        print(f"[NORMALIZE] Durée cible (min): {target_duration:.2f}s")
    else:
        target_duration = screen_duration
    
    screen_dest = video_folder / "screen.mp4"
    webcam_dest = video_folder / "webcam.mp4" if webcam_path else None
    
    # Convertir screen en 60fps CFR avec durée cible
    print(f"[NORMALIZE] Conversion screen.mp4 (60fps CFR, durée={target_duration:.2f}s)...")
    screen_cmd = [
        video_merger.ffmpeg_path, "-y",
        "-i", str(screen_path),
        "-t", str(target_duration),  # Limiter la durée
        "-r", "60",  # 60fps output
        "-vsync", "cfr",  # Framerate constant
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(screen_dest)
    ]
    result = subprocess.run(screen_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[NORMALIZE] Erreur screen: {result.stderr}")
    else:
        print(f"[NORMALIZE] screen.mp4 créé: {screen_dest.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Convertir webcam en 60fps CFR avec même durée
    if webcam_path:
        print(f"[NORMALIZE] Conversion webcam.mp4 (60fps CFR, durée={target_duration:.2f}s)...")
        webcam_cmd = [
            video_merger.ffmpeg_path, "-y",
            "-i", str(webcam_path),
            "-t", str(target_duration),  # Même durée que screen
            "-r", "60",  # 60fps output
            "-vsync", "cfr",  # Framerate constant
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-movflags", "+faststart",
            str(webcam_dest)
        ]
        result = subprocess.run(webcam_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[NORMALIZE] Erreur webcam: {result.stderr}")
        else:
            print(f"[NORMALIZE] webcam.mp4 créé: {webcam_dest.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Vérifier les durées finales
    final_screen_dur = get_video_duration(str(screen_dest))
    print(f"[NORMALIZE] Durée finale screen: {final_screen_dur:.2f}s")
    if webcam_dest and webcam_dest.exists():
        final_webcam_dur = get_video_duration(str(webcam_dest))
        print(f"[NORMALIZE] Durée finale webcam: {final_webcam_dur:.2f}s")
        print(f"[NORMALIZE] Écart: {abs(final_screen_dur - final_webcam_dur):.3f}s")
    
    return screen_dest, webcam_dest


# ===== TEST DES APIs =====
@app.get("/api/test-apis")
async def test_apis():
    """Teste toutes les APIs configurées"""
    import aiohttp
    import subprocess
    
    results = {}
    
    # Test Groq
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {groq_key}"}
                ) as resp:
                    if resp.status == 200:
                        results["groq"] = {"status": True, "details": f"Clé: {groq_key[:15]}..."}
                    else:
                        results["groq"] = {"status": False, "details": f"Erreur {resp.status}"}
        except Exception as e:
            results["groq"] = {"status": False, "details": str(e)[:50]}
    else:
        results["groq"] = {"status": False, "details": "GROQ_API_KEY non configuré"}
    
    # Test OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {openrouter_key}"}
                ) as resp:
                    if resp.status == 200:
                        results["openrouter"] = {"status": True, "details": f"Clé: {openrouter_key[:15]}..."}
                    else:
                        results["openrouter"] = {"status": False, "details": f"Erreur {resp.status}"}
        except Exception as e:
            results["openrouter"] = {"status": False, "details": str(e)[:50]}
    else:
        results["openrouter"] = {"status": False, "details": "OPENROUTER_API_KEY non configuré"}
    
    # Test Pexels
    pexels_key = os.getenv("PEXELS_API_KEY", "")
    if pexels_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.pexels.com/v1/curated?per_page=1",
                    headers={"Authorization": pexels_key}
                ) as resp:
                    if resp.status == 200:
                        results["pexels"] = {"status": True, "details": f"Clé: {pexels_key[:15]}..."}
                    else:
                        results["pexels"] = {"status": False, "details": f"Erreur {resp.status}"}
        except Exception as e:
            results["pexels"] = {"status": False, "details": str(e)[:50]}
    else:
        results["pexels"] = {"status": False, "details": "PEXELS_API_KEY non configuré"}
    
    # Test Unsplash
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if unsplash_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.unsplash.com/photos/random?client_id={unsplash_key}"
                ) as resp:
                    if resp.status == 200:
                        results["unsplash"] = {"status": True, "details": f"Clé: {unsplash_key[:15]}..."}
                    else:
                        results["unsplash"] = {"status": False, "details": f"Erreur {resp.status}"}
        except Exception as e:
            results["unsplash"] = {"status": False, "details": str(e)[:50]}
    else:
        results["unsplash"] = {"status": False, "details": "UNSPLASH_ACCESS_KEY non configuré"}
    
    # Test FFmpeg
    ffmpeg_path = video_merger.ffmpeg_path
    try:
        result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0] if result.stdout else "OK"
            results["ffmpeg"] = {"status": True, "details": version[:50]}
        else:
            results["ffmpeg"] = {"status": False, "details": "Erreur exécution"}
    except FileNotFoundError:
        results["ffmpeg"] = {"status": False, "details": "FFmpeg non trouvé"}
    except Exception as e:
        results["ffmpeg"] = {"status": False, "details": str(e)[:50]}
    
    return results


class MergeRequest(BaseModel):
    layout: str = "overlay"  # overlay, side_by_side
    webcam_x: int = 50
    webcam_y: int = 50
    webcam_size: int = 300
    webcam_shape: str = "circle"


class TranscriptionResponse(BaseModel):
    text: str
    segments: list
    language: str


@app.get("/")
async def root():
    return {"status": "ok", "message": "YouTube Pipeline API v2.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "ffmpeg": video_merger.check_ffmpeg()}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload une vidéo temporaire"""
    try:
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix or ".webm"
        file_path = UPLOAD_DIR / f"{file_id}{ext}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": f"{file_id}{ext}",
            "path": str(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def transcribe_merged_video(video_path: Path, output_filename: str):
    """Fonction de transcription en arrière-plan pour la vidéo fusionnée"""
    try:
        print(f"[TRANSCRIBE_BG] Démarrage transcription de {video_path}")
        
        # Attendre que le fichier soit complètement écrit
        import time
        max_wait = 30  # Attendre max 30 secondes
        waited = 0
        while not video_path.exists() or video_path.stat().st_size == 0:
            if waited >= max_wait:
                print(f"[TRANSCRIBE_BG] Timeout: fichier non disponible après {max_wait}s")
                return
            time.sleep(0.5)
            waited += 0.5
        
        # Attendre encore un peu pour être sûr que le fichier est complètement écrit
        time.sleep(2)
        
        # Transcrire la vidéo fusionnée
        result = await transcription_service.transcribe(
            video_path=str(video_path),
            language="fr"
        )
        
        # Générer les métadonnées SEO avec OpenRouter
        seo_metadata = None
        if result.get("text"):
            print(f"[TRANSCRIBE_BG] Génération métadonnées SEO avec OpenRouter...")
            segments = result.get("segments", [])
            seo_metadata = await openrouter_service.generate_youtube_seo(
                transcript=result["text"],
                language="fr",
                segments=segments if segments else None
            )
            if seo_metadata:
                print(f"[TRANSCRIBE_BG] Métadonnées SEO générées avec succès")
            else:
                print(f"[TRANSCRIBE_BG] Échec génération métadonnées SEO (peut-être clé API manquante)")
        
        # Sauvegarder la transcription et les métadonnées SEO dans un fichier JSON
        if result.get("text"):
            # output_filename est maintenant le nom du dossier (video_YYYYMMDD_HHMMSS)
            video_folder = OUTPUT_DIR / output_filename
            transcription_json_path = video_folder / "transcription.json"
            
            import json
            transcription_data = {
                "text": result["text"],
                "segments": result.get("segments", []),
                "language": result.get("language", "fr")
            }
            
            # Ajouter les métadonnées SEO si disponibles
            if seo_metadata:
                transcription_data["seo"] = {
                    "summary": seo_metadata.get("summary", []),
                    "title": seo_metadata.get("title", ""),
                    "description": seo_metadata.get("description", ""),
                    "hashtags": seo_metadata.get("hashtags", [])
                }
            
            with open(transcription_json_path, "w", encoding="utf-8") as f:
                json.dump(transcription_data, f, ensure_ascii=False, indent=2)
            
            print(f"[TRANSCRIBE_BG] Transcription et métadonnées sauvegardées: {transcription_json_path}")
        else:
            print(f"[TRANSCRIBE_BG] Aucun texte transcrit")
            
    except Exception as e:
        import traceback
        print(f"[TRANSCRIBE_BG] Erreur: {e}")
        print(traceback.format_exc())


@app.post("/api/merge")
async def merge_videos(
    background_tasks: BackgroundTasks,
    screen_file: UploadFile = File(...),
    webcam_file: UploadFile = File(None),
    layout: str = Form("overlay"),
    webcam_x: int = Form(50),
    webcam_y: int = Form(50),
    webcam_size: int = Form(300),
    webcam_shape: str = Form("circle"),
    webcam_border_color: str = Form("#FFB6C1"),
    webcam_border_width: int = Form(4),
):
    """Fusionner écran + webcam selon le layout et transcrire en parallèle"""
    # Vérifier FFmpeg
    if not video_merger.check_ffmpeg():
        raise HTTPException(
            status_code=500, 
            detail="FFmpeg non disponible. Installez FFmpeg et ajoutez-le au PATH."
        )
    
    print(f"[MERGE] Requête reçue - layout: {layout}, webcam: {webcam_file is not None}")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Créer un dossier pour cette vidéo
        video_folder = OUTPUT_DIR / f"video_{timestamp}"
        video_folder.mkdir(exist_ok=True, parents=True)
        print(f"[MERGE] Dossier créé: {video_folder}")
        folder_name = video_folder.name
        
        # 1. Sauvegarder les fichiers uploadés temporairement
        screen_ext = Path(screen_file.filename).suffix or '.webm'
        screen_temp = UPLOAD_DIR / f"screen_{timestamp}{screen_ext}"
        with open(screen_temp, "wb") as f:
            shutil.copyfileobj(screen_file.file, f)
        print(f"[MERGE] Screen uploadé: {screen_temp} ({screen_temp.stat().st_size / 1024 / 1024:.2f} MB)")
        
        webcam_temp = None
        if webcam_file:
            webcam_ext = Path(webcam_file.filename).suffix or '.webm'
            webcam_temp = UPLOAD_DIR / f"webcam_{timestamp}{webcam_ext}"
            with open(webcam_temp, "wb") as f:
                shutil.copyfileobj(webcam_file.file, f)
            print(f"[MERGE] Webcam uploadé: {webcam_temp} ({webcam_temp.stat().st_size / 1024 / 1024:.2f} MB)")
        
        # 2. Convertir en MP4 60fps et sauvegarder dans le dossier vidéo
        print(f"[MERGE] Conversion en MP4 60fps...")
        screen_path = video_folder / "screen.mp4"
        webcam_path = video_folder / "webcam.mp4" if webcam_temp else None
        
        # Convertir screen
        screen_cmd = [
            video_merger.ffmpeg_path, '-y', '-i', str(screen_temp),
            '-r', '60', '-vsync', 'cfr',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            str(screen_path)
        ]
        proc = await asyncio.create_subprocess_exec(*screen_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.wait()
        print(f"[MERGE] screen.mp4 créé: {screen_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Convertir webcam
        if webcam_temp:
            webcam_cmd = [
                video_merger.ffmpeg_path, '-y', '-i', str(webcam_temp),
                '-r', '60', '-vsync', 'cfr',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-an',  # Pas d'audio sur webcam
                '-movflags', '+faststart',
                str(webcam_path)
            ]
            proc = await asyncio.create_subprocess_exec(*webcam_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            print(f"[MERGE] webcam.mp4 créé: {webcam_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # 3. Nettoyer fichiers temporaires
        screen_temp.unlink(missing_ok=True)
        if webcam_temp:
            webcam_temp.unlink(missing_ok=True)
        
        # 4. Sauvegarder la configuration
        config_path = video_folder / "config.json"
        config_data = {
            "layout": layout,
            "webcam_x": webcam_x,
            "webcam_y": webcam_y,
            "webcam_size": webcam_size,
            "webcam_shape": webcam_shape,
            "border_color": webcam_border_color,
            "border_width": webcam_border_width
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        print(f"[MERGE] config.json sauvegardé")
        
        # 5. Fusionner screen.mp4 + webcam.mp4 → original.mp4
        output_path = video_folder / "original.mp4"
        print(f"[MERGE] Fusion vers: {output_path}")
        
        success = await video_merger.merge(
            screen_path=str(screen_path),
            webcam_path=str(webcam_path) if webcam_path else None,
            output_path=str(output_path),
            layout=layout,
            webcam_x=webcam_x,
            webcam_y=webcam_y,
            webcam_size=webcam_size,
            webcam_shape=webcam_shape,
            border_color=webcam_border_color,
            border_width=webcam_border_width
        )
        
        # Vérifier que le fichier existe
        if success and output_path.exists():
            print(f"[MERGE] original.mp4 créé: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Lancer la transcription en arrière-plan
            print(f"[MERGE] Lancement transcription en arrière-plan...")
            background_tasks.add_task(transcribe_merged_video, output_path, folder_name)
        else:
            print(f"[MERGE] ERREUR: Fusion échouée")
            success = False
        
        if success:
            return {
                "success": True,
                "output_url": f"/output/{folder_name}/original.mp4",
                "filename": folder_name,
                "folder": folder_name,
                "transcription": "en_cours"
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la fusion")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create-project")
async def create_project(
    screen_file: UploadFile = File(...),
    webcam_file: UploadFile = File(None),
    layout: str = Form("overlay"),
    webcam_x: int = Form(50),
    webcam_y: int = Form(50),
    webcam_size: int = Form(300),
    webcam_shape: str = Form("circle"),
    webcam_border_color: str = Form("#FFB6C1"),
    webcam_border_width: int = Form(4),
    auto_process: str = Form("true"),
    layout_switches: str = Form(None),  # JSON des timestamps de switch auto
):
    """
    Créer un projet: sauvegarde les fichiers BRUTS et démarre le pipeline en arrière-plan.
    - Crée le projet MongoDB immédiatement avec statut "uploading"
    - Sauvegarde les fichiers bruts (WebM ou MP4)
    - Retourne immédiatement au frontend
    - La conversion 60fps se fait dans step0_convert (Celery)
    """
    print(f"[CREATE-PROJECT] Nouvelle requête - layout: {layout}, webcam: {webcam_file is not None}")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"video_{timestamp}"
        video_folder = OUTPUT_DIR / folder_name
        video_folder.mkdir(exist_ok=True, parents=True)
        print(f"[CREATE-PROJECT] Dossier créé: {video_folder}")
        
        # Parser les layout_switches si présents (pour le switch auto)
        parsed_layout_switches = []
        if layout_switches:
            try:
                parsed_layout_switches = json.loads(layout_switches)
                print(f"[CREATE-PROJECT] {len(parsed_layout_switches)} switch(es) de layout reçu(s)")
            except json.JSONDecodeError:
                print(f"[CREATE-PROJECT] Erreur parsing layout_switches")
        
        # 1. CRÉER LE PROJET MONGODB IMMÉDIATEMENT avec statut "uploading"
        project_id = None
        config_data = {
            "layout": layout,
            "webcam_x": webcam_x,
            "webcam_y": webcam_y,
            "webcam_size": webcam_size,
            "webcam_shape": webcam_shape,
            "border_color": webcam_border_color,
            "border_width": webcam_border_width,
            "layout_switches": parsed_layout_switches  # Timestamps des switches auto
        }
        
        try:
            from services.database import db
            if db.is_connected():
                project_id = db.create_project(
                    name=f"Projet {timestamp}",
                    folder_name=folder_name,
                    config=config_data,
                    status="uploading"  # Statut initial = upload en cours
                )
                print(f"[CREATE-PROJECT] Projet MongoDB créé: {project_id} (statut: uploading)")
        except Exception as e:
            print(f"[CREATE-PROJECT] Erreur MongoDB (non bloquant): {e}")
        
        # 2. Sauvegarder les fichiers BRUTS (pas de conversion ici!)
        screen_ext = Path(screen_file.filename).suffix or '.webm'
        screen_raw = video_folder / f"screen_raw{screen_ext}"
        with open(screen_raw, "wb") as f:
            shutil.copyfileobj(screen_file.file, f)
        screen_size = screen_raw.stat().st_size / 1024 / 1024
        print(f"[CREATE-PROJECT] Screen brut sauvé: {screen_size:.2f} MB")
        
        # Mettre à jour le statut
        if project_id:
            try:
                db.update_project(project_id, {"status": "uploading", "step_name": f"Upload screen: {screen_size:.1f} MB"})
            except: pass
        
        webcam_raw = None
        if webcam_file:
            webcam_ext = Path(webcam_file.filename).suffix or '.webm'
            webcam_raw = video_folder / f"webcam_raw{webcam_ext}"
            with open(webcam_raw, "wb") as f:
                shutil.copyfileobj(webcam_file.file, f)
            webcam_size = webcam_raw.stat().st_size / 1024 / 1024
            print(f"[CREATE-PROJECT] Webcam brute sauvée: {webcam_size:.2f} MB")
            
            if project_id:
                try:
                    db.update_project(project_id, {"step_name": f"Upload terminé ({screen_size:.1f} + {webcam_size:.1f} MB)"})
                except: pass
        
        # 3. Sauvegarder la configuration
        config_path = video_folder / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        print(f"[CREATE-PROJECT] config.json sauvegardé")
        
        # 4. Mettre à jour le statut avant de lancer le pipeline
        if project_id:
            try:
                db.update_project(project_id, {"status": "converting", "step_name": "En attente de conversion..."})
            except: pass
        
        # 5. Démarrer le pipeline Celery si auto_process activé
        task_id = None
        if auto_process.lower() == "true":
            try:
                from celery import chain
                from tasks import (
                    task_step0_convert, task_step1_merge, task_step2_silence, 
                    task_step3_cut_sources, task_step4_transcribe, task_step5_shorts, 
                    task_step6_broll, task_step7_integrate_broll, task_step8_seo, 
                    task_step9_thumbnail, task_step10_schedule
                )
                
                # Mettre à jour le statut - déjà "converting" depuis plus haut
                if project_id:
                    db.update_project(project_id, {"status": "processing", "current_step": 0})
                
                # Créer la chaîne de tâches avec step0_convert en premier
                # S'arrête à step10 (schedule) - L'utilisateur doit approuver l'upload manuellement
                pipeline = chain(
                    task_step0_convert.s(str(video_folder)),  # Conversion 60fps
                    task_step1_merge.s(),  # Reçoit le résultat de step0
                    task_step2_silence.s(),
                    task_step3_cut_sources.s(),
                    task_step4_transcribe.s(),
                    task_step5_shorts.s(),
                    task_step6_broll.s(),
                    task_step7_integrate_broll.s(),
                    task_step8_seo.s(),
                    task_step9_thumbnail.s(),
                    task_step10_schedule.s(),  # Fin du pipeline auto - upload manuel requis
                )
                
                # Lancer le pipeline
                result = pipeline.apply_async()
                task_id = result.id
                
                # Sauvegarder le task ID
                if project_id:
                    db.update_project(project_id, {"celery_task_id": task_id})
                
                print(f"[CREATE-PROJECT] Pipeline Celery lancé: {task_id} (11 étapes, upload manuel)")
                
            except Exception as e:
                print(f"[CREATE-PROJECT] Erreur Celery (pipeline non lancé): {e}")
                import traceback
                print(traceback.format_exc())
                # En cas d'erreur Celery, on continue quand même
        
        return {
            "success": True,
            "project_id": str(project_id) if project_id else None,
            "folder_name": folder_name,
            "task_id": task_id,
            "message": "Projet créé, pipeline en cours" if task_id else "Projet créé (pipeline manuel requis)"
        }
        
    except Exception as e:
        import traceback
        print(f"[CREATE-PROJECT] Erreur: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/create-composite")
async def create_composite_project(
    combined_file: UploadFile = File(...),
    layout: str = Form("composite"),
    auto_process: str = Form("true"),
):
    """
    Créer un projet depuis un fichier composite (Canvas compositing).
    - Pas besoin de merge, le fichier est déjà combiné
    - Step1 (merge) optimisera juste le fichier avec FFmpeg
    """
    print(f"[CREATE-COMPOSITE] Nouvelle requête - layout: {layout}")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"video_{timestamp}"
        video_folder = OUTPUT_DIR / folder_name
        video_folder.mkdir(exist_ok=True, parents=True)
        print(f"[CREATE-COMPOSITE] Dossier créé: {video_folder}")
        
        # 1. CRÉER LE PROJET MONGODB
        project_id = None
        config_data = {
            "layout": "composite",
            "canvas_compositing": True
        }
        
        try:
            from services.database import db
            if db.is_connected():
                project_id = db.create_project(
                    name=f"Projet {timestamp}",
                    folder_name=folder_name,
                    config=config_data,
                    status="uploading"
                )
                print(f"[CREATE-COMPOSITE] Projet MongoDB créé: {project_id}")
        except Exception as e:
            print(f"[CREATE-COMPOSITE] Erreur MongoDB: {e}")
        
        # 2. Sauvegarder le fichier composite
        combined_ext = Path(combined_file.filename).suffix or '.webm'
        combined_path = video_folder / f"combined{combined_ext}"
        with open(combined_path, "wb") as f:
            shutil.copyfileobj(combined_file.file, f)
        combined_size = combined_path.stat().st_size / 1024 / 1024
        print(f"[CREATE-COMPOSITE] Fichier composite sauvé: {combined_size:.2f} MB")
        
        # 3. Sauvegarder la config
        config_path = video_folder / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        
        # 4. Démarrer le pipeline si auto_process
        task_id = None
        if auto_process.lower() == "true":
            try:
                from celery import chain
                from tasks import (
                    task_step0_convert, task_step1_merge, task_step2_silence, 
                    task_step3_cut_sources, task_step4_transcribe, task_step5_shorts, 
                    task_step6_broll, task_step7_integrate_broll, task_step8_seo, 
                    task_step9_thumbnail, task_step10_schedule
                )
                
                if project_id:
                    db.update_project(project_id, {"status": "processing", "current_step": 0})
                
                # Pour le composite, on skip step0 (pas de conversion nécessaire)
                # On commence directement par step1 qui optimisera le fichier
                # S'arrête à step10 (schedule) - L'utilisateur doit approuver l'upload manuellement
                pipeline = chain(
                    task_step1_merge.s(str(video_folder)),  # Optimise combined.webm
                    task_step2_silence.s(),
                    task_step3_cut_sources.s(),
                    task_step4_transcribe.s(),
                    task_step5_shorts.s(),
                    task_step6_broll.s(),
                    task_step7_integrate_broll.s(),
                    task_step8_seo.s(),
                    task_step9_thumbnail.s(),
                    task_step10_schedule.s(),  # Fin du pipeline auto - upload manuel requis
                )
                
                result = pipeline.apply_async()
                task_id = result.id
                
                if project_id:
                    db.update_project(project_id, {"celery_task_id": task_id})
                
                print(f"[CREATE-COMPOSITE] Pipeline Celery lancé: {task_id} (upload manuel)")
                
            except Exception as e:
                print(f"[CREATE-COMPOSITE] Erreur Celery: {e}")
                import traceback
                print(traceback.format_exc())
        
        return {
            "success": True,
            "project_id": str(project_id) if project_id else None,
            "folder_name": folder_name,
            "task_id": task_id,
            "message": "Projet composite créé, pipeline en cours" if task_id else "Projet créé"
        }
        
    except Exception as e:
        import traceback
        print(f"[CREATE-COMPOSITE] Erreur: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


class OptimizeSEORequest(BaseModel):
    filename: str
    transcript: str
    language: str = "fr"
    segments: Optional[list] = None  # Segments avec timestamps pour chapitrage


@app.post("/api/optimize-seo")
async def optimize_seo(request: OptimizeSEORequest):
    """Optimiser les métadonnées SEO pour YouTube à partir d'une transcription existante"""
    try:
        if not request.transcript:
            raise HTTPException(status_code=400, detail="Transcription manquante")
        
        print(f"[SEO] Optimisation SEO pour {request.filename}")
        
        # Utiliser les segments fournis ou charger depuis le fichier JSON
        segments = request.segments
        if not segments:
            base_name = Path(request.filename).stem
            transcription_json_filename = base_name + ".json"
            transcription_json_path = OUTPUT_DIR / transcription_json_filename
            
            if transcription_json_path.exists():
                try:
                    with open(transcription_json_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        segments = existing_data.get("segments", [])
                        print(f"[SEO] {len(segments)} segments chargés depuis le fichier pour chapitrage")
                except Exception as e:
                    print(f"[SEO] Erreur chargement segments: {e}")
        
        if segments:
            print(f"[SEO] Utilisation de {len(segments)} segments pour générer les chapitres avec timestamps réels")
        
        # Générer les métadonnées SEO optimisées
        try:
            seo_metadata = await openrouter_service.generate_youtube_seo(
                transcript=request.transcript,
                language=request.language,
                segments=segments
            )
        except Exception as e:
            import traceback
            print(f"[SEO] Exception lors de la génération SEO: {e}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors de la génération SEO: {str(e)}"
            )
        
        if not seo_metadata:
            # Vérifier si c'est un problème de configuration
            if not openrouter_service.api_key:
                raise HTTPException(
                    status_code=500, 
                    detail="Clé API OpenRouter non configurée. Ajoutez OPENROUTER_API_KEY dans le fichier .env"
                )
            raise HTTPException(
                status_code=500, 
                detail="Échec génération métadonnées SEO. Vérifiez les logs du serveur pour plus de détails."
            )
        
        # Mettre à jour le fichier JSON existant
        base_name = Path(request.filename).stem
        transcription_json_filename = base_name + ".json"
        transcription_json_path = OUTPUT_DIR / transcription_json_filename
        
        if transcription_json_path.exists():
            # Charger le fichier existant
            with open(transcription_json_path, "r", encoding="utf-8") as f:
                transcription_data = json.load(f)
        else:
            # Créer un nouveau fichier si n'existe pas
            transcription_data = {
                "text": request.transcript,
                "segments": [],
                "language": request.language
            }
        
        # Mettre à jour les métadonnées SEO
        transcription_data["seo"] = seo_metadata
        
        # Sauvegarder
        with open(transcription_json_path, "w", encoding="utf-8") as f:
            json.dump(transcription_data, f, ensure_ascii=False, indent=2)
        
        print(f"[SEO] Métadonnées SEO sauvegardées: {transcription_json_path}")
        
        return {
            "success": True,
            "seo": seo_metadata,
            "transcription_file": transcription_json_filename
        }
        
    except Exception as e:
        import traceback
        print(f"[SEO] Erreur: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe_video(
    file: UploadFile = File(...),
    language: str = Form("fr")
):
    """Transcrire une vidéo et générer les métadonnées SEO"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarder le fichier
        video_path = UPLOAD_DIR / f"transcribe_{timestamp}.mp4"
        with open(video_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Extraire l'audio et transcrire
        result = await transcription_service.transcribe(
            video_path=str(video_path),
            language=language
        )
        
        # Générer les métadonnées SEO avec OpenRouter
        seo_metadata = None
        if result.get("text"):
            print(f"[Transcription] Génération métadonnées SEO avec OpenRouter...")
            segments = result.get("segments", [])
            seo_metadata = await openrouter_service.generate_youtube_seo(
                transcript=result["text"],
                language=language,
                segments=segments if segments else None
            )
            if seo_metadata:
                print(f"[Transcription] Métadonnées SEO générées avec succès")
                result["seo"] = seo_metadata
            else:
                print(f"[Transcription] Échec génération métadonnées SEO (peut-être clé API manquante)")
        
        # Sauvegarder la transcription dans un fichier JSON (texte + segments + SEO)
        if result.get("text"):
            # Extraire le nom du fichier vidéo original depuis le filename
            original_filename = file.filename or "video"
            base_name = Path(original_filename).stem
            transcription_json_filename = base_name + ".json"
            transcription_json_path = OUTPUT_DIR / transcription_json_filename
            
            # Sauvegarder les segments avec timestamps dans un fichier JSON
            import json
            transcription_data = {
                "text": result["text"],
                "segments": result.get("segments", []),
                "language": result.get("language", "fr")
            }
            
            # Ajouter les métadonnées SEO si disponibles
            if seo_metadata:
                transcription_data["seo"] = seo_metadata
            
            with open(transcription_json_path, "w", encoding="utf-8") as f:
                json.dump(transcription_data, f, ensure_ascii=False, indent=2)
            
            print(f"[Transcription] Sauvegardee: {transcription_json_path}")
            result["transcription_file"] = transcription_json_filename
        
        # Nettoyer
        video_path.unlink(missing_ok=True)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert")
async def convert_video(
    file: UploadFile = File(...),
    format: str = Form("mp4"),
    resolution: str = Form("1080p")
):
    """Convertir une vidéo"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarder
        input_path = UPLOAD_DIR / f"convert_{timestamp}.webm"
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Convertir
        output_path = OUTPUT_DIR / f"converted_{timestamp}.{format}"
        success = await video_merger.convert(
            input_path=str(input_path),
            output_path=str(output_path),
            resolution=resolution
        )
        
        # Nettoyer
        input_path.unlink(missing_ok=True)
        
        if success:
            return {
                "success": True,
                "output_url": f"/output/{output_path.name}",
                "filename": output_path.name
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur conversion")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def list_files():
    """Lister les vidéos (dossiers et fichiers standalone)"""
    files = []
    
    # Parcourir les dossiers vidéo (nouveau format: video_YYYYMMDD_HHMMSS)
    for folder in OUTPUT_DIR.glob("video_*"):
        if folder.is_dir():
            try:
                # Chercher tous les fichiers du dossier
                video_file = folder / "original.mp4"
                nosilence_file = folder / "nosilence.mp4"
                transcription_file = folder / "transcription.json"
                screen_file = folder / "screen.mp4"
                webcam_file = folder / "webcam.mp4"
                screen_nosilence_file = folder / "screen_nosilence.mp4"
                webcam_nosilence_file = folder / "webcam_nosilence.mp4"
                
                # Utiliser nosilence si disponible, sinon original
                main_video = nosilence_file if nosilence_file.exists() else video_file
                
                if main_video.exists():
                    stat = main_video.stat()
                    folder_stat = folder.stat()
                    
                    # Vérifier le dossier shorts
                    shorts_dir = folder / "shorts"
                    shorts_list = []
                    if shorts_dir.exists() and shorts_dir.is_dir():
                        for short_file in shorts_dir.glob("*.mp4"):
                            shorts_list.append({
                                "name": short_file.name,
                                "path": f"/output/{folder.name}/shorts/{short_file.name}",
                                "size": short_file.stat().st_size
                            })
                    
                    video_info = {
                        "name": folder.name,
                        "size": stat.st_size,
                        "url": f"/output/{folder.name}/{main_video.name}",
                        "created": datetime.fromtimestamp(folder_stat.st_ctime).isoformat(),
                        "folder": folder.name,
                        "has_original": video_file.exists(),
                        "has_nosilence": nosilence_file.exists(),
                        "has_transcription": transcription_file.exists(),
                        "has_screen": screen_file.exists(),
                        "has_webcam": webcam_file.exists(),
                        "has_screen_nosilence": screen_nosilence_file.exists(),
                        "has_webcam_nosilence": webcam_nosilence_file.exists(),
                        "has_shorts": len(shorts_list) > 0,
                        "shorts": shorts_list
                    }
                    files.append(video_info)
            except Exception as e:
                print(f"[API/files] Erreur dossier {folder.name}: {e}")
                continue
    
    # Compatibilité: Parcourir aussi les fichiers MP4 standalone (ancien format)
    for f in OUTPUT_DIR.glob("*.mp4"):
        if f.is_file():
            try:
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "url": f"/output/{f.name}",
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "folder": None,
                    "has_original": True,
                    "has_nosilence": False,
                    "has_transcription": (OUTPUT_DIR / f"{f.stem}.json").exists()
                })
            except Exception as e:
                print(f"[API/files] Erreur fichier {f.name}: {e}")
                continue
    
    print(f"[API/files] {len(files)} vidéo(s) trouvée(s)")
    return {"files": sorted(files, key=lambda x: x["created"], reverse=True)}


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Supprimer un fichier ou dossier vidéo"""
    file_path = OUTPUT_DIR / filename
    
    if file_path.exists():
        if file_path.is_dir():
            # Supprimer le dossier et tout son contenu
            shutil.rmtree(file_path)
            print(f"[API/files] Dossier supprimé: {filename}")
        else:
            # Supprimer le fichier et son JSON associé
            file_path.unlink()
            json_path = OUTPUT_DIR / f"{Path(filename).stem}.json"
            if json_path.exists():
                json_path.unlink()
            print(f"[API/files] Fichier supprimé: {filename}")
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="Fichier non trouvé")


class RepositionWebcamRequest(BaseModel):
    folder_name: str
    webcam_x: int = 50
    webcam_y: int = 50
    webcam_size: int = 300
    webcam_shape: str = "circle"  # circle ou rectangle
    border_thickness: int = 4  # Épaisseur du bord (0-20)
    border_color: str = "ec4899"  # Couleur du bord (hex sans #)


@app.post("/api/reposition-webcam")
async def reposition_webcam(request: RepositionWebcamRequest):
    """Repositionner la webcam sur l'écran et refusionner"""
    import subprocess
    
    folder_path = OUTPUT_DIR / request.folder_name
    
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Dossier vidéo non trouvé")
    
    screen_path = folder_path / "screen_nosilence.mp4"
    webcam_path = folder_path / "webcam_nosilence.mp4"
    output_path = folder_path / "nosilence.mp4"
    
    if not screen_path.exists():
        raise HTTPException(status_code=404, detail="screen_nosilence.mp4 non trouvé")
    if not webcam_path.exists():
        raise HTTPException(status_code=404, detail="webcam_nosilence.mp4 non trouvé")
    
    print(f"[REPOSITION] Repositionnement webcam dans {request.folder_name}")
    print(f"[REPOSITION] Position: x={request.webcam_x}, y={request.webcam_y}, taille={request.webcam_size}, forme={request.webcam_shape}")
    print(f"[REPOSITION] Bordure: {request.border_thickness}px, couleur=#{request.border_color}")
    
    try:
        ffmpeg_path = video_merger.ffmpeg_path
        
        # Supprimer l'ancien fichier si existe
        if output_path.exists():
            output_path.unlink()
        
        # Paramètres de bordure
        border_size = request.border_thickness
        border_color = request.border_color.replace("#", "")  # Enlever le # si présent
        inner_size = request.webcam_size - (border_size * 2)
        
        # S'assurer que inner_size est positif
        if inner_size < 10:
            inner_size = request.webcam_size - 4
            border_size = 2
        
        # Pré-redimensionner l'écran et la webcam à une résolution maximale raisonnable
        # pour éviter les problèmes avec les très hautes résolutions
        # L'écran est redimensionné à 1920x1080 max (résolution finale)
        # La webcam est redimensionnée à 1280x720 max avant traitement
        # IMPORTANT: On ajoute fps=60 pour forcer le framerate comme dans video_merger.py
        screen_pre_scale = "scale=1920:1080:force_original_aspect_ratio=decrease,fps=60"
        webcam_pre_scale = "scale=1280:720:force_original_aspect_ratio=decrease,fps=60,"
        
        if request.webcam_shape == "circle":
            if border_size > 0:
                # Webcam circulaire avec bordure
                filter_complex = (
                    # Écran pré-redimensionné + fps=60
                    f"[0:v]{screen_pre_scale}[screen_scaled];"
                    # Bordure circulaire
                    f"color=c=0x{border_color}:s={request.webcam_size}x{request.webcam_size}:d=1[border];"
                    f"[border]format=rgba,geq=lum='p(X,Y)':a='if(gt(pow(X-W/2,2)+pow(Y-H/2,2),pow(W/2,2)),0,255)'[border_circle];"
                    
                    # Webcam circulaire (avec pré-scale + fps=60)
                    f"[1:v]{webcam_pre_scale}scale={inner_size}:{inner_size}:force_original_aspect_ratio=increase,"
                    f"crop={inner_size}:{inner_size},"
                    f"format=rgba,"
                    f"geq=lum='p(X,Y)':a='if(gt(pow(X-W/2,2)+pow(Y-H/2,2),pow(W/2,2)),0,255)'[webcam_circle];"
                    
                    # Superposer webcam sur bordure
                    f"[border_circle][webcam_circle]overlay={border_size}:{border_size}[webcam_with_border];"
                    
                    # Superposer sur l'écran
                    f"[screen_scaled][webcam_with_border]overlay={request.webcam_x}:{request.webcam_y}[out]"
                )
            else:
                # Sans bordure - juste la webcam circulaire (avec pré-scale + fps=60)
                filter_complex = (
                    # Écran pré-redimensionné + fps=60
                    f"[0:v]{screen_pre_scale}[screen_scaled];"
                    # Webcam circulaire (avec pré-scale + fps=60)
                    f"[1:v]{webcam_pre_scale}scale={request.webcam_size}:{request.webcam_size}:force_original_aspect_ratio=increase,"
                    f"crop={request.webcam_size}:{request.webcam_size},"
                    f"format=rgba,"
                    f"geq=lum='p(X,Y)':a='if(gt(pow(X-W/2,2)+pow(Y-H/2,2),pow(W/2,2)),0,255)'[webcam_circle];"
                    f"[screen_scaled][webcam_circle]overlay={request.webcam_x}:{request.webcam_y}[out]"
                )
        else:
            # Rectangulaire
            if border_size > 0:
                filter_complex = (
                    # Écran pré-redimensionné + fps=60
                    f"[0:v]{screen_pre_scale}[screen_scaled];"
                    # Bordure
                    f"color=c=0x{border_color}:s={request.webcam_size}x{request.webcam_size}:d=1[border];"
                    
                    # Webcam (avec pré-scale + fps=60)
                    f"[1:v]{webcam_pre_scale}scale={inner_size}:{inner_size}:force_original_aspect_ratio=increase,"
                    f"crop={inner_size}:{inner_size}[webcam_scaled];"
                    
                    # Superposer
                    f"[border][webcam_scaled]overlay={border_size}:{border_size}[webcam_with_border];"
                    f"[screen_scaled][webcam_with_border]overlay={request.webcam_x}:{request.webcam_y}[out]"
                )
            else:
                # Sans bordure (avec pré-scale + fps=60)
                filter_complex = (
                    # Écran pré-redimensionné + fps=60
                    f"[0:v]{screen_pre_scale}[screen_scaled];"
                    # Webcam (avec pré-scale + fps=60)
                    f"[1:v]{webcam_pre_scale}scale={request.webcam_size}:{request.webcam_size}:force_original_aspect_ratio=increase,"
                    f"crop={request.webcam_size}:{request.webcam_size}[webcam_scaled];"
                    f"[screen_scaled][webcam_scaled]overlay={request.webcam_x}:{request.webcam_y}[out]"
                )
        
        # Commande FFmpeg pour fusionner avec optimisations performance
        merge_cmd = [
            ffmpeg_path, "-y",
            "-i", str(screen_path),
            "-r", "60",  # Forcer lecture webcam à 30 fps (important pour VFR)
            "-i", str(webcam_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",  # Audio de l'écran si présent
            "-c:v", "libx264", 
            "-preset", "fast", 
            "-crf", "18",
            "-maxrate", "8M",  # Limiter le bitrate max pour éviter le lag
            "-bufsize", "16M",  # Buffer pour le bitrate
            "-threads", "0",  # Utiliser tous les threads disponibles
            "-vsync", "cfr",  # Framerate constant en sortie
            "-c:a", "aac", 
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        print(f"[REPOSITION] Exécution FFmpeg...")
        print(f"[REPOSITION] Commande: {' '.join(merge_cmd[:6])}...")
        result = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            error_msg = result.stderr[-1000:] if result.stderr else "Aucun message d'erreur"
            print(f"[REPOSITION] Erreur FFmpeg (code {result.returncode}):")
            print(f"[REPOSITION] {error_msg}")
            # Essayer d'extraire un message d'erreur plus spécifique
            if "resolution" in error_msg.lower() or "size" in error_msg.lower():
                raise HTTPException(
                    status_code=500, 
                    detail=f"Erreur de résolution lors de la fusion. Vérifiez que les fichiers vidéo sont valides. Détails: {error_msg[-200:]}"
                )
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors de la fusion FFmpeg: {error_msg[-300:]}"
            )
        
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Fichier de sortie non créé")
        
        output_size = output_path.stat().st_size
        print(f"[REPOSITION] Fichier créé: {output_path} ({output_size} bytes)")
        
        return {
            "success": True,
            "output_url": f"/output/{request.folder_name}/nosilence.mp4",
            "size": output_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REPOSITION] Erreur: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class SilenceSegment(BaseModel):
    start: float
    end: float

class RemoveSilencesRequest(BaseModel):
    filename: str
    detected_silences: Optional[List[SilenceSegment]] = None  # Silences détectés côté client
    video_duration: Optional[float] = None  # Durée de la vidéo
    # Fallback si pas de silences fournis
    silence_threshold: float = -40  # dB
    min_silence_duration: float = 0.5  # secondes


@app.post("/api/remove-silences")
async def remove_silences(request: RemoveSilencesRequest):
    """Supprimer les silences d'une vidéo avec FFmpeg"""
    import subprocess
    import re
    
    # Déterminer le chemin d'entrée (dossier ou fichier)
    base_path = OUTPUT_DIR / request.filename
    is_folder = base_path.is_dir()
    
    if is_folder:
        # Nouveau format: dossier vidéo
        input_path = base_path / "original.mp4"
        output_folder = base_path
    else:
        # Ancien format: fichier standalone
        input_path = base_path
        output_folder = OUTPUT_DIR
    
    print(f"[REMOVE_SILENCES] Fichier d'entrée: {input_path.absolute()}")
    print(f"[REMOVE_SILENCES] Dossier de sortie: {output_folder.absolute()}")
    
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Fichier vidéo non trouvé")
    
    # Utiliser le même chemin FFmpeg que VideoMerger
    video_merger = VideoMerger()
    ffmpeg_path = video_merger.ffmpeg_path
    
    # Calculer le chemin ffprobe (dans le même dossier que ffmpeg)
    ffmpeg_dir = Path(ffmpeg_path).parent
    ffprobe_path = str(ffmpeg_dir / "ffprobe.exe")
    
    # Vérifier que ffprobe existe
    if not Path(ffprobe_path).exists():
        print(f"[REMOVE_SILENCES] ERREUR: ffprobe non trouvé à {ffprobe_path}")
        raise HTTPException(status_code=500, detail=f"ffprobe non trouvé à {ffprobe_path}")
    
    print(f"[REMOVE_SILENCES] FFmpeg: {ffmpeg_path}")
    print(f"[REMOVE_SILENCES] FFprobe: {ffprobe_path}")
    
    try:
        # Obtenir la durée totale de la vidéo
        probe_cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_path)
        ]
        duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        total_duration = float(duration_result.stdout.strip())
        
        # Utiliser les silences envoyés par le frontend (zones ROUGES)
        if request.detected_silences and len(request.detected_silences) > 0:
            silences = [(s.start, s.end) for s in request.detected_silences]
            print(f"[REMOVE_SILENCES] ======================================")
            print(f"[REMOVE_SILENCES] ZONES ROUGES À SUPPRIMER ({len(silences)}):")
            print(f"[REMOVE_SILENCES] ======================================")
            for i, (s, e) in enumerate(silences):
                print(f"  🔴 ROUGE {i}: {s:.2f}s → {e:.2f}s (durée: {e-s:.2f}s) - SERA COUPÉ")
        else:
            print(f"[REMOVE_SILENCES] Aucune zone rouge reçue, détection FFmpeg...")
            detect_cmd = [
                ffmpeg_path, "-i", str(input_path),
                "-af", f"silencedetect=noise={request.silence_threshold}dB:d={request.min_silence_duration}",
                "-f", "null", "-"
            ]
            result = subprocess.run(detect_cmd, capture_output=True, text=True)
            stderr = result.stderr
            silence_starts = re.findall(r"silence_start: ([\d.]+)", stderr)
            silence_ends = re.findall(r"silence_end: ([\d.]+)", stderr)
            min_len = min(len(silence_starts), len(silence_ends))
            silences = list(zip(
                [float(s) for s in silence_starts[:min_len]],
                [float(e) for e in silence_ends[:min_len]]
            ))
            print(f"[REMOVE_SILENCES] {len(silences)} silence(s) détecté(s) par FFmpeg")
        
        if len(silences) == 0:
            return {
                "success": True,
                "message": "Aucun silence détecté",
                "output_filename": request.filename,
                "silences_removed": 0
            }
        
        # Étape 2: Construire les segments non-silencieux (les parties à GARDER)
        segments = []
        current_pos = 0.0
        
        print(f"[REMOVE_SILENCES] ======================================")
        print(f"[REMOVE_SILENCES] SEGMENTS VERTS À GARDER:")
        print(f"[REMOVE_SILENCES] ======================================")
        
        for silence_start, silence_end in silences:
            # Le segment avant ce silence (s'il y en a un)
            if silence_start > current_pos + 0.01:  # Ajouter une petite marge
                segment = (current_pos, silence_start)
                segments.append(segment)
                print(f"  🟢 GARDER: {current_pos:.2f}s → {silence_start:.2f}s (durée: {silence_start - current_pos:.2f}s)")
            current_pos = silence_end
        
        # Ajouter le segment final si nécessaire
        if current_pos < total_duration - 0.01:
            segment = (current_pos, total_duration)
            segments.append(segment)
            print(f"  🟢 GARDER (fin): {current_pos:.2f}s → {total_duration:.2f}s (durée: {total_duration - current_pos:.2f}s)")
        
        if len(segments) == 0:
            return {
                "success": True,
                "message": "Vidéo entièrement silencieuse",
                "output_filename": request.filename,
                "silences_removed": len(silences)
            }
        
        # Filtrer les segments avec une durée minimum de 0.1s
        valid_segments_to_extract = [(start, end) for start, end in segments if (end - start) >= 0.1]
        print(f"[REMOVE_SILENCES] {len(valid_segments_to_extract)}/{len(segments)} segment(s) valides à extraire (durée >= 0.1s)")
        
        if len(valid_segments_to_extract) == 0:
            return {
                "success": True,
                "message": "Tous les segments sont trop courts, vidéo non modifiée",
                "output_filename": request.filename,
                "silences_removed": len(silences)
            }
        
        # Calculer la durée attendue
        expected_duration = sum(end - start for start, end in valid_segments_to_extract)
        print(f"[REMOVE_SILENCES] Durée attendue après suppression: {expected_duration:.2f}s")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Étape 3: Extraire chaque segment NON-silencieux
        temp_segments = []
        
        for i, (start, end) in enumerate(valid_segments_to_extract):
            duration = end - start
            segment_file = UPLOAD_DIR / f"segment_{timestamp}_{i}.mp4"
            temp_segments.append(segment_file)
            
            # Extraire le segment avec ré-encodage pour garantir la compatibilité
            extract_cmd = [
                ffmpeg_path, "-y",
                "-i", str(input_path),
                "-ss", str(start),
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                str(segment_file)
            ]
            
            print(f"[REMOVE_SILENCES] Extraction segment {i}: {start:.2f}s → {end:.2f}s ({duration:.2f}s)")
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[REMOVE_SILENCES] ERREUR segment {i}: {result.stderr[-300:]}")
            elif segment_file.exists():
                print(f"[REMOVE_SILENCES] Segment {i} OK: {segment_file.stat().st_size} bytes")
            else:
                print(f"[REMOVE_SILENCES] ERREUR: segment {i} non créé")
        
        # Vérifier les segments créés
        valid_segments = [seg for seg in temp_segments if seg.exists() and seg.stat().st_size > 1000]
        print(f"[REMOVE_SILENCES] {len(valid_segments)}/{len(temp_segments)} segments valides créés")
        
        if len(valid_segments) == 0:
            for seg in temp_segments:
                seg.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="Aucun segment valide extrait")
        
        # Étape 4: Créer le fichier de concat
        concat_file = UPLOAD_DIR / f"concat_{timestamp}.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in valid_segments:
                # Utiliser des chemins avec forward slashes pour FFmpeg
                f.write(f"file '{str(seg.absolute()).replace(chr(92), '/')}'\n")
        
        print(f"[REMOVE_SILENCES] Fichier concat créé: {concat_file}")
        
        # Étape 5: Créer le fichier de sortie
        if is_folder:
            output_filename = "nosilence.mp4"
            output_path = output_folder / output_filename
            output_url = f"/output/{request.filename}/nosilence.mp4"
            result_filename = request.filename
            if output_path.exists():
                print(f"[REMOVE_SILENCES] Suppression du fichier existant: {output_path}")
                output_path.unlink()  # Supprimer explicitement avant de recréer
        else:
            output_filename = f"nosilence_{timestamp}.mp4"
            output_path = OUTPUT_DIR / output_filename
            output_url = f"/output/{output_filename}"
            result_filename = output_filename
        
        # Étape 6: Concaténer tous les segments avec ré-encodage complet
        # (évite les problèmes de métadonnées/durée incorrecte)
        print(f"[REMOVE_SILENCES] Concaténation de {len(valid_segments)} segments avec ré-encodage...")
        
        concat_cmd = [
            ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",  # Métadonnées au début du fichier
            str(output_path)
        ]
        
        concat_result = subprocess.run(concat_cmd, capture_output=True, text=True)
        
        if concat_result.returncode != 0:
            print(f"[REMOVE_SILENCES] ERREUR concat: {concat_result.stderr[-500:]}")
            # Fallback sans movflags
            print(f"[REMOVE_SILENCES] Tentative sans movflags...")
            concat_cmd = [
                ffmpeg_path, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                str(output_path)
            ]
            concat_result = subprocess.run(concat_cmd, capture_output=True, text=True)
            if concat_result.returncode != 0:
                print(f"[REMOVE_SILENCES] ERREUR concat ré-encodage: {concat_result.stderr[-500:]}")
        
        # Nettoyer les fichiers temporaires
        concat_file.unlink(missing_ok=True)
        for seg in temp_segments:
            seg.unlink(missing_ok=True)
        print(f"[REMOVE_SILENCES] Fichiers temporaires nettoyés")
        
        # Vérifier que le fichier de sortie existe
        if not output_path.exists():
            print(f"[REMOVE_SILENCES] ERREUR: Fichier de sortie non créé: {output_path}")
            raise HTTPException(status_code=500, detail="Erreur lors de la création du fichier sans silences")
        
        output_size = output_path.stat().st_size
        print(f"[REMOVE_SILENCES] Fichier créé: {output_path} ({output_size} bytes)")
        
        # Calculer la nouvelle durée
        probe_cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output_path)
        ]
        new_duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        new_duration = float(new_duration_result.stdout.strip()) if new_duration_result.stdout.strip() else 0
        
        print(f"[REMOVE_SILENCES] Terminé: {total_duration:.1f}s → {new_duration:.1f}s (attendu: {expected_duration:.1f}s)")
        
        # Étape 7: Couper les mêmes silences sur screen.mp4 et webcam.mp4 si présents
        screen_path = output_folder / "screen.mp4"
        webcam_path = output_folder / "webcam.mp4"
        
        for source_name, source_path in [("screen", screen_path), ("webcam", webcam_path)]:
            if source_path.exists():
                print(f"[REMOVE_SILENCES] Traitement de {source_name}.mp4...")
                
                # Extraire les segments
                source_segments = []
                source_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                
                for i, (start, end) in enumerate(valid_segments_to_extract):
                    duration = end - start
                    segment_file = UPLOAD_DIR / f"{source_name}_segment_{source_timestamp}_{i}.mp4"
                    source_segments.append(segment_file)
                    
                    extract_cmd = [
                        ffmpeg_path, "-y",
                        "-i", str(source_path),
                        "-ss", str(start),
                        "-t", str(duration),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k",
                        "-avoid_negative_ts", "make_zero",
                        str(segment_file)
                    ]
                    subprocess.run(extract_cmd, capture_output=True, text=True)
                
                # Vérifier les segments valides
                valid_source_segments = [s for s in source_segments if s.exists() and s.stat().st_size > 1000]
                
                if len(valid_source_segments) > 0:
                    # Créer le fichier concat
                    source_concat_file = UPLOAD_DIR / f"{source_name}_concat_{source_timestamp}.txt"
                    with open(source_concat_file, "w", encoding="utf-8") as f:
                        for seg in valid_source_segments:
                            f.write(f"file '{str(seg.absolute()).replace(chr(92), '/')}'\n")
                    
                    # Concaténer
                    output_nosilence_path = output_folder / f"{source_name}_nosilence.mp4"
                    concat_cmd = [
                        ffmpeg_path, "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(source_concat_file),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart",
                        str(output_nosilence_path)
                    ]
                    subprocess.run(concat_cmd, capture_output=True, text=True)
                    
                    if output_nosilence_path.exists():
                        print(f"[REMOVE_SILENCES] {source_name}_nosilence.mp4 créé: {output_nosilence_path.stat().st_size} bytes")
                    
                    # Nettoyer
                    source_concat_file.unlink(missing_ok=True)
                
                # Nettoyer les segments
                for seg in source_segments:
                    seg.unlink(missing_ok=True)
        
        # Étape 8: Extraire l'audio et retranscrire le fichier nosilence
        print(f"[REMOVE_SILENCES] Extraction audio de nosilence.mp4...")
        
        audio_path = output_folder / "nosilence_audio.mp3"
        extract_audio_cmd = [
            ffmpeg_path, "-y",
            "-i", str(output_path),
            "-vn",  # Pas de vidéo
            "-acodec", "libmp3lame",
            "-ar", "16000",  # 16kHz pour Whisper
            "-ac", "1",  # Mono
            "-b:a", "64k",
            str(audio_path)
        ]
        
        audio_result = subprocess.run(extract_audio_cmd, capture_output=True, text=True)
        
        if audio_result.returncode == 0 and audio_path.exists():
            print(f"[REMOVE_SILENCES] Audio extrait: {audio_path} ({audio_path.stat().st_size} bytes)")
            
            # Transcrire avec Groq (fonction async)
            try:
                print(f"[REMOVE_SILENCES] Transcription en cours...")
                transcription_result = await transcription_service.transcribe(str(audio_path))
                
                if transcription_result:
                    print(f"[REMOVE_SILENCES] Transcription réussie: {len(transcription_result.get('segments', []))} segments")
                    
                    # Générer SEO
                    from services.openrouter import OpenRouterService
                    openrouter = OpenRouterService()
                    
                    seo_data = await openrouter.generate_youtube_seo(
                        transcription_result.get('text', ''),
                        transcription_result.get('segments', [])
                    )
                    
                    # Sauvegarder la transcription
                    transcription_file = output_folder / "transcription.json"
                    transcription_data = {
                        "filename": "nosilence.mp4",
                        "text": transcription_result.get('text', ''),
                        "segments": transcription_result.get('segments', []),
                        "seo": seo_data,
                        "source": "nosilence"
                    }
                    
                    with open(transcription_file, 'w', encoding='utf-8') as f:
                        json.dump(transcription_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"[REMOVE_SILENCES] Transcription sauvegardée: {transcription_file}")
                else:
                    print(f"[REMOVE_SILENCES] Échec transcription")
            except Exception as e:
                print(f"[REMOVE_SILENCES] Erreur transcription: {e}")
            
            # Nettoyer l'audio temporaire
            audio_path.unlink(missing_ok=True)
        else:
            print(f"[REMOVE_SILENCES] Erreur extraction audio: {audio_result.stderr[-300:] if audio_result.stderr else 'Unknown'}")
        
        return {
            "success": True,
            "output_filename": result_filename,
            "output_url": output_url,
            "original_duration": total_duration,
            "new_duration": new_duration,
            "silences_removed": len(silences),
            "time_saved": total_duration - new_duration,
            "is_folder": is_folder,
            "transcription_updated": True
        }
        
    except Exception as e:
        print(f"[REMOVE_SILENCES] Erreur: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# SHORTS - Génération de shorts YouTube/TikTok
# =============================================

class GenerateShortsRequest(BaseModel):
    folder_name: str
    # Segments avec timestamps (optionnel si transcription existe)
    segments: Optional[List[dict]] = None


@app.post("/api/generate-shorts")
async def generate_shorts_suggestions(request: GenerateShortsRequest):
    """Analyser la transcription et suggérer des shorts"""
    
    folder_path = OUTPUT_DIR / request.folder_name
    
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Dossier vidéo non trouvé")
    
    print(f"[SHORTS] Génération suggestions pour {request.folder_name}")
    
    # Charger la transcription si segments non fournis
    segments = request.segments
    video_duration = 0
    
    if not segments:
        transcription_path = folder_path / "transcription.json"
        if transcription_path.exists():
            with open(transcription_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                segments = data.get("segments", [])
                video_duration = data.get("duration", 0)
                print(f"[SHORTS] Transcription chargée: {len(segments)} segments, {video_duration:.1f}s")
        else:
            raise HTTPException(status_code=404, detail="Transcription non trouvée")
    
    # Calculer la durée si pas fournie
    if video_duration == 0 and segments:
        video_duration = max(seg.get("end", 0) for seg in segments)
    
    if not segments or len(segments) == 0:
        raise HTTPException(status_code=400, detail="Aucun segment de transcription")
    
    try:
        # Utiliser OpenRouter pour analyser et suggérer des shorts
        shorts = await openrouter_service.generate_shorts_suggestions(
            segments=segments,
            video_duration=video_duration,
            language="fr"
        )
        
        if shorts is None:
            raise HTTPException(status_code=500, detail="Erreur lors de la génération des suggestions")
        
        print(f"[SHORTS] {len(shorts)} short(s) suggéré(s)")
        
        return {
            "success": True,
            "shorts": shorts,
            "video_duration": video_duration,
            "total_segments": len(segments)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SHORTS] Erreur: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class CreateShortRequest(BaseModel):
    folder_name: str
    start: float  # Début du short en secondes
    end: float  # Fin du short en secondes
    title: str = "short"  # Titre pour le nom du fichier


def generate_karaoke_ass(segments: list, start_time: float, end_time: float, output_path: str):
    """
    Générer un fichier ASS avec sous-titres karaoké (highlight mot par mot)
    - 1 seule ligne centrée avec 2 mots max
    - Police GRANDE (100px)
    - Centré au milieu exact du short (960px sur 1920px)
    - Highlight jaune vif
    - Contour épais pour lisibilité
    - Marges de 60px à gauche et droite pour éviter le crop
    """
    # Header ASS
    # PrimaryColour = couleur AVANT highlight (blanc)
    # SecondaryColour = couleur highlight karaoké (jaune vif)
    # Fontsize = 100 pour GRANDE visibilité
    # Outline = 7 pour contour épais
    # Shadow = 4 pour ombre
    # MarginL/MarginR = 60 pour éviter le crop sur les bords
    ass_content = """[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,120,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,4,5,60,60,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_ass_time(seconds: float) -> str:
        """Formater le temps en format ASS (H:MM:SS.cc)"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    
    # Durée du short
    short_duration = end_time - start_time
    
    # Filtrer les segments dans la plage temporelle ET couper les mots qui dépassent
    relevant_words = []  # Liste de (mot, start_relatif, end_relatif)
    
    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        
        # Vérifier si le segment touche la plage
        if seg_end > start_time and seg_start < end_time:
            words = seg.get("text", "").strip().split()
            if not words:
                continue
            
            # Durée originale par mot
            orig_seg_duration = seg_end - seg_start
            word_duration = orig_seg_duration / len(words) if words else orig_seg_duration
            
            # Ajouter chaque mot avec ses timestamps, COUPER ceux hors plage
            for idx, word in enumerate(words):
                word_start = seg_start + (idx * word_duration)
                word_end = word_start + word_duration
                
                # Ignorer les mots qui commencent après la fin du short
                if word_start >= end_time:
                    break
                
                # Ignorer les mots qui finissent avant le début du short
                if word_end <= start_time:
                    continue
                
                # Convertir en temps relatif au short
                rel_start = max(0, word_start - start_time)
                rel_end = min(short_duration, word_end - start_time)
                
                relevant_words.append({
                    "text": word,
                    "start": rel_start,
                    "end": rel_end,
                    "duration": rel_end - rel_start
                })
    
    print(f"[KARAOKE] {len(relevant_words)} mots dans la plage {start_time:.1f}s-{end_time:.1f}s")
    
    # Générer les événements avec karaoké - 2 mots par affichage
    for i in range(0, len(relevant_words), 2):
        chunk = relevant_words[i:i+2]
        if not chunk:
            continue
        
        # Timing du chunk = du premier mot au dernier
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]
        
        # Construire le texte avec karaoké effect + position centrée
        # \pos(540,960) = centre exact du short 1080x1920
        # \an5 = alignement centre
        karaoke_text = "{\\pos(540,960)\\an5}"
        
        for word_data in chunk:
            k_duration = int(word_data["duration"] * 100)  # En centisecondes
            karaoke_text += f"{{\\kf{k_duration}}}{word_data['text'].upper()} "
        
        # Ajouter l'événement
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)
        
        ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{karaoke_text.strip()}\n"
    
    # Écrire le fichier
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    return output_path


@app.post("/api/create-short")
async def create_short(request: CreateShortRequest):
    """Créer un short en format 9:16 avec webcam en bas, écran en haut, zoom et sous-titres karaoké"""
    import subprocess
    
    folder_path = OUTPUT_DIR / request.folder_name
    
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Dossier vidéo non trouvé")
    
    # Chercher les fichiers sources (priorité aux versions sans silence)
    screen_path = folder_path / "screennosilence.mp4"
    webcam_path = folder_path / "webcamnosilence.mp4"
    
    if not screen_path.exists():
        screen_path = folder_path / "screen.mp4"
    if not webcam_path.exists():
        webcam_path = folder_path / "webcam.mp4"
    
    if not screen_path.exists():
        raise HTTPException(status_code=404, detail="Fichier screen non trouvé")
    if not webcam_path.exists():
        raise HTTPException(status_code=404, detail="Fichier webcam non trouvé")
    
    # Charger la transcription pour les sous-titres
    transcription_path = folder_path / "transcription.json"
    segments = []
    if transcription_path.exists():
        with open(transcription_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            segments = data.get("segments", [])
    
    # Valider la durée
    duration = request.end - request.start
    if duration < 3 or duration > 60:
        raise HTTPException(status_code=400, detail="Durée invalide (3-60 secondes)")
    
    print(f"[SHORT] Création short: {request.start:.1f}s → {request.end:.1f}s ({duration:.1f}s)")
    print(f"[SHORT] Sources: screen={screen_path.name}, webcam={webcam_path.name}")
    print(f"[SHORT] Transcription: {len(segments)} segments")
    
    try:
        ffmpeg_path = video_merger.ffmpeg_path
        
        # Créer le dossier shorts si nécessaire
        shorts_dir = folder_path / "shorts"
        shorts_dir.mkdir(exist_ok=True)
        
        # Nom du fichier de sortie
        safe_title = "".join(c for c in request.title if c.isalnum() or c in " -_")[:30]
        timestamp = datetime.now().strftime("%H%M%S")
        output_filename = f"short_{safe_title}_{timestamp}.mp4"
        output_path = shorts_dir / output_filename
        
        # Générer les sous-titres karaoké si transcription disponible
        ass_path = None
        if segments:
            ass_path = shorts_dir / f"temp_{timestamp}.ass"
            generate_karaoke_ass(segments, request.start, request.end, str(ass_path))
            print(f"[SHORT] Sous-titres karaoké générés: {ass_path}")
        
        # Dimensions du short (9:16)
        SHORT_WIDTH = 1080
        SHORT_HEIGHT = 1920
        HALF_HEIGHT = SHORT_HEIGHT // 2  # 960px pour chaque moitié
        
        # Facteur de zoom pour animation (1.8 = plus grand pour permettre le pan)
        ZOOM = 1.8
        ZOOM_WIDTH = int(SHORT_WIDTH * ZOOM)
        ZOOM_HEIGHT = int(HALF_HEIGHT * ZOOM)
        
        # Paramètres
        WEBCAM_ZOOM = 1.5  # Zoom fixe sur webcam
        WEBCAM_W = int(SHORT_WIDTH * WEBCAM_ZOOM)
        WEBCAM_H = int(HALF_HEIGHT * WEBCAM_ZOOM)
        
        if ass_path and ass_path.exists():
            # Avec sous-titres
            ass_path_str = str(ass_path.absolute()).replace("\\", "/")
            ass_path_escaped = ass_path_str.replace(":", "\\:")
            
            print(f"[SHORT] Écran: pan fluide, Webcam: zoom {WEBCAM_ZOOM}x statique")
            
            filter_complex = (
                # Écran avec pan FLUIDE
                f"[0:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"fps=30,"
                f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}:'(iw-ow)/2+(iw-ow)/4*sin(n*0.005)':'(ih-oh)/2+(ih-oh)/4*cos(n*0.004)'[screen];"
                
                # Webcam : zoom STATIQUE 1.5x centré (le zoom progressif déforme trop)
                f"[1:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"scale={WEBCAM_W}:{WEBCAM_H}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                
                # Empiler verticalement
                f"[screen][webcam]vstack=inputs=2[stacked];"
                
                # Ajouter les sous-titres karaoké (utiliser subtitles au lieu de ass pour meilleure compatibilité)
                f"[stacked]subtitles='{ass_path_escaped}'[out];"
                
                # Audio
                f"[0:a]atrim=start={request.start}:end={request.end},asetpts=PTS-STARTPTS[audio]"
            )
        else:
            # Sans sous-titres - mêmes filtres
            filter_complex = (
                # Écran avec pan FLUIDE
                f"[0:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"fps=30,"
                f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}:'(iw-ow)/2+(iw-ow)/4*sin(n*0.005)':'(ih-oh)/2+(ih-oh)/4*cos(n*0.004)'[screen];"
                
                # Webcam : zoom STATIQUE 1.5x centré
                f"[1:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"scale={WEBCAM_W}:{WEBCAM_H}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                
                f"[screen][webcam]vstack=inputs=2[out];"
                
                f"[0:a]atrim=start={request.start}:end={request.end},asetpts=PTS-STARTPTS[audio]"
            )
        
        # Commande FFmpeg
        cmd = [
            ffmpeg_path, "-y",
            "-i", str(screen_path),
            "-i", str(webcam_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "[audio]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        print(f"[SHORT] Exécution FFmpeg...")
        print(f"[SHORT] Commande: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[SHORT] Erreur FFmpeg (tentative 1): {result.stderr[-800:] if result.stderr else 'No stderr'}")
            
            # Essayer sans sous-titres mais avec audio
            print(f"[SHORT] Réessai sans sous-titres (avec audio)...")
            filter_complex_no_subs = (
                f"[0:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[screen];"
                f"[1:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                f"[screen][webcam]vstack=inputs=2[out];"
                f"[0:a]atrim=start={request.start}:end={request.end},asetpts=PTS-STARTPTS[audio]"
            )
            cmd_no_subs = [
                ffmpeg_path, "-y",
                "-i", str(screen_path),
                "-i", str(webcam_path),
                "-filter_complex", filter_complex_no_subs,
                "-map", "[out]",
                "-map", "[audio]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(output_path)
            ]
            result = subprocess.run(cmd_no_subs, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[SHORT] Erreur FFmpeg (tentative 2): {result.stderr[-500:] if result.stderr else 'No stderr'}")
                
                # Dernier essai sans audio
                print(f"[SHORT] Réessai sans audio...")
                filter_complex_fallback = (
                    f"[0:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                    f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[screen];"
                    f"[1:v]trim=start={request.start}:end={request.end},setpts=PTS-STARTPTS,"
                    f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                    f"[screen][webcam]vstack=inputs=2[out]"
                )
                cmd_fallback = [
                    ffmpeg_path, "-y",
                    "-i", str(screen_path),
                    "-i", str(webcam_path),
                    "-filter_complex", filter_complex_fallback,
                    "-map", "[out]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-an",
                    "-movflags", "+faststart",
                    str(output_path)
                ]
                result = subprocess.run(cmd_fallback, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"[SHORT] Erreur FFmpeg finale: {result.stderr[-500:] if result.stderr else 'No stderr'}")
                    raise HTTPException(status_code=500, detail="Erreur lors de la création du short")
        
        # Nettoyer le fichier ASS temporaire
        if ass_path and ass_path.exists():
            ass_path.unlink()
        
        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Fichier short non créé")
        
        output_size = output_path.stat().st_size
        print(f"[SHORT] Short créé: {output_path} ({output_size} bytes)")
        
        return {
            "success": True,
            "filename": output_filename,
            "path": f"/output/{request.folder_name}/shorts/{output_filename}",
            "duration": duration,
            "size": output_size,
            "dimensions": f"{SHORT_WIDTH}x{SHORT_HEIGHT}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SHORT] Erreur: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shorts/{folder_name}")
async def list_shorts(folder_name: str):
    """Lister les shorts générés pour une vidéo"""
    
    folder_path = OUTPUT_DIR / folder_name
    shorts_dir = folder_path / "shorts"
    
    if not shorts_dir.exists():
        return {"shorts": []}
    
    shorts = []
    for file in shorts_dir.glob("*.mp4"):
        shorts.append({
            "filename": file.name,
            "path": f"/output/{folder_name}/shorts/{file.name}",
            "size": file.stat().st_size,
            "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    # Trier par date de création (plus récent en premier)
    shorts.sort(key=lambda x: x["created"], reverse=True)
    
    return {"shorts": shorts}


# ===== TRAITEMENT AUTOMATIQUE =====

class AutoProcessRequest(BaseModel):
    folder_name: str
    silence_threshold: float = 0.3  # Seuil de silence en secondes
    auto_illustrate: bool = False  # Ajouter des clips Pexels/Unsplash
    layout: str = "overlay"  # Layout: screen_only, webcam_only, overlay, side_by_side


class AutoIllustrateRequest(BaseModel):
    folder_name: str


async def auto_process_task(folder_name: str, silence_threshold: float = 0.3, auto_illustrate: bool = False, layout: str = "overlay"):
    """Tâche de traitement automatique en arrière-plan
    
    Workflows par layout:
    - screen_only: silences + clips Pexels (pas de shorts)
    - webcam_only: silences + clips Pexels (pas de shorts)
    - overlay/side_by_side: silences + shorts + clips Pexels (workflow complet)
    """
    import subprocess
    import asyncio
    import time
    
    folder_path = OUTPUT_DIR / folder_name
    transcription_path = folder_path / "transcription.json"
    original_path = folder_path / "original.mp4"
    
    # Déterminer le type de workflow
    is_full_workflow = layout in ['overlay', 'side_by_side']
    workflow_type = "complet" if is_full_workflow else "simplifié"
    
    print(f"[AUTO-PROCESS] Démarrage traitement automatique pour {folder_name}")
    print(f"[AUTO-PROCESS] Layout: {layout} - Workflow: {workflow_type}")
    
    # 1. Attendre que la transcription soit terminée (max 5 minutes)
    max_wait = 300  # 5 minutes
    wait_start = time.time()
    while not transcription_path.exists():
        if time.time() - wait_start > max_wait:
            print(f"[AUTO-PROCESS] Timeout: transcription non disponible après {max_wait}s")
            return
        await asyncio.sleep(2)
        print(f"[AUTO-PROCESS] Attente transcription... ({int(time.time() - wait_start)}s)")
    
    print(f"[AUTO-PROCESS] Transcription disponible!")
    
    # Charger la transcription
    try:
        with open(transcription_path, "r", encoding="utf-8") as f:
            transcription_data = json.load(f)
    except Exception as e:
        print(f"[AUTO-PROCESS] Erreur lecture transcription: {e}")
        return
    
    segments = transcription_data.get("segments", [])
    if not segments:
        print(f"[AUTO-PROCESS] Pas de segments dans la transcription")
        return
    
    # 2. Détecter les silences automatiquement
    print(f"[AUTO-PROCESS] Détection des silences (seuil: {silence_threshold}s)...")
    
    detected_silences = []
    for i in range(len(segments) - 1):
        current_end = segments[i]["end"]
        next_start = segments[i + 1]["start"]
        gap = next_start - current_end
        
        if gap >= silence_threshold:
            detected_silences.append({
                "start": current_end,
                "end": next_start,
                "duration": gap
            })
    
    print(f"[AUTO-PROCESS] {len(detected_silences)} silences détectés")
    
    # 3. Supprimer les silences si détectés
    if detected_silences:
        print(f"[AUTO-PROCESS] Suppression des silences...")
        
        # Obtenir la durée de la vidéo
        ffprobe_path = str(Path(__file__).parent.parent.parent / "ffmpeg" / "ffprobe.exe")
        ffmpeg_path = str(Path(__file__).parent.parent.parent / "ffmpeg" / "ffmpeg.exe")
        
        if not Path(ffprobe_path).exists():
            ffprobe_path = "ffprobe"
            ffmpeg_path = "ffmpeg"
        
        try:
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", str(original_path)],
                capture_output=True, text=True
            )
            video_duration = float(result.stdout.strip())
        except:
            video_duration = segments[-1]["end"] + 1
        
        # Créer les segments à conserver (inverser les silences)
        keep_segments = []
        current_pos = 0.0
        
        for silence in detected_silences:
            if silence["start"] > current_pos:
                keep_segments.append({"start": current_pos, "end": silence["start"]})
            current_pos = silence["end"]
        
        # Ajouter le dernier segment
        if current_pos < video_duration:
            keep_segments.append({"start": current_pos, "end": video_duration})
        
        if keep_segments:
            # Construire le filtre FFmpeg
            filter_parts = []
            concat_parts = []
            
            for i, seg in enumerate(keep_segments):
                start = seg["start"]
                end = seg["end"]
                filter_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
                filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
                concat_parts.append(f"[v{i}][a{i}]")
            
            filter_complex = "".join(filter_parts)
            filter_complex += f"{''.join(concat_parts)}concat=n={len(keep_segments)}:v=1:a=1[outv][outa]"
            
            nosilence_path = folder_path / "nosilence.mp4"
            
            cmd = [
                ffmpeg_path, "-y",
                "-i", str(original_path),
                "-filter_complex", filter_complex,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(nosilence_path)
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if process.returncode == 0 and nosilence_path.exists():
                print(f"[AUTO-PROCESS] Silences supprimés! nosilence.mp4 créé ({nosilence_path.stat().st_size} bytes)")
            else:
                print(f"[AUTO-PROCESS] Erreur suppression silences: {process.stderr[-500:] if process.stderr else 'Unknown'}")
            
            # Créer webcamnosilence.mp4 et screennosilence.mp4 SEULEMENT pour overlay/side_by_side
            if is_full_workflow:
                webcam_path = folder_path / "webcam.mp4"
                screen_path = folder_path / "screen.mp4"
                
                # Traiter webcam.mp4
                if webcam_path.exists():
                    print(f"[AUTO-PROCESS] Création webcamnosilence.mp4...")
                    webcamnosilence_path = folder_path / "webcamnosilence.mp4"
                    
                    # Filtre pour vidéo seule (webcam n'a pas d'audio)
                    filter_parts_v = []
                    concat_parts_v = []
                    for i, seg in enumerate(keep_segments):
                        start = seg["start"]
                        end = seg["end"]
                        filter_parts_v.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
                        concat_parts_v.append(f"[v{i}]")
                    
                    filter_complex_v = "".join(filter_parts_v)
                    filter_complex_v += f"{''.join(concat_parts_v)}concat=n={len(keep_segments)}:v=1:a=0[outv]"
                    
                    cmd_webcam = [
                        ffmpeg_path, "-y",
                        "-i", str(webcam_path),
                        "-filter_complex", filter_complex_v,
                        "-map", "[outv]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-movflags", "+faststart",
                        str(webcamnosilence_path)
                    ]
                    
                    process_webcam = subprocess.run(cmd_webcam, capture_output=True, text=True, timeout=600)
                    if process_webcam.returncode == 0 and webcamnosilence_path.exists():
                        print(f"[AUTO-PROCESS] webcamnosilence.mp4 créé ({webcamnosilence_path.stat().st_size} bytes)")
                    else:
                        print(f"[AUTO-PROCESS] Erreur webcamnosilence: {process_webcam.stderr[-200:] if process_webcam.stderr else 'Unknown'}")
                
                # Traiter screen.mp4
                if screen_path.exists():
                    print(f"[AUTO-PROCESS] Création screennosilence.mp4...")
                    screennosilence_path = folder_path / "screennosilence.mp4"
                    
                    # Screen a l'audio, utiliser le même filtre que original
                    cmd_screen = [
                        ffmpeg_path, "-y",
                        "-i", str(screen_path),
                        "-filter_complex", filter_complex,
                        "-map", "[outv]", "-map", "[outa]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart",
                        str(screennosilence_path)
                    ]
                    
                    process_screen = subprocess.run(cmd_screen, capture_output=True, text=True, timeout=600)
                    if process_screen.returncode == 0 and screennosilence_path.exists():
                        print(f"[AUTO-PROCESS] screennosilence.mp4 créé ({screennosilence_path.stat().st_size} bytes)")
                    else:
                        print(f"[AUTO-PROCESS] Erreur screennosilence: {process_screen.stderr[-200:] if process_screen.stderr else 'Unknown'}")
            else:
                print(f"[AUTO-PROCESS] Layout {layout}: pas de création webcamnosilence/screennosilence")
    
    # 4. Générer les shorts automatiquement (SEULEMENT pour overlay/side_by_side)
    if is_full_workflow:
        print(f"[AUTO-PROCESS] Génération des suggestions de shorts...")
        
        try:
            openrouter = OpenRouterService()
            shorts_suggestions = await openrouter.generate_shorts_suggestions(segments, video_duration)
            
            if shorts_suggestions:
                # Sauvegarder les suggestions
                shorts_path = folder_path / "shorts_suggestions.json"
                with open(shorts_path, "w", encoding="utf-8") as f:
                    json.dump(shorts_suggestions, f, ensure_ascii=False, indent=2)
                
                print(f"[AUTO-PROCESS] {len(shorts_suggestions)} suggestions de shorts générées")
                
                # Créer automatiquement les shorts
                shorts_dir = folder_path / "shorts"
                shorts_dir.mkdir(exist_ok=True)
                
                video_merger = VideoMerger()
                ffmpeg_path = video_merger.ffmpeg_path
                
                for i, short in enumerate(shorts_suggestions[:3]):  # Max 3 shorts auto
                    start_time = short.get("start_time", 0)
                    end_time = short.get("end_time", start_time + 30)
                    duration = end_time - start_time
                    
                    if duration < 5 or duration > 60:
                        continue
                    
                    output_filename = f"short_{i+1}_{int(start_time)}s.mp4"
                    output_path = shorts_dir / output_filename
                    
                    # Extraire le short avec format vertical 9:16
                    cmd = [
                        ffmpeg_path, "-y",
                        "-i", str(original_path),
                        "-ss", str(start_time),
                        "-t", str(duration),
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart",
                        str(output_path)
                    ]
                    
                    process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    
                    if process.returncode == 0 and output_path.exists():
                        print(f"[AUTO-PROCESS] Short créé: {output_filename}")
                    else:
                        print(f"[AUTO-PROCESS] Erreur création short {i+1}")
            else:
                print(f"[AUTO-PROCESS] Pas de suggestions de shorts générées")
        except Exception as e:
            print(f"[AUTO-PROCESS] Erreur génération shorts: {e}")
    else:
        print(f"[AUTO-PROCESS] Layout {layout}: pas de génération de shorts")
    
    # 5. Auto-illustration si activée
    if auto_illustrate:
        print(f"[AUTO-PROCESS] Lancement auto-illustration Pexels/Unsplash...")
        try:
            await auto_illustrate_task(folder_name, segments, video_duration)
        except Exception as e:
            print(f"[AUTO-PROCESS] Erreur auto-illustration: {e}")
    
    print(f"[AUTO-PROCESS] Traitement automatique terminé pour {folder_name}")


@app.post("/api/auto-process")
async def auto_process(request: AutoProcessRequest, background_tasks: BackgroundTasks):
    """Lance le traitement automatique (suppression silences + génération shorts + illustration)"""
    
    folder_path = OUTPUT_DIR / request.folder_name
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(
        auto_process_task,
        request.folder_name,
        request.silence_threshold,
        request.auto_illustrate,
        request.layout
    )
    
    return {
        "success": True,
        "message": "Traitement automatique lancé en arrière-plan",
        "folder_name": request.folder_name,
        "layout": request.layout
    }


# ===== AUTO-ILLUSTRATION PEXELS/UNSPLASH =====

async def auto_illustrate_task(folder_name: str, segments: List[dict] = None, video_duration: float = None):
    """Tâche d'auto-illustration en arrière-plan"""
    import subprocess
    import aiohttp
    import asyncio
    
    folder_path = OUTPUT_DIR / folder_name
    original_path = folder_path / "original.mp4"
    transcription_path = folder_path / "transcription.json"
    
    print(f"[AUTO-ILLUSTRATE] Démarrage pour {folder_name}")
    
    # Charger la transcription si pas fournie
    if segments is None:
        if not transcription_path.exists():
            print(f"[AUTO-ILLUSTRATE] Pas de transcription disponible")
            return
        
        try:
            with open(transcription_path, "r", encoding="utf-8") as f:
                transcription_data = json.load(f)
            segments = transcription_data.get("segments", [])
        except Exception as e:
            print(f"[AUTO-ILLUSTRATE] Erreur lecture transcription: {e}")
            return
    
    if not segments:
        print(f"[AUTO-ILLUSTRATE] Pas de segments")
        return
    
    # Obtenir la durée vidéo si pas fournie
    if video_duration is None:
        video_merger = VideoMerger()
        ffprobe_path = str(Path(video_merger.ffmpeg_path).parent / "ffprobe.exe")
        if not Path(ffprobe_path).exists():
            ffprobe_path = "ffprobe"
        
        try:
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(original_path)],
                capture_output=True, text=True
            )
            video_duration = float(result.stdout.strip())
        except:
            video_duration = segments[-1]["end"] + 1
    
    # Analyser le contenu pour trouver les moments à illustrer
    print(f"[AUTO-ILLUSTRATE] Analyse du contenu avec IA...")
    
    try:
        openrouter = OpenRouterService()
        illustration_moments = await openrouter.analyze_for_illustrations(segments, video_duration, max_illustrations=2)
        
        if not illustration_moments:
            print(f"[AUTO-ILLUSTRATE] Pas de moments à illustrer trouvés")
            return
        
        print(f"[AUTO-ILLUSTRATE] {len(illustration_moments)} moments à illustrer")
        
        # Créer le dossier pour les illustrations
        illustrations_dir = folder_path / "illustrations"
        illustrations_dir.mkdir(exist_ok=True)
        
        # Clé API Pexels (depuis .env) - pour les CLIPS VIDÉO
        pexels_key = os.getenv("PEXELS_API_KEY", "")
        
        if not pexels_key:
            print(f"[AUTO-ILLUSTRATE] Clé API Pexels non configurée")
            print(f"[AUTO-ILLUSTRATE] Ajoutez PEXELS_API_KEY dans .env (https://www.pexels.com/api/)")
            # Sauvegarder les suggestions quand même
            suggestions_path = folder_path / "illustration_suggestions.json"
            with open(suggestions_path, "w", encoding="utf-8") as f:
                json.dump(illustration_moments, f, ensure_ascii=False, indent=2)
            print(f"[AUTO-ILLUSTRATE] Suggestions sauvegardées dans illustration_suggestions.json")
            return
        
        # Télécharger les clips vidéo Pexels
        downloaded_clips = []
        
        async with aiohttp.ClientSession() as session:
            for i, moment in enumerate(illustration_moments[:5]):  # Max 5 illustrations
                keyword = moment.get("keyword", "")
                timestamp = moment.get("timestamp", 0)
                duration = moment.get("duration", 3)
                
                if not keyword:
                    continue
                
                print(f"[AUTO-ILLUSTRATE] Recherche clip Pexels pour '{keyword}'...")
                
                clip_path = await download_pexels_video(session, pexels_key, keyword, illustrations_dir, i)
                
                if clip_path:
                    downloaded_clips.append({
                        "path": str(clip_path),
                        "keyword": keyword,
                        "timestamp": timestamp,
                        "duration": duration
                    })
                    print(f"[AUTO-ILLUSTRATE] Clip téléchargé: {clip_path.name}")
        
        if downloaded_clips:
            # Sauvegarder les infos des clips
            clips_info_path = folder_path / "illustration_clips.json"
            with open(clips_info_path, "w", encoding="utf-8") as f:
                json.dump(downloaded_clips, f, ensure_ascii=False, indent=2)
            
            print(f"[AUTO-ILLUSTRATE] {len(downloaded_clips)} clips téléchargés")
            
            # Créer la vidéo illustrée
            await create_illustrated_video(folder_path, original_path, downloaded_clips)
        else:
            print(f"[AUTO-ILLUSTRATE] Aucun clip téléchargé")
            
    except Exception as e:
        print(f"[AUTO-ILLUSTRATE] Erreur: {e}")
        import traceback
        traceback.print_exc()


async def download_pexels_video(session, api_key: str, keyword: str, output_dir: Path, index: int) -> Optional[Path]:
    """Télécharge une vidéo depuis Pexels"""
    try:
        headers = {"Authorization": api_key}
        url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&size=small"
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None
            
            data = await response.json()
            videos = data.get("videos", [])
            
            if not videos:
                return None
            
            # Prendre la plus petite qualité
            video_files = videos[0].get("video_files", [])
            if not video_files:
                return None
            
            # Trier par taille et prendre le plus petit
            video_files.sort(key=lambda x: x.get("width", 9999))
            video_url = video_files[0].get("link")
            
            if not video_url:
                return None
            
            # Télécharger
            output_path = output_dir / f"pexels_{index}_{keyword.replace(' ', '_')[:20]}.mp4"
            
            async with session.get(video_url) as video_response:
                if video_response.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await video_response.read())
                    return output_path
            
    except Exception as e:
        print(f"[PEXELS] Erreur: {e}")
    
    return None


async def download_unsplash_image(session, api_key: str, keyword: str, output_dir: Path, index: int) -> Optional[Path]:
    """Télécharge une image depuis Unsplash"""
    try:
        url = f"https://api.unsplash.com/search/photos?query={keyword}&per_page=1&client_id={api_key}"
        
        async with session.get(url) as response:
            if response.status != 200:
                return None
            
            data = await response.json()
            results = data.get("results", [])
            
            if not results:
                return None
            
            # Prendre la taille small
            image_url = results[0].get("urls", {}).get("small")
            
            if not image_url:
                return None
            
            # Télécharger
            output_path = output_dir / f"unsplash_{index}_{keyword.replace(' ', '_')[:20]}.jpg"
            
            async with session.get(image_url) as img_response:
                if img_response.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await img_response.read())
                    return output_path
            
    except Exception as e:
        print(f"[UNSPLASH] Erreur: {e}")
    
    return None


async def create_illustrated_video(folder_path: Path, original_path: Path, clips: List[dict]):
    """Crée une vidéo avec les B-rolls insérés EN PLEIN ÉCRAN (audio original conservé)"""
    import subprocess
    
    video_merger = VideoMerger()
    ffmpeg_path = video_merger.ffmpeg_path
    
    output_path = folder_path / "illustrated.mp4"
    
    print(f"[AUTO-ILLUSTRATE] Création de illustrated.mp4...")
    
    # Filtrer les clips téléchargés avec succès
    valid_clips = [c for c in clips if c.get("downloaded", True) and (c.get("path") or c.get("local_path"))]
    
    if not valid_clips:
        print(f"[AUTO-ILLUSTRATE] Aucun clip valide à insérer")
        return
    
    # Obtenir la résolution de la vidéo originale
    probe_cmd = [
        ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe"),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        str(original_path)
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    original_res = probe_result.stdout.strip() or "1920x1080"
    try:
        orig_w, orig_h = map(int, original_res.split("x"))
    except:
        orig_w, orig_h = 1920, 1080
    
    print(f"[AUTO-ILLUSTRATE] Résolution originale: {orig_w}x{orig_h}")
    
    # ÉTAPE 1: Pré-traiter chaque clip Pexels (couper à max 3s + redimensionner)
    processed_clips = []
    ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe")
    
    for i, clip in enumerate(valid_clips):
        clip_path = clip.get("path") or clip.get("local_path")
        timestamp = clip["timestamp"]
        
        # Obtenir la durée du clip original
        probe_clip_cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            clip_path
        ]
        probe_result = subprocess.run(probe_clip_cmd, capture_output=True, text=True)
        try:
            clip_duration = float(probe_result.stdout.strip())
        except:
            clip_duration = 10  # Fallback
        
        # Durée = min(3 secondes, durée du clip)
        target_duration = min(3, clip_duration)
        
        # Fichier de sortie pré-traité
        processed_path = folder_path / "illustrations" / f"processed_{i}.mp4"
        
        # Couper et redimensionner
        preprocess_cmd = [
            ffmpeg_path, "-y",
            "-i", clip_path,
            "-t", str(target_duration),  # Durée max 3 secondes ou moins
            "-vf", f"scale={orig_w}:{orig_h}:force_original_aspect_ratio=increase,crop={orig_w}:{orig_h}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an",  # Pas d'audio
            str(processed_path)
        ]
        
        result = subprocess.run(preprocess_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and processed_path.exists():
            processed_clips.append({
                "path": str(processed_path),
                "timestamp": timestamp,
                "duration": target_duration
            })
            print(f"[AUTO-ILLUSTRATE] B-roll {i+1} pré-traité: {target_duration:.1f}s @ {orig_w}x{orig_h}")
        else:
            print(f"[AUTO-ILLUSTRATE] Erreur pré-traitement clip {i+1}: {result.stderr[-200:] if result.stderr else 'Unknown'}")
    
    if not processed_clips:
        print(f"[AUTO-ILLUSTRATE] Aucun clip pré-traité avec succès")
        return
    
    # ÉTAPE 2: Construction du filtre complexe avec clips pré-traités
    # On utilise tpad pour ajouter du "silence vidéo" au début du clip
    # Ainsi le clip commence à jouer exactement au bon timestamp
    inputs = ["-i", str(original_path)]
    filter_parts = []
    
    for i, clip in enumerate(processed_clips):
        timestamp = clip["timestamp"]
        duration = clip.get("duration", 3)
        inputs.extend(["-i", clip["path"]])
        
        # tpad ajoute des frames au début pour que le clip commence au bon moment
        filter_parts.append(
            f"[{i+1}:v]tpad=start_duration={timestamp}:start_mode=clone,"
            f"setpts=PTS-STARTPTS[clip{i}];"
        )
        
        print(f"[AUTO-ILLUSTRATE] B-roll {i+1}: tpad={timestamp:.1f}s + {duration:.1f}s clip")
    
    # Overlay les clips - avec enable pour le timing exact
    current_output = "[0:v]"
    for i, clip in enumerate(processed_clips):
        timestamp = clip["timestamp"]
        duration = clip.get("duration", 3)
        
        next_output = f"[v{i}]" if i < len(processed_clips) - 1 else "[outv]"
        
        # Overlay avec enable (le clip est déjà décalé par tpad)
        filter_parts.append(
            f"{current_output}[clip{i}]overlay=0:0:"
            f"enable='between(t,{timestamp},{timestamp+duration})':eof_action=pass{next_output};"
        )
        current_output = f"[v{i}]"
        
        print(f"[AUTO-ILLUSTRATE] B-roll {i+1}: overlay {timestamp:.1f}s → {timestamp+duration:.1f}s")
    
    filter_complex = "".join(filter_parts).rstrip(";")
    
    cmd = [
        ffmpeg_path, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",  # Garde l'audio original (voix-off)
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    try:
        print(f"[AUTO-ILLUSTRATE] Commande FFmpeg: {' '.join(cmd[:10])}...")
        print(f"[AUTO-ILLUSTRATE] Filter complex: {filter_complex[:200]}...")
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if process.returncode == 0 and output_path.exists():
            print(f"[AUTO-ILLUSTRATE] illustrated.mp4 créé ({output_path.stat().st_size} bytes)")
        else:
            print(f"[AUTO-ILLUSTRATE] Erreur FFmpeg (code {process.returncode}): {process.stderr[-500:] if process.stderr else 'Unknown'}")
    except Exception as e:
        print(f"[AUTO-ILLUSTRATE] Erreur création vidéo: {e}")


@app.post("/api/auto-illustrate")
async def auto_illustrate(request: AutoIllustrateRequest, background_tasks: BackgroundTasks):
    """Lance l'auto-illustration seule"""
    
    folder_path = OUTPUT_DIR / request.folder_name
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    
    # Lancer en arrière-plan
    background_tasks.add_task(auto_illustrate_task, request.folder_name)
    
    return {
        "success": True,
        "message": "Auto-illustration lancée en arrière-plan",
        "folder_name": request.folder_name
    }


# =============================================
# PIPELINE AUTO OVERLAY COMPLET (11 étapes)
# =============================================

class AutoProcessFullRequest(BaseModel):
    folder_name: str
    layout: str = "overlay"  # overlay, side_by_side, screen_only, webcam_only
    silence_threshold: float = 0.3  # Seuil de silence en secondes
    max_shorts: int = 5  # Nombre max de shorts
    webcam_x: int = 50
    webcam_y: int = 50
    webcam_size: int = 300
    webcam_shape: str = "circle"
    border_color: str = "#FFB6C1"
    border_width: int = 4


class AutoProcessFullProgress(BaseModel):
    step: int
    total_steps: int
    step_name: str
    status: str  # running, completed, error
    message: str
    progress_percent: float


# Stockage des progressions (en mémoire pour SSE)
process_progress: Dict[str, List[AutoProcessFullProgress]] = {}


async def auto_process_full_pipeline(
    folder_name: str,
    layout: str,
    silence_threshold: float,
    max_shorts: int,
    webcam_x: int,
    webcam_y: int,
    webcam_size: int,
    webcam_shape: str,
    border_color: str,
    border_width: int
):
    """
    Pipeline complet de traitement automatique en 11 étapes
    
    1. Organisation des fichiers
    2. Détection des silences
    3. Découpe des silences
    4. Transcription
    5. Analyse pour clips Pexels
    6. Détection moments clés (shorts)
    7. Génération des shorts (9:16)
    8. Vidéo finale 16:9 (sans Pexels)
    9. Vidéo finale 16:9 avec B-roll Pexels
    10. Génération SEO YouTube
    11. Génération miniature
    """
    import subprocess
    import asyncio
    import time
    import base64
    
    from services.pexels import PexelsService
    from services.openrouter import OpenRouterService
    from services.transcription import TranscriptionService
    
    folder_path = OUTPUT_DIR / folder_name
    is_full_workflow = layout in ['overlay', 'side_by_side']
    
    # Initialiser la progression
    process_progress[folder_name] = []
    
    def update_progress(step: int, step_name: str, status: str, message: str):
        total_steps = 11 if is_full_workflow else 7
        progress = AutoProcessFullProgress(
            step=step,
            total_steps=total_steps,
            step_name=step_name,
            status=status,
            message=message,
            progress_percent=(step / total_steps) * 100 if status == "completed" else ((step - 1) / total_steps) * 100
        )
        process_progress[folder_name].append(progress)
        print(f"[PIPELINE {folder_name}] Étape {step}/{total_steps}: {step_name} - {status} - {message}")
    
    try:
        # ========== ÉTAPE 1: Organisation des fichiers ==========
        update_progress(1, "Organisation des fichiers", "running", "Vérification des fichiers...")
        
        original_path = folder_path / "original.mp4"
        screen_path = folder_path / "screen.mp4"
        webcam_path = folder_path / "webcam.mp4"
        
        if not original_path.exists():
            update_progress(1, "Organisation des fichiers", "error", "original.mp4 non trouvé")
            return
        
        # Vérifier les fichiers disponibles
        has_screen = screen_path.exists()
        has_webcam = webcam_path.exists()
        
        update_progress(1, "Organisation des fichiers", "completed", 
            f"Fichiers OK: original={original_path.exists()}, screen={has_screen}, webcam={has_webcam}")
        
        # ========== ÉTAPE 2: Détection des silences ==========
        update_progress(2, "Détection des silences", "running", "Analyse audio avec FFmpeg...")
        
        ffmpeg_path = video_merger.ffmpeg_path
        ffprobe_path = str(Path(ffmpeg_path).parent / "ffprobe.exe")
        if not Path(ffprobe_path).exists():
            ffprobe_path = "ffprobe"
        
        # Obtenir la durée totale
        try:
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(original_path)],
                capture_output=True, text=True
            )
            video_duration = float(result.stdout.strip())
        except:
            video_duration = 60.0  # Défaut
        
        # Détecter les silences avec FFmpeg
        import re
        detect_cmd = [
            ffmpeg_path, "-i", str(original_path),
            "-af", f"silencedetect=noise=-40dB:d={silence_threshold}",
            "-f", "null", "-"
        ]
        result = subprocess.run(detect_cmd, capture_output=True, text=True)
        stderr = result.stderr
        
        silence_starts = re.findall(r"silence_start: ([\d.]+)", stderr)
        silence_ends = re.findall(r"silence_end: ([\d.]+)", stderr)
        min_len = min(len(silence_starts), len(silence_ends))
        silences = list(zip(
            [float(s) for s in silence_starts[:min_len]],
            [float(e) for e in silence_ends[:min_len]]
        ))
        
        # Sauvegarder les silences
        silences_data = [{"start": s, "end": e, "duration": e - s} for s, e in silences]
        silences_path = folder_path / "silences.json"
        with open(silences_path, "w", encoding="utf-8") as f:
            json.dump(silences_data, f, ensure_ascii=False, indent=2)
        
        update_progress(2, "Détection des silences", "completed", f"{len(silences)} silence(s) détecté(s)")
        
        # ========== ÉTAPE 3: Découpe des silences ==========
        update_progress(3, "Découpe des silences", "running", "Suppression des zones silencieuses...")
        
        # Construire les segments à garder
        keep_segments = []
        current_pos = 0.0
        
        for silence_start, silence_end in silences:
            if silence_start > current_pos + 0.1:
                keep_segments.append({"start": current_pos, "end": silence_start})
            current_pos = silence_end
        
        if current_pos < video_duration - 0.1:
            keep_segments.append({"start": current_pos, "end": video_duration})
        
        nosilence_path = folder_path / "nosilence.mp4"
        screennosilence_path = folder_path / "screennosilence.mp4"
        webcamnosilence_path = folder_path / "webcamnosilence.mp4"
        
        async def cut_silences_from_video(input_path: Path, output_path: Path, segments: list, with_audio: bool = True):
            """Couper les silences d'une vidéo"""
            if not input_path.exists() or not segments:
                return False
            
            # Construire le filtre
            filter_parts = []
            concat_v = []
            concat_a = []
            
            for i, seg in enumerate(segments):
                start, end = seg["start"], seg["end"]
                filter_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
                concat_v.append(f"[v{i}]")
                if with_audio:
                    filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
                    concat_a.append(f"[a{i}]")
            
            filter_complex = "".join(filter_parts)
            
            if with_audio:
                filter_complex += f"{''.join(concat_v)}concat=n={len(segments)}:v=1:a=0[outv];"
                filter_complex += f"{''.join(concat_a)}concat=n={len(segments)}:v=0:a=1[outa]"
                maps = ["-map", "[outv]", "-map", "[outa]"]
            else:
                filter_complex += f"{''.join(concat_v)}concat=n={len(segments)}:v=1:a=0[outv]"
                maps = ["-map", "[outv]"]
            
            cmd = [
                ffmpeg_path, "-y",
                "-i", str(input_path),
                "-filter_complex", filter_complex,
                *maps,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return process.returncode == 0 and output_path.exists()
        
        if keep_segments:
            # Couper original.mp4 -> nosilence.mp4
            success = await cut_silences_from_video(original_path, nosilence_path, keep_segments, with_audio=True)
            
            # Couper screen.mp4 -> screennosilence.mp4 (pour overlay/side_by_side)
            if is_full_workflow and has_screen:
                await cut_silences_from_video(screen_path, screennosilence_path, keep_segments, with_audio=True)
            
            # Couper webcam.mp4 -> webcamnosilence.mp4 (pour overlay/side_by_side)
            if is_full_workflow and has_webcam:
                await cut_silences_from_video(webcam_path, webcamnosilence_path, keep_segments, with_audio=False)
            
            update_progress(3, "Découpe des silences", "completed", 
                f"nosilence.mp4 créé ({nosilence_path.stat().st_size // 1024}KB)" if nosilence_path.exists() else "Erreur découpe")
        else:
            # Pas de silences, copier original
            shutil.copy(original_path, nosilence_path)
            update_progress(3, "Découpe des silences", "completed", "Aucun silence à supprimer")
        
        # ========== ÉTAPE 4: Transcription ==========
        update_progress(4, "Transcription", "running", "Transcription audio avec Groq...")
        
        transcription_service = TranscriptionService()
        
        # Utiliser nosilence.mp4 pour la transcription
        video_to_transcribe = nosilence_path if nosilence_path.exists() else original_path
        
        transcription_result = await transcription_service.transcribe(str(video_to_transcribe))
        
        segments = []
        transcript_text = ""
        
        if transcription_result:
            segments = transcription_result.get("segments", [])
            transcript_text = transcription_result.get("text", "")
            
            # Sauvegarder la transcription
            transcription_data = {
                "filename": "nosilence.mp4",
                "text": transcript_text,
                "segments": segments,
                "language": transcription_result.get("language", "fr"),
                "source": "nosilence"
            }
            
            transcription_path = folder_path / "transcription.json"
            with open(transcription_path, "w", encoding="utf-8") as f:
                json.dump(transcription_data, f, ensure_ascii=False, indent=2)
            
            update_progress(4, "Transcription", "completed", f"{len(segments)} segments transcrits")
        else:
            update_progress(4, "Transcription", "error", "Échec de la transcription")
            return
        
        # ========== ÉTAPE 5: Analyse pour clips Pexels ==========
        update_progress(5, "Analyse pour clips Pexels", "running", "Identification des moments à illustrer...")
        
        openrouter = OpenRouterService()
        pexels = PexelsService()
        
        # Obtenir la durée du fichier nosilence
        try:
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_to_transcribe)],
                capture_output=True, text=True
            )
            nosilence_duration = float(result.stdout.strip())
        except:
            nosilence_duration = segments[-1]["end"] if segments else video_duration
        
        illustration_moments = await openrouter.analyze_for_illustrations(segments, nosilence_duration, max_illustrations=2)
        
        downloaded_clips = []
        if illustration_moments and pexels.is_configured():
            illustrations_dir = folder_path / "illustrations"
            illustrations_dir.mkdir(exist_ok=True)
            
            downloaded_clips = await pexels.download_illustrations(illustration_moments, str(illustrations_dir))
            
            # Sauvegarder les infos
            clips_info_path = folder_path / "illustration_clips.json"
            with open(clips_info_path, "w", encoding="utf-8") as f:
                json.dump(downloaded_clips, f, ensure_ascii=False, indent=2)
            
            downloaded_count = sum(1 for c in downloaded_clips if c.get("downloaded"))
            update_progress(5, "Analyse pour clips Pexels", "completed", f"{downloaded_count} clip(s) téléchargé(s)")
        else:
            update_progress(5, "Analyse pour clips Pexels", "completed", "Aucun clip Pexels (API non configurée ou pas de moments)")
        
        # ========== ÉTAPE 6: Détection moments clés pour shorts ==========
        if is_full_workflow:
            update_progress(6, "Détection moments clés", "running", "Analyse IA des meilleurs moments...")
            
            shorts_suggestions = await openrouter.generate_shorts_suggestions(segments, nosilence_duration)
            
            if shorts_suggestions:
                shorts_path = folder_path / "shorts_suggestions.json"
                with open(shorts_path, "w", encoding="utf-8") as f:
                    json.dump(shorts_suggestions, f, ensure_ascii=False, indent=2)
                
                update_progress(6, "Détection moments clés", "completed", f"{len(shorts_suggestions)} short(s) suggéré(s)")
            else:
                shorts_suggestions = []
                update_progress(6, "Détection moments clés", "completed", "Aucun moment clé détecté")
        
            # ========== ÉTAPE 7: Génération des shorts (9:16) ==========
            update_progress(7, "Génération des shorts", "running", "Création des shorts 9:16...")
            
            shorts_dir = folder_path / "shorts"
            shorts_dir.mkdir(exist_ok=True)
            
            created_shorts = 0
            for i, short in enumerate(shorts_suggestions[:max_shorts]):
                start_time = short.get("start", 0)
                end_time = short.get("end", start_time + 30)
                duration = end_time - start_time
                
                if duration < 5 or duration > 60:
                    continue
                
                # Générer métadonnées avec branding
                short_segments = [s for s in segments if s["start"] >= start_time and s["end"] <= end_time]
                short_text = " ".join([s["text"] for s in short_segments])
                
                short_metadata = await openrouter.generate_short_metadata(short_text, i + 1)
                
                # Nom du fichier
                safe_title = "".join(c for c in short.get("title", f"short_{i+1}")[:20] if c.isalnum() or c in " -_")
                output_filename = f"short_{i+1}_{safe_title.replace(' ', '_')}.mp4"
                output_path = shorts_dir / output_filename
                
                # Générer le short 9:16 avec sous-titres karaoké
                SHORT_WIDTH = 1080
                SHORT_HEIGHT = 1920
                HALF_HEIGHT = SHORT_HEIGHT // 2
                ZOOM = 1.3
                ZOOM_WIDTH = int(SHORT_WIDTH * ZOOM)
                ZOOM_HEIGHT = int(HALF_HEIGHT * ZOOM)
                
                # Générer les sous-titres karaoké
                ass_path = shorts_dir / f"temp_{i}.ass"
                generate_karaoke_ass(segments, start_time, end_time, str(ass_path))
                
                # Fichiers sources (utiliser versions sans silence si disponibles)
                screen_src = screennosilence_path if screennosilence_path.exists() else screen_path
                webcam_src = webcamnosilence_path if webcamnosilence_path.exists() else webcam_path
                
                if screen_src.exists() and webcam_src.exists():
                    # Échapper le chemin ASS pour FFmpeg Windows
                    ass_path_escaped = str(ass_path.absolute()).replace("\\", "/").replace(":", "\\:")
                    
                    filter_complex = (
                        f"[0:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS,"
                        f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                        f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[screen];"
                        f"[1:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS,"
                        f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                        f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                        f"[screen][webcam]vstack=inputs=2[stacked];"
                        f"[stacked]subtitles='{ass_path_escaped}'[out];"
                        f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[audio]"
                    )
                    
                    cmd = [
                        ffmpeg_path, "-y",
                        "-i", str(screen_src),
                        "-i", str(webcam_src),
                        "-filter_complex", filter_complex,
                        "-map", "[out]",
                        "-map", "[audio]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart",
                        str(output_path)
                    ]
                    
                    process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    
                    if process.returncode != 0:
                        # Réessayer sans sous-titres
                        filter_complex_no_subs = (
                            f"[0:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS,"
                            f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[screen];"
                            f"[1:v]trim=start={start_time}:end={end_time},setpts=PTS-STARTPTS,"
                            f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
                            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
                            f"[screen][webcam]vstack=inputs=2[out];"
                            f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[audio]"
                        )
                        cmd[cmd.index("-filter_complex") + 1] = filter_complex_no_subs
                        process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    
                    if process.returncode == 0 and output_path.exists():
                        created_shorts += 1
                        
                        # Sauvegarder les métadonnées du short
                        if short_metadata:
                            metadata_path = shorts_dir / f"{output_filename}.json"
                            with open(metadata_path, "w", encoding="utf-8") as f:
                                json.dump(short_metadata, f, ensure_ascii=False, indent=2)
                
                # Nettoyer le fichier ASS
                ass_path.unlink(missing_ok=True)
            
            update_progress(7, "Génération des shorts", "completed", f"{created_shorts} short(s) créé(s)")
        
            # ========== ÉTAPE 8: Vidéo finale 16:9 (sans Pexels) ==========
            update_progress(8, "Vidéo finale 16:9", "running", "Fusion écran + webcam...")
            
            final_path = folder_path / "final.mp4"
            
            if screennosilence_path.exists() and webcamnosilence_path.exists():
                # Charger les paramètres depuis config.json s'il existe (ceux utilisés pour créer original.mp4)
                config_path = folder_path / "config.json"
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        saved_config = json.load(f)
                    # Utiliser les paramètres sauvegardés
                    webcam_x = saved_config.get("webcam_x", webcam_x)
                    webcam_y = saved_config.get("webcam_y", webcam_y)
                    webcam_size = saved_config.get("webcam_size", webcam_size)
                    webcam_shape = saved_config.get("webcam_shape", webcam_shape)
                    border_color = saved_config.get("border_color", border_color)
                    border_width = saved_config.get("border_width", border_width)
                    print(f"[AUTO-PROCESS] Paramètres chargés depuis config.json: x={webcam_x}, y={webcam_y}, size={webcam_size}")
                else:
                    print(f"[AUTO-PROCESS] config.json non trouvé, utilisation des paramètres passés")
                
                # Refusionner avec les paramètres de position webcam
                inner_size = webcam_size - (border_width * 2) if border_width > 0 else webcam_size
                border_rgb = f"0x{border_color.lstrip('#')}"
                
                if webcam_shape == "circle":
                    shape_filter = (
                        f"[1:v]scale=1280:720:force_original_aspect_ratio=decrease,fps=60,"
                        f"crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size},"
                        f"format=rgba,"
                        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(pow(X-{inner_size//2},2)+pow(Y-{inner_size//2},2),pow({inner_size//2},2)),255,0)'"
                        f"[webcam_shaped]"
                    )
                    if border_width > 0:
                        border_filter = (
                            f"color=c={border_rgb}:s={webcam_size}x{webcam_size}:d=1,format=rgba,"
                            f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(pow(X-{webcam_size//2},2)+pow(Y-{webcam_size//2},2),pow({webcam_size//2},2)),255,0)'"
                            f"[border_circle];"
                            f"[border_circle][webcam_shaped]overlay={border_width}:{border_width}[webcam_with_border];"
                        )
                        webcam_output = "[webcam_with_border]"
                    else:
                        border_filter = ""
                        webcam_output = "[webcam_shaped]"
                else:
                    shape_filter = f"[1:v]scale=1280:720:force_original_aspect_ratio=decrease,fps=60,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}[webcam_shaped]"
                    if border_width > 0:
                        border_filter = (
                            f"color=c={border_rgb}:s={webcam_size}x{webcam_size}:d=1[border];"
                            f"[border][webcam_shaped]overlay={border_width}:{border_width}[webcam_with_border];"
                        )
                        webcam_output = "[webcam_with_border]"
                    else:
                        border_filter = ""
                        webcam_output = "[webcam_shaped]"
                
                filter_complex = (
                    f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                    f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60[screen];"
                    f"{shape_filter};"
                    f"{border_filter}"
                    f"[screen]{webcam_output}overlay={webcam_x}:{webcam_y}[out]"
                )
                
                cmd = [
                    ffmpeg_path, "-y",
                    "-i", str(screennosilence_path),
                    "-r", "60",
                    "-i", str(webcamnosilence_path),
                    "-filter_complex", filter_complex,
                    "-map", "[out]",
                    "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-vsync", "cfr",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(final_path)
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                
                if process.returncode == 0 and final_path.exists():
                    update_progress(8, "Vidéo finale 16:9", "completed", f"final.mp4 créé ({final_path.stat().st_size // 1024}KB)")
                else:
                    # Fallback: copier nosilence
                    shutil.copy(nosilence_path, final_path)
                    update_progress(8, "Vidéo finale 16:9", "completed", "Copie de nosilence.mp4")
            else:
                # Pas de screen/webcam séparés, utiliser nosilence
                shutil.copy(nosilence_path, final_path)
                update_progress(8, "Vidéo finale 16:9", "completed", "Copie de nosilence.mp4")
        
            # ========== ÉTAPE 9: Vidéo avec B-roll Pexels ==========
            update_progress(9, "Vidéo avec B-roll Pexels", "running", "Insertion des clips d'illustration...")
            
            illustrated_path = folder_path / "illustrated.mp4"
            
            if downloaded_clips and any(c.get("downloaded") for c in downloaded_clips):
                source_video = final_path if final_path.exists() else nosilence_path
                await create_illustrated_video(folder_path, source_video, downloaded_clips)
                
                if illustrated_path.exists():
                    update_progress(9, "Vidéo avec B-roll Pexels", "completed", f"illustrated.mp4 créé ({illustrated_path.stat().st_size // 1024}KB)")
                else:
                    update_progress(9, "Vidéo avec B-roll Pexels", "completed", "Échec création illustrated.mp4")
            else:
                update_progress(9, "Vidéo avec B-roll Pexels", "completed", "Pas de clips à insérer")
        else:
            # Layout simple (screen_only ou webcam_only) - pas de shorts ni fusion complexe
            update_progress(6, "Vidéo finale", "completed", "Layout simple - pas de fusion nécessaire")
        
        # ========== ÉTAPE 10: Génération SEO YouTube ==========
        step_num = 10 if is_full_workflow else 6
        update_progress(step_num, "Génération SEO YouTube", "running", "Génération titre, description, hashtags...")
        
        seo_data = await openrouter.generate_youtube_seo(transcript_text, segments=segments)
        
        if seo_data:
            # Mettre à jour la transcription avec les données SEO
            transcription_path = folder_path / "transcription.json"
            if transcription_path.exists():
                with open(transcription_path, "r", encoding="utf-8") as f:
                    transcription_data = json.load(f)
                transcription_data["seo"] = seo_data
                with open(transcription_path, "w", encoding="utf-8") as f:
                    json.dump(transcription_data, f, ensure_ascii=False, indent=2)
            
            update_progress(step_num, "Génération SEO YouTube", "completed", f"Titre: {seo_data.get('title', '')[:50]}...")
        else:
            update_progress(step_num, "Génération SEO YouTube", "completed", "Échec génération SEO")
        
        # ========== ÉTAPE 11: Génération miniature ==========
        step_num = 11 if is_full_workflow else 7
        update_progress(step_num, "Génération miniature", "running", "Création miniature YouTube...")
        
        thumbnail_path = folder_path / "thumbnail.png"
        
        # Extraire une frame de la webcam pour le personnage
        webcam_frame_path = folder_path / "webcam_frame.jpg"
        webcam_frame_base64 = None
        
        webcam_source = webcamnosilence_path if webcamnosilence_path.exists() else webcam_path
        if webcam_source.exists():
            # Extraire une frame au milieu de la vidéo
            extract_cmd = [
                ffmpeg_path, "-y",
                "-i", str(webcam_source),
                "-ss", str(nosilence_duration / 2),
                "-vframes", "1",
                "-q:v", "2",
                str(webcam_frame_path)
            ]
            subprocess.run(extract_cmd, capture_output=True)
            
            if webcam_frame_path.exists():
                with open(webcam_frame_path, "rb") as f:
                    webcam_frame_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Générer le prompt pour la miniature
        title = seo_data.get("title", "Vidéo YouTube") if seo_data else "Vidéo YouTube"
        thumbnail_prompt = await openrouter.generate_thumbnail_prompt(transcript_text[:2000], title)
        
        if thumbnail_prompt:
            # Générer la miniature avec Gemini
            result = await openrouter.generate_thumbnail_with_gemini(
                thumbnail_prompt,
                webcam_frame_base64=webcam_frame_base64,
                output_path=str(thumbnail_path)
            )
            
            if result and thumbnail_path.exists():
                update_progress(step_num, "Génération miniature", "completed", "thumbnail.png créé")
            else:
                update_progress(step_num, "Génération miniature", "completed", "Miniature non générée (limite Gemini)")
        else:
            update_progress(step_num, "Génération miniature", "completed", "Échec génération prompt miniature")
        
        # Nettoyer le fichier frame temporaire
        webcam_frame_path.unlink(missing_ok=True)
        
        print(f"[PIPELINE {folder_name}] Pipeline terminé avec succès!")
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[PIPELINE {folder_name}] Erreur: {error_msg}")
        traceback.print_exc()
        
        # Marquer l'étape courante comme erreur
        if process_progress.get(folder_name):
            last_progress = process_progress[folder_name][-1]
            if last_progress.status == "running":
                process_progress[folder_name].append(AutoProcessFullProgress(
                    step=last_progress.step,
                    total_steps=last_progress.total_steps,
                    step_name=last_progress.step_name,
                    status="error",
                    message=error_msg[:200],
                    progress_percent=last_progress.progress_percent
                ))


@app.post("/api/auto-process-full")
async def auto_process_full(request: AutoProcessFullRequest, background_tasks: BackgroundTasks):
    """
    Lance le pipeline complet de traitement automatique (11 étapes)
    
    Pour le mode Overlay/Side by Side:
    1. Organisation des fichiers
    2. Détection des silences
    3. Découpe des silences
    4. Transcription
    5. Analyse pour clips Pexels
    6. Détection moments clés (shorts)
    7. Génération des shorts (9:16)
    8. Vidéo finale 16:9 (sans Pexels)
    9. Vidéo finale 16:9 avec B-roll Pexels
    10. Génération SEO YouTube
    11. Génération miniature
    """
    
    folder_path = OUTPUT_DIR / request.folder_name
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    
    # Vérifier que original.mp4 existe
    if not (folder_path / "original.mp4").exists():
        raise HTTPException(status_code=404, detail="original.mp4 non trouvé dans le dossier")
    
    # Initialiser la progression
    process_progress[request.folder_name] = []
    
    # Lancer le pipeline en arrière-plan
    background_tasks.add_task(
        auto_process_full_pipeline,
        request.folder_name,
        request.layout,
        request.silence_threshold,
        request.max_shorts,
        request.webcam_x,
        request.webcam_y,
        request.webcam_size,
        request.webcam_shape,
        request.border_color,
        request.border_width
    )
    
    return {
        "success": True,
        "message": "Pipeline complet lancé",
        "folder_name": request.folder_name,
        "layout": request.layout,
        "total_steps": 11 if request.layout in ['overlay', 'side_by_side'] else 7
    }


@app.get("/api/auto-process-full/progress/{folder_name}")
async def get_auto_process_progress(folder_name: str):
    """Obtenir la progression du pipeline pour un dossier"""
    
    if folder_name not in process_progress:
        return {"progress": [], "is_running": False, "is_complete": False}
    
    progress_list = process_progress[folder_name]
    
    # Déterminer l'état
    is_running = len(progress_list) > 0 and progress_list[-1].status == "running"
    is_complete = len(progress_list) > 0 and (
        progress_list[-1].status == "completed" and 
        progress_list[-1].step == progress_list[-1].total_steps
    )
    has_error = any(p.status == "error" for p in progress_list)
    
    return {
        "progress": [p.dict() for p in progress_list],
        "is_running": is_running,
        "is_complete": is_complete,
        "has_error": has_error,
        "current_step": progress_list[-1].step if progress_list else 0,
        "total_steps": progress_list[-1].total_steps if progress_list else 11
    }


# ============================================================================
# GESTION DES CLÉS API (Settings)
# ============================================================================

CONFIG_FILE = BASE_DIR / "api_keys.json"

class ApiKeysConfig(BaseModel):
    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    pexels_api_key: Optional[str] = None

def load_api_keys() -> dict:
    """Charger les clés API depuis le fichier de configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_api_keys(keys: dict):
    """Sauvegarder les clés API dans le fichier de configuration"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)

def apply_api_keys(keys: dict):
    """Appliquer les clés API aux variables d'environnement"""
    if keys.get("groq_api_key"):
        os.environ["GROQ_API_KEY"] = keys["groq_api_key"]
    if keys.get("openrouter_api_key"):
        os.environ["OPENROUTER_API_KEY"] = keys["openrouter_api_key"]
    if keys.get("pexels_api_key"):
        os.environ["PEXELS_API_KEY"] = keys["pexels_api_key"]

# Charger les clés au démarrage
startup_keys = load_api_keys()
apply_api_keys(startup_keys)

@app.get("/api/settings/keys")
async def get_api_keys():
    """
    Récupérer les clés API configurées (masquées pour la sécurité)
    """
    keys = load_api_keys()
    
    # Masquer les clés pour la sécurité (montrer seulement les 4 derniers caractères)
    def mask_key(key: str) -> str:
        if not key or len(key) < 8:
            return ""
        return "•" * 20 + key[-4:]
    
    return {
        "groq_api_key": mask_key(keys.get("groq_api_key", "")),
        "openrouter_api_key": mask_key(keys.get("openrouter_api_key", "")),
        "pexels_api_key": mask_key(keys.get("pexels_api_key", "")),
        "groq_configured": bool(keys.get("groq_api_key")),
        "openrouter_configured": bool(keys.get("openrouter_api_key")),
        "pexels_configured": bool(keys.get("pexels_api_key"))
    }

@app.post("/api/settings/keys")
async def save_api_keys_endpoint(config: ApiKeysConfig):
    """
    Sauvegarder les clés API
    """
    # Charger les clés existantes
    existing_keys = load_api_keys()
    
    # Mettre à jour seulement les clés fournies (non vides et non masquées)
    if config.groq_api_key and not config.groq_api_key.startswith("•"):
        existing_keys["groq_api_key"] = config.groq_api_key
    if config.openrouter_api_key and not config.openrouter_api_key.startswith("•"):
        existing_keys["openrouter_api_key"] = config.openrouter_api_key
    if config.pexels_api_key and not config.pexels_api_key.startswith("•"):
        existing_keys["pexels_api_key"] = config.pexels_api_key
    
    # Sauvegarder
    save_api_keys(existing_keys)
    
    # Appliquer aux variables d'environnement
    apply_api_keys(existing_keys)
    
    return {"success": True, "message": "Clés API sauvegardées avec succès"}

@app.delete("/api/settings/keys/{key_name}")
async def delete_api_key(key_name: str):
    """
    Supprimer une clé API spécifique
    """
    valid_keys = ["groq_api_key", "openrouter_api_key", "pexels_api_key"]
    if key_name not in valid_keys:
        raise HTTPException(status_code=400, detail="Clé invalide")
    
    keys = load_api_keys()
    if key_name in keys:
        del keys[key_name]
        save_api_keys(keys)
        
        # Supprimer de l'environnement aussi
        env_key = key_name.upper()
        if env_key in os.environ:
            del os.environ[env_key]
    
    return {"success": True, "message": f"Clé {key_name} supprimée"}

@app.get("/api/settings/status")
async def get_api_status():
    """
    Vérifier le statut de configuration des APIs
    """
    keys = load_api_keys()
    
    # Tester les APIs
    groq_ok = bool(keys.get("groq_api_key"))
    openrouter_ok = bool(keys.get("openrouter_api_key"))
    pexels_ok = bool(keys.get("pexels_api_key"))
    
    return {
        "groq": {
            "configured": groq_ok,
            "name": "Groq (Transcription)",
            "description": "Transcription audio rapide et précise"
        },
        "openrouter": {
            "configured": openrouter_ok,
            "name": "OpenRouter (IA)",
            "description": "Suggestions shorts, SEO YouTube, génération miniature"
        },
        "pexels": {
            "configured": pexels_ok,
            "name": "Pexels (B-roll)",
            "description": "Clips vidéo gratuits pour illustrations"
        },
        "all_configured": groq_ok and openrouter_ok and pexels_ok,
        "minimum_configured": groq_ok  # Minimum requis pour fonctionner
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

