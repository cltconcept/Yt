"""
Router TikTok - Préparation des shorts pour upload manuel sur TikTok
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from services.database import db

router = APIRouter(prefix="/api/tiktok", tags=["tiktok"])

OUTPUT_DIR = Path("output")

# Fichier pour stocker le statut TikTok des shorts
TIKTOK_STATUS_FILE = Path("data/tiktok_status.json")


class ShortItem(BaseModel):
    project_id: str
    project_name: str
    folder_name: str
    short_file: str
    short_index: int
    title: str
    description: str
    tags: List[str]
    created_at: str


class MarkPublishedRequest(BaseModel):
    folder_name: str
    short_index: int
    published: bool = True


def load_tiktok_status() -> dict:
    """Charger le statut des publications TikTok"""
    if TIKTOK_STATUS_FILE.exists():
        try:
            with open(TIKTOK_STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_tiktok_status(status: dict):
    """Sauvegarder le statut des publications TikTok"""
    TIKTOK_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TIKTOK_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


@router.get("/shorts")
async def get_all_shorts():
    """
    Récupère tous les shorts disponibles de tous les projets.
    Retourne les métadonnées optimisées pour TikTok.
    """
    shorts = []
    tiktok_status = load_tiktok_status()
    
    try:
        # Récupérer tous les projets (pas seulement completed)
        projects = db.get_all_projects(limit=100)
        
        for project in projects:
            folder_name = project.get("folder_name", "")
            project_id = str(project.get("_id", ""))
            project_name = project.get("name", folder_name)
            created_at = str(project.get("created_at", ""))
            
            # Vérifier le dossier shorts
            shorts_dir = OUTPUT_DIR / folder_name / "shorts"
            if not shorts_dir.exists():
                continue
            
            # Charger les données SEO si disponibles
            seo_data = None
            seo_path = OUTPUT_DIR / folder_name / "seo.json"
            if seo_path.exists():
                try:
                    with open(seo_path, 'r', encoding='utf-8') as f:
                        seo_data = json.load(f)
                except:
                    pass
            
            # Lister les fichiers shorts
            short_files = sorted([f.name for f in shorts_dir.glob("*.mp4")])
            
            for idx, short_file in enumerate(short_files):
                # Récupérer les métadonnées SEO pour ce short
                title = f"Short {idx + 1}"
                description = ""
                tags = []
                
                if seo_data and "shorts" in seo_data:
                    if idx < len(seo_data["shorts"]):
                        short_seo = seo_data["shorts"][idx]
                        title = short_seo.get("title", title)
                        description = short_seo.get("description", "")
                        tags = short_seo.get("tags", [])
                
                # Optimiser pour TikTok (hashtags populaires)
                tiktok_tags = optimize_tags_for_tiktok(tags)
                
                # Vérifier si publié sur TikTok
                status_key = f"{folder_name}_{idx}"
                tiktok_published = tiktok_status.get(status_key, {})
                
                shorts.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "folder_name": folder_name,
                    "short_file": short_file,
                    "short_index": idx,
                    "title": title,
                    "description": description,
                    "tags": tiktok_tags,
                    "created_at": created_at,
                    "tiktok_published": tiktok_published.get("published", False),
                    "tiktok_published_at": tiktok_published.get("published_at")
                })
        
        # Trier par date de création (plus récent en premier)
        shorts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "shorts": shorts,
            "total": len(shorts),
            "published_count": len([s for s in shorts if s.get("tiktok_published")])
        }
    
    except Exception as e:
        print(f"[TikTok] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shorts/mark-published")
async def mark_short_published(request: MarkPublishedRequest):
    """
    Marquer un short comme publié (ou non) sur TikTok.
    """
    tiktok_status = load_tiktok_status()
    status_key = f"{request.folder_name}_{request.short_index}"
    
    if request.published:
        tiktok_status[status_key] = {
            "published": True,
            "published_at": datetime.now().isoformat()
        }
    else:
        # Retirer le marquage
        if status_key in tiktok_status:
            del tiktok_status[status_key]
    
    save_tiktok_status(tiktok_status)
    
    return {
        "success": True,
        "folder_name": request.folder_name,
        "short_index": request.short_index,
        "published": request.published
    }


def optimize_tags_for_tiktok(tags: List[str]) -> List[str]:
    """
    Optimise les tags pour TikTok :
    - Supprime les espaces dans les hashtags
    - Ajoute des hashtags populaires pertinents
    - Limite à 5-8 hashtags (TikTok recommande moins que YouTube)
    """
    # Tags populaires TikTok à ajouter si pertinents
    popular_tiktok_tags = ["fyp", "foryou", "viral", "pourtoi"]
    
    # Nettoyer les tags existants
    cleaned_tags = []
    for tag in tags[:5]:  # Limiter à 5 tags du contenu
        cleaned = tag.replace(" ", "").replace("-", "").lower()
        if cleaned and cleaned not in cleaned_tags:
            cleaned_tags.append(cleaned)
    
    # Ajouter quelques tags populaires TikTok
    for pop_tag in popular_tiktok_tags[:2]:  # Ajouter 2 tags populaires
        if pop_tag not in cleaned_tags:
            cleaned_tags.append(pop_tag)
    
    return cleaned_tags[:8]  # Max 8 hashtags


@router.get("/shorts/{project_id}")
async def get_project_shorts(project_id: str):
    """
    Récupère les shorts d'un projet spécifique pour TikTok.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    folder_name = project.get("folder_name", "")
    shorts_dir = OUTPUT_DIR / folder_name / "shorts"
    
    if not shorts_dir.exists():
        return {"shorts": [], "total": 0}
    
    # Charger SEO
    seo_data = None
    seo_path = OUTPUT_DIR / folder_name / "seo.json"
    if seo_path.exists():
        try:
            with open(seo_path, 'r', encoding='utf-8') as f:
                seo_data = json.load(f)
        except:
            pass
    
    shorts = []
    short_files = sorted([f.name for f in shorts_dir.glob("*.mp4")])
    
    for idx, short_file in enumerate(short_files):
        title = f"Short {idx + 1}"
        description = ""
        tags = []
        
        if seo_data and "shorts" in seo_data:
            if idx < len(seo_data["shorts"]):
                short_seo = seo_data["shorts"][idx]
                title = short_seo.get("title", title)
                description = short_seo.get("description", "")
                tags = short_seo.get("tags", [])
        
        tiktok_tags = optimize_tags_for_tiktok(tags)
        
        shorts.append({
            "project_id": project_id,
            "project_name": project.get("name", folder_name),
            "folder_name": folder_name,
            "short_file": short_file,
            "short_index": idx,
            "title": title,
            "description": description,
            "tags": tiktok_tags,
            "created_at": str(project.get("created_at", ""))
        })
    
    return {
        "shorts": shorts,
        "total": len(shorts)
    }

