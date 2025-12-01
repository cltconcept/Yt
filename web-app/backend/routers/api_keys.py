"""
Routes API pour la gestion des clés API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.database import db

router = APIRouter(prefix="/api/settings/keys", tags=["api_keys"])


class ApiKeyUpdate(BaseModel):
    value: str
    description: Optional[str] = None


@router.get("")
async def get_all_api_keys():
    """Récupérer toutes les clés API (valeurs masquées)"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    return db.get_all_api_keys()


@router.get("/{key_name}")
async def get_api_key(key_name: str):
    """Récupérer une clé API spécifique (masquée)"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    keys = db.get_all_api_keys()
    for key in keys:
        if key["name"] == key_name:
            return key

    raise HTTPException(status_code=404, detail="Clé API non trouvée")


@router.put("/{key_name}")
async def set_api_key(key_name: str, data: ApiKeyUpdate):
    """Définir ou mettre à jour une clé API"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    success = db.set_api_key(
        key_name=key_name,
        value=data.value,
        description=data.description or ""
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")

    return {"message": f"Clé {key_name} mise à jour avec succès"}


@router.delete("/{key_name}")
async def delete_api_key(key_name: str):
    """Supprimer une clé API"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    success = db.delete_api_key(key_name)
    if not success:
        raise HTTPException(status_code=404, detail="Clé API non trouvée ou erreur de suppression")

    return {"message": f"Clé {key_name} supprimée avec succès"}


@router.post("/init")
async def init_api_keys():
    """Initialiser les clés API par défaut"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    db.init_default_api_keys()
    return {"message": "Clés API initialisées"}


@router.get("/status")
async def get_api_keys_status():
    """Vérifier le statut des clés API (configurées ou non)"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    keys = db.get_all_api_keys()
    return {
        "configured": sum(1 for k in keys if k["has_value"]),
        "total": len(keys),
        "keys": {k["name"]: k["has_value"] for k in keys}
    }


