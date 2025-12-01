"""
Step 10: Programmation YouTube automatique
Programme les uploads avec des dates optimales
"""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Heures optimales pour YouTube (France)
OPTIMAL_HOURS = ['18:00', '19:00', '20:00', '17:00', '12:00', '13:00']

# Meilleurs jours (0 = Lundi, 6 = Dimanche)
BEST_DAYS = [1, 2, 3, 5, 0, 4, 6]  # Mar, Mer, Jeu, Sam, Lun, Ven, Dim


def get_next_optimal_date(start_from: datetime = None, offset_days: int = 0) -> tuple:
    """Trouver la prochaine date optimale pour publier"""
    if start_from is None:
        start_from = datetime.now()
    
    # Commencer à partir de demain + offset
    target = start_from + timedelta(days=1 + offset_days)
    
    # Trouver le prochain meilleur jour
    for _ in range(14):  # Chercher dans les 2 prochaines semaines
        if target.weekday() in BEST_DAYS[:4]:  # Top 4 meilleurs jours
            break
        target += timedelta(days=1)
    
    # Heure optimale
    hour = OPTIMAL_HOURS[offset_days % len(OPTIMAL_HOURS)]
    
    return target.strftime('%Y-%m-%d'), hour


def prepare_schedule(video_folder: str) -> Dict:
    """
    Prépare la programmation automatique des uploads
    
    Args:
        video_folder: Chemin vers le dossier du projet
    
    Returns:
        Dict avec les informations de programmation
    """
    video_folder = Path(video_folder)
    
    print(f"[Step 10] Préparation programmation: {video_folder}")
    
    # Vérifier les fichiers requis
    illustrated_path = video_folder / "illustrated.mp4"
    nosilence_path = video_folder / "nosilence.mp4"
    thumbnail_path = video_folder / "thumbnail.png"
    seo_path = video_folder / "seo.json"
    shorts_dir = video_folder / "shorts"
    
    # Charger le SEO
    seo_data = None
    if seo_path.exists():
        with open(seo_path, 'r', encoding='utf-8') as f:
            seo_data = json.load(f)
    
    schedule = {
        "created_at": datetime.now().isoformat(),
        "status": "ready",
        "uploads": []
    }
    
    now = datetime.now()
    upload_index = 0
    
    # 1. Vidéo principale (Illustrated) - Premier jour optimal à 18h
    if illustrated_path.exists():
        date, time = get_next_optimal_date(now, offset_days=0)
        
        upload = {
            "type": "illustrated",
            "file": "illustrated.mp4",
            "title": seo_data.get('main_video', {}).get('title', 'Vidéo YouTube') if seo_data else 'Vidéo YouTube',
            "description": seo_data.get('main_video', {}).get('description', '') if seo_data else '',
            "tags": seo_data.get('main_video', {}).get('tags', []) if seo_data else [],
            "pinned_comment": seo_data.get('main_video', {}).get('pinned_comment', '') if seo_data else '',
            "privacy": "public",
            "scheduled_date": date,
            "scheduled_time": time,
            "thumbnail": "thumbnail.png" if thumbnail_path.exists() else None,
            "status": "pending"
        }
        schedule["uploads"].append(upload)
        print(f"[Step 10] Illustrated programmée: {date} {time}")
        upload_index += 1
    
    # 2. Vidéo Classroom (Nosilence) - Même jour à 10h (non répertoriée)
    if nosilence_path.exists():
        date, _ = get_next_optimal_date(now, offset_days=0)
        
        classroom_title = f"[Classroom] {seo_data.get('main_video', {}).get('title', 'Cours')}" if seo_data else '[Classroom] Cours'
        
        upload = {
            "type": "classroom",
            "file": "nosilence.mp4",
            "title": classroom_title,
            "description": f"Version complète pour les étudiants.\n\n{seo_data.get('main_video', {}).get('description', '')}" if seo_data else "Version complète pour les étudiants.",
            "tags": seo_data.get('main_video', {}).get('tags', []) if seo_data else [],
            "privacy": "unlisted",
            "scheduled_date": date,
            "scheduled_time": "10:00",
            "thumbnail": "thumbnail.png" if thumbnail_path.exists() else None,
            "status": "pending"
        }
        schedule["uploads"].append(upload)
        print(f"[Step 10] Classroom programmée: {date} 10:00 (non répertoriée)")
    
    # 3. Shorts - Jours suivants, espacés
    if shorts_dir.exists():
        shorts_files = sorted([f for f in shorts_dir.iterdir() if f.suffix == '.mp4'])
        shorts_seo = seo_data.get('shorts', []) if seo_data else []
        
        for i, short_file in enumerate(shorts_files):
            # Espacer les shorts de 1-2 jours
            date, time = get_next_optimal_date(now, offset_days=1 + i)
            
            # Récupérer le SEO du short
            short_seo = shorts_seo[i] if i < len(shorts_seo) else {}
            
            short_title = short_seo.get('title', short_file.stem)
            if '#Shorts' not in short_title and '#shorts' not in short_title.lower():
                short_title = f"{short_title} #Shorts"
            
            # Hashtags
            hashtags = short_seo.get('hashtags', short_seo.get('tags', []))
            hashtags_str = ' '.join([h if h.startswith('#') else f'#{h}' for h in hashtags])
            
            upload = {
                "type": "short",
                "file": f"shorts/{short_file.name}",
                "title": short_title,
                "description": f"{short_seo.get('description', '')}\n\n{hashtags_str}\n\n#Shorts #Short #YouTubeShorts",
                "tags": [h.replace('#', '') for h in hashtags] + ['Shorts', 'Short', 'YouTubeShorts'],
                "privacy": "public",
                "scheduled_date": date,
                "scheduled_time": time,
                "status": "pending"
            }
            schedule["uploads"].append(upload)
            print(f"[Step 10] Short {i+1} programmé: {date} {time}")
    
    # Sauvegarder la programmation
    schedule_path = video_folder / "schedule.json"
    with open(schedule_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    
    print(f"[Step 10] Programmation sauvegardée: {len(schedule['uploads'])} uploads")
    print(f"[Step 10] Fichier: {schedule_path}")
    
    return schedule


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        result = prepare_schedule(folder)
        print(f"\nRésultat: {len(result['uploads'])} uploads programmés")
    else:
        print("Usage: python step10_schedule.py <video_folder>")


