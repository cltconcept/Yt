"""
Step 11: Upload automatique vers YouTube
Upload les vidéos programmées avec les dates optimales
"""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

def upload_to_youtube(video_folder: str) -> Dict:
    """
    Upload automatique de toutes les vidéos vers YouTube
    
    Args:
        video_folder: Chemin vers le dossier du projet
    
    Returns:
        Dict avec les résultats des uploads
    """
    video_folder = Path(video_folder)
    
    print(f"[Step 11] Upload YouTube automatique: {video_folder}")
    
    # Charger le schedule
    schedule_path = video_folder / "schedule.json"
    if not schedule_path.exists():
        return {"success": False, "error": "schedule.json non trouvé"}
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    
    uploads = schedule.get('uploads', [])
    if not uploads:
        return {"success": False, "error": "Aucun upload programmé"}
    
    # Importer le service YouTube
    try:
        from services.youtube_service import youtube_service
    except ImportError as e:
        print(f"[Step 11] Erreur import youtube_service: {e}")
        return {"success": False, "error": f"Service YouTube non disponible: {e}"}
    
    # Vérifier l'authentification
    if not youtube_service.is_authenticated():
        print("[Step 11] YouTube non authentifié!")
        return {"success": False, "error": "YouTube non connecté. Connectez-vous d'abord."}
    
    results = {
        "success": True,
        "uploads": [],
        "errors": []
    }
    
    for upload in uploads:
        upload_type = upload.get('type')
        file_name = upload.get('file')
        title = upload.get('title', 'Vidéo sans titre')
        description = upload.get('description', '')
        tags = upload.get('tags', [])
        privacy = upload.get('privacy', 'public')
        scheduled_date = upload.get('scheduled_date')
        scheduled_time = upload.get('scheduled_time', '18:00')
        
        # Construire le chemin du fichier
        file_path = video_folder / file_name
        if not file_path.exists():
            error_msg = f"Fichier non trouvé: {file_name}"
            print(f"[Step 11] {error_msg}")
            results["errors"].append({"type": upload_type, "error": error_msg})
            continue
        
        # Calculer la date de publication
        publish_at = None
        if scheduled_date and scheduled_time:
            try:
                publish_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
                # Si la date est dans le passé, programmer pour demain
                if publish_datetime <= datetime.now():
                    publish_datetime = datetime.now() + timedelta(hours=1)
                publish_at = publish_datetime.isoformat() + "Z"
            except ValueError:
                pass
        
        # Gestion de la confidentialité selon le type
        # - unlisted: reste unlisted sans programmation (classroom)
        # - public programmé: private temporairement puis public à la date
        final_privacy = privacy
        final_publish_at = publish_at
        
        if privacy == 'unlisted':
            # Vidéos non répertoriées: pas de programmation
            final_publish_at = None
        elif publish_at and privacy == 'public':
            # Public programmé: private temporairement
            final_privacy = 'private'
        
        print(f"[Step 11] Upload {upload_type}: {title}")
        print(f"[Step 11]   Fichier: {file_path}")
        print(f"[Step 11]   Privacy: {final_privacy}")
        if final_publish_at:
            print(f"[Step 11]   Programmé: {final_publish_at}")
        
        try:
            # Déterminer si c'est un short
            is_short = upload_type == 'short'
            
            # Upload vers YouTube
            result = youtube_service.upload_video(
                file_path=str(file_path),
                title=title,
                description=description,
                tags=tags,
                privacy=final_privacy,
                publish_at=final_publish_at,
                is_short=is_short
            )
            
            if result:
                video_id = result.get('id')
                video_url = result.get('url', f"https://youtube.com/watch?v={video_id}")
                
                print(f"[Step 11] ✓ {upload_type} uploadé: {video_url}")
                
                # Upload de la miniature pour les vidéos principales
                if upload_type in ['illustrated', 'classroom']:
                    thumbnail_path = video_folder / "thumbnail.png"
                    if thumbnail_path.exists():
                        try:
                            youtube_service.set_thumbnail(video_id, str(thumbnail_path))
                            print(f"[Step 11]   Miniature uploadée")
                        except Exception as thumb_err:
                            print(f"[Step 11]   Erreur miniature: {thumb_err}")
                
                results["uploads"].append({
                    "type": upload_type,
                    "title": title,
                    "video_id": video_id,
                    "url": video_url,
                    "status": "uploaded",
                    "privacy": final_privacy,
                    "scheduled": final_publish_at
                })
            else:
                error_msg = "Échec upload (résultat vide)"
                print(f"[Step 11] ✗ {upload_type}: {error_msg}")
                results["errors"].append({"type": upload_type, "title": title, "error": error_msg})
                
        except Exception as e:
            error_msg = str(e)
            print(f"[Step 11] ✗ {upload_type}: {error_msg}")
            results["errors"].append({"type": upload_type, "title": title, "error": error_msg})
    
    # Mettre à jour le schedule avec les résultats
    schedule['upload_results'] = results
    schedule['uploaded_at'] = datetime.now().isoformat()
    
    with open(schedule_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    
    # Résumé
    uploaded_count = len(results["uploads"])
    error_count = len(results["errors"])
    print(f"[Step 11] Terminé: {uploaded_count} uploadés, {error_count} erreurs")
    
    if error_count > 0 and uploaded_count == 0:
        results["success"] = False
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        result = upload_to_youtube(folder)
        print(f"\nRésultat: {result}")
    else:
        print("Usage: python step11_upload.py <video_folder>")

