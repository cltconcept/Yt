"""
Routes API pour YouTube
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import os

from services.youtube_service import youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

# URL de redirection pour OAuth
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3010')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8010')


class UploadRequest(BaseModel):
    file_path: str
    title: str
    description: str
    tags: Optional[List[str]] = None
    privacy: str = "private"
    is_short: bool = False


class ScheduledUpload(BaseModel):
    type: str  # 'illustrated', 'classroom', 'short'
    file: str
    title: str
    description: str
    tags: List[str] = []
    privacy: str = "public"
    scheduledDate: str
    scheduledTime: str


class ScheduleRequest(BaseModel):
    project_id: str
    folder_name: str
    uploads: List[ScheduledUpload]


class UploadNowRequest(BaseModel):
    project_id: str
    type: str  # 'illustrated', 'classroom', 'short'
    title: str
    privacy: str = "public"


@router.get("/status")
async def get_youtube_status():
    """Vérifier le statut de connexion YouTube"""
    is_connected = youtube_service.is_authenticated()
    channel = None
    
    if is_connected:
        channel = youtube_service.get_channel_info()
    
    return {
        "connected": is_connected,
        "channel": channel
    }


@router.get("/auth/url")
async def get_auth_url():
    """Obtenir l'URL d'authentification OAuth2"""
    redirect_uri = f"{BACKEND_URL}/api/youtube/auth/callback"
    auth_url = youtube_service.get_auth_url(redirect_uri)
    
    if not auth_url:
        raise HTTPException(
            status_code=500, 
            detail="Impossible de générer l'URL d'authentification. Vérifiez que client_secrets.json existe."
        )
    
    return {"auth_url": auth_url}


@router.get("/auth/callback")
async def auth_callback(code: str = Query(...), state: str = Query(None)):
    """Callback OAuth2 - appelé par Google après authentification"""
    redirect_uri = f"{BACKEND_URL}/api/youtube/auth/callback"
    
    success = youtube_service.authenticate(code, redirect_uri)
    
    if success:
        # Rediriger vers le frontend avec succès
        return RedirectResponse(url=f"{FRONTEND_URL}/youtube?auth=success")
    else:
        return RedirectResponse(url=f"{FRONTEND_URL}/youtube?auth=error")


@router.post("/disconnect")
async def disconnect_youtube():
    """Déconnecter le compte YouTube"""
    youtube_service.disconnect()
    return {"message": "Déconnecté de YouTube"}


@router.get("/channel")
async def get_channel_info():
    """Récupérer les informations de la chaîne"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    channel = youtube_service.get_channel_info()
    if not channel:
        raise HTTPException(status_code=404, detail="Chaîne non trouvée")
    
    return channel


@router.get("/videos")
async def get_videos(max_results: int = Query(10, ge=1, le=50)):
    """Récupérer les vidéos récentes"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    videos = youtube_service.get_recent_videos(max_results)
    
    # Séparer vidéos et shorts
    regular_videos = [v for v in videos if not v.get('is_short')]
    shorts = [v for v in videos if v.get('is_short')]
    
    return {
        "videos": regular_videos,
        "shorts": shorts,
        "total": len(videos)
    }


@router.get("/analytics")
async def get_analytics(days: int = Query(28, ge=1, le=365)):
    """Récupérer les analytics de la chaîne"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    analytics = youtube_service.get_analytics(days)
    if not analytics:
        raise HTTPException(status_code=500, detail="Erreur récupération analytics")
    
    return analytics


@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """Récupérer les stats pour le dashboard"""
    if not youtube_service.is_authenticated():
        return {
            "connected": False,
            "channel": None,
            "stats": None
        }
    
    channel = youtube_service.get_channel_info()
    analytics = youtube_service.get_analytics(28)
    recent_videos = youtube_service.get_recent_videos(5)
    
    return {
        "connected": True,
        "channel": channel,
        "analytics": analytics,
        "recent_videos": recent_videos[:3] if recent_videos else [],
        "recent_shorts": [v for v in recent_videos if v.get('is_short')][:3] if recent_videos else []
    }


