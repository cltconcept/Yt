"""
Router Instagram - Préparation des shorts pour upload manuel sur Instagram Reels
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from datetime import datetime
from typing import List
from pydantic import BaseModel
from services.database import db

router = APIRouter(prefix="/api/instagram", tags=["instagram"])

OUTPUT_DIR = Path("output")

# Fichier pour stocker le statut Instagram des shorts
INSTAGRAM_STATUS_FILE = Path("data/instagram_status.json")


class MarkPublishedRequest(BaseModel):
    folder_name: str
    short_index: int
    published: bool = True


def load_instagram_status() -> dict:
    """Charger le statut des publications Instagram"""
    if INSTAGRAM_STATUS_FILE.exists():
        try:
            with open(INSTAGRAM_STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_instagram_status(status: dict):
    """Sauvegarder le statut des publications Instagram"""
    INSTAGRAM_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INSTAGRAM_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def optimize_tags_for_instagram(tags: List[str]) -> List[str]:
    """
    Optimise les tags pour Instagram :
    - Instagram permet jusqu'à 30 hashtags
    - Recommandé : 5-15 hashtags pertinents
    """
    popular_instagram_tags = ["reels", "reelsinstagram", "viral", "explore", "trending"]
    
    cleaned_tags = []
    for tag in tags[:10]:
        cleaned = tag.replace(" ", "").replace("-", "").lower()
        if cleaned and cleaned not in cleaned_tags:
            cleaned_tags.append(cleaned)
    
    for pop_tag in popular_instagram_tags[:3]:
        if pop_tag not in cleaned_tags:
            cleaned_tags.append(pop_tag)
    
    return cleaned_tags[:15]


@router.get("/shorts")
async def get_all_shorts():
    """
    Récupère tous les shorts disponibles pour Instagram Reels.
    """
    shorts = []
    instagram_status = load_instagram_status()
    
    try:
        projects = db.get_all_projects(limit=100)
        
        for project in projects:
            folder_name = project.get("folder_name", "")
            project_id = str(project.get("_id", ""))
            project_name = project.get("name", folder_name)
            created_at = str(project.get("created_at", ""))
            
            shorts_dir = OUTPUT_DIR / folder_name / "shorts"
            if not shorts_dir.exists():
                continue
            
            seo_data = None
            seo_path = OUTPUT_DIR / folder_name / "seo.json"
            if seo_path.exists():
                try:
                    with open(seo_path, 'r', encoding='utf-8') as f:
                        seo_data = json.load(f)
                except:
                    pass
            
            short_files = sorted([f.name for f in shorts_dir.glob("*.mp4")])
            
            for idx, short_file in enumerate(short_files):
                title = f"Reel {idx + 1}"
                description = ""
                tags = []
                
                if seo_data and "shorts" in seo_data:
                    if idx < len(seo_data["shorts"]):
                        short_seo = seo_data["shorts"][idx]
                        title = short_seo.get("title", title)
                        description = short_seo.get("description", "")
                        tags = short_seo.get("tags", [])
                
                instagram_tags = optimize_tags_for_instagram(tags)
                
                status_key = f"{folder_name}_{idx}"
                instagram_published = instagram_status.get(status_key, {})
                
                shorts.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "folder_name": folder_name,
                    "short_file": short_file,
                    "short_index": idx,
                    "title": title,
                    "description": description,
                    "tags": instagram_tags,
                    "created_at": created_at,
                    "instagram_published": instagram_published.get("published", False),
                    "instagram_published_at": instagram_published.get("published_at")
                })
        
        shorts.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "shorts": shorts,
            "total": len(shorts),
            "published_count": len([s for s in shorts if s.get("instagram_published")])
        }
    
    except Exception as e:
        print(f"[Instagram] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shorts/mark-published")
async def mark_short_published(request: MarkPublishedRequest):
    """
    Marquer un short comme publié (ou non) sur Instagram.
    """
    instagram_status = load_instagram_status()
    status_key = f"{request.folder_name}_{request.short_index}"
    
    if request.published:
        instagram_status[status_key] = {
            "published": True,
            "published_at": datetime.now().isoformat()
        }
    else:
        if status_key in instagram_status:
            del instagram_status[status_key]
    
    save_instagram_status(instagram_status)
    
    return {
        "success": True,
        "folder_name": request.folder_name,
        "short_index": request.short_index,
        "published": request.published
    }