@router.post("/upload")
async def upload_video(request: UploadRequest):
    """Uploader une vidéo sur YouTube"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    result = youtube_service.upload_video(
        file_path=request.file_path,
        title=request.title,
        description=request.description,
        tags=request.tags,
        privacy=request.privacy,
        is_short=request.is_short
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Erreur lors de l'upload")
    
    return result


@router.post("/upload-now")
async def upload_now(request: UploadNowRequest):
    """Mettre en ligne immédiatement une vidéo"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    from pathlib import Path
    from services.database import db
    
    # Récupérer le projet
    project = db.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    output_dir = Path("/app/output") / project.get('folder_name', '')
    
    # Déterminer le fichier selon le type
    if request.type == 'illustrated':
        file_path = output_dir / "illustrated.mp4"
    elif request.type == 'classroom':
        file_path = output_dir / "nosilence.mp4"
    elif request.type == 'short':
        # Trouver le short par titre
        shorts = project.get('outputs', {}).get('shorts', [])
        short_file = None
        for s in shorts:
            if request.title in s.get('title', '') or s.get('title', '') in request.title:
                short_file = s.get('path')
                break
        if not short_file:
            # Prendre le premier short
            if shorts:
                short_file = shorts[0].get('path')
        if short_file:
            file_path = output_dir / short_file
        else:
            raise HTTPException(status_code=404, detail="Short non trouvé")
    else:
        raise HTTPException(status_code=400, detail="Type invalide")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {file_path}")
    
    # Récupérer le SEO
    outputs = project.get('outputs') or {}
    seo = outputs.get('seo') or {}
    main_seo = seo.get('main_video') or {}
    
    # Préparer les métadonnées
    if request.type == 'short':
        title = request.title if '#Shorts' in request.title else f"{request.title} #Shorts"
        description = f"#Shorts #Short #YouTubeShorts"
        tags = ['Shorts', 'Short', 'YouTubeShorts']
        is_short = True
        privacy = request.privacy
    elif request.type == 'classroom':
        # Classroom est toujours en non répertorié (unlisted)
        title = main_seo.get('title', request.title)
        if title:
            title = f"{title} (Version classroom)"
        else:
            title = f"{request.title} (Version classroom)"
        description = main_seo.get('description', '')
        tags = main_seo.get('tags', [])
        is_short = False
        privacy = 'unlisted'  # Toujours unlisted pour classroom
    else:
        title = main_seo.get('title', request.title)
        description = main_seo.get('description', '')
        tags = main_seo.get('tags', [])
        is_short = False
        privacy = request.privacy
    
    # Upload
    result = youtube_service.upload_video(
        file_path=str(file_path),
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
        is_short=is_short
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Erreur lors de l'upload")
    
    # Upload de la miniature pour les vidéos principales
    if request.type in ['illustrated', 'classroom']:
        thumbnail_path = output_dir / "thumbnail.png"
        if thumbnail_path.exists():
            youtube_service.set_thumbnail(result['id'], str(thumbnail_path))
    
    return {
        "success": True,
        "video_id": result['id'],
        "url": result['url'],
        "title": result['title'],
        "status": result['status']
    }


@router.post("/schedule")
async def schedule_uploads(request: ScheduleRequest):
    """Programmer des uploads sur YouTube"""
    if not youtube_service.is_authenticated():
        raise HTTPException(status_code=401, detail="Non connecté à YouTube")
    
    from pathlib import Path
    from datetime import datetime
    
    output_dir = Path("/app/output") / request.folder_name
    results = []
    errors = []
    
    for upload in request.uploads:
        try:
            # Construire le chemin du fichier
            file_path = output_dir / upload.file
            
            if not file_path.exists():
                errors.append(f"Fichier non trouvé: {upload.file}")
                continue
            
            # Créer la date de publication programmée
            scheduled_datetime = f"{upload.scheduledDate}T{upload.scheduledTime}:00"
            
            # Déterminer si c'est un short
            is_short = upload.type == 'short'
            
            # Pour les shorts, s'assurer que #Shorts est dans le titre
            title = upload.title
            if is_short and '#Shorts' not in title and '#shorts' not in title.lower():
                title = f"{title} #Shorts"
            
            # Pour les shorts, ajouter les hashtags shorts dans la description
            description = upload.description
            if is_short:
                description = f"{description}\n\n#Shorts #Short #YouTubeShorts"
            
            # Classroom est toujours en unlisted et sans programmation
            if upload.type == 'classroom':
                privacy = 'unlisted'
                publish_at = None
                title = f"{title} (Version classroom)" if "(Version classroom)" not in title else title
            else:
                privacy = upload.privacy
                publish_at = scheduled_datetime if upload.privacy == 'public' else None
            
            # Upload avec programmation
            result = youtube_service.upload_video(
                file_path=str(file_path),
                title=title,
                description=description,
                tags=upload.tags + ['Shorts', 'Short', 'YouTubeShorts'] if is_short else upload.tags,
                privacy=privacy,
                is_short=is_short,
                publish_at=publish_at
            )
            
            if result:
                video_id = result.get("id")
                
                # Upload de la miniature pour les vidéos principales (pas les shorts)
                if upload.type in ['illustrated', 'classroom']:
                    thumbnail_path = output_dir / "thumbnail.png"
                    if thumbnail_path.exists():
                        thumbnail_success = youtube_service.set_thumbnail(video_id, str(thumbnail_path))
                        if thumbnail_success:
                            print(f"[Schedule] Miniature uploadée pour {video_id}")
                        else:
                            print(f"[Schedule] Échec miniature pour {video_id}")
                
                results.append({
                    "type": upload.type,
                    "title": title,
                    "video_id": video_id,
                    "url": result.get("url"),
                    "scheduled_for": scheduled_datetime,
                    "status": "scheduled" if upload.privacy == 'public' else "uploaded",
                    "thumbnail": upload.type in ['illustrated', 'classroom']
                })
            else:
                errors.append(f"Échec upload: {title}")
                
        except Exception as e:
            errors.append(f"Erreur {upload.title}: {str(e)}")
    
    return {
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }

