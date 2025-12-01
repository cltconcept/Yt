"""
Routes API pour la gestion des projets
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from services.database import db, ProjectStatus

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    folder_name: str
    config: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    current_step: Optional[str] = None
    progress: Optional[int] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    folder_name: str
    status: str
    current_step: Optional[str]
    progress: int
    steps: Dict[str, Any]
    outputs: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


@router.get("")
async def get_projects(
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Récupérer tous les projets"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    projects = db.get_all_projects(status=status, limit=limit, skip=skip)
    total = db.count_projects(status=status)

    return {
        "projects": projects,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/stats")
async def get_projects_stats():
    """Récupérer les statistiques des projets"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    return {
        "total": db.count_projects(),
        "created": db.count_projects(status=ProjectStatus.CREATED.value),
        "processing": db.count_projects(status=ProjectStatus.PROCESSING.value),
        "completed": db.count_projects(status=ProjectStatus.COMPLETED.value),
        "failed": db.count_projects(status=ProjectStatus.FAILED.value),
    }


@router.get("/in-progress")
async def get_projects_in_progress():
    """Récupérer les projets en cours de traitement"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    return db.get_projects_in_progress()


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Récupérer un projet par son ID"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    return project


@router.post("")
async def create_project(project: ProjectCreate):
    """Créer un nouveau projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    # Vérifier si un projet avec ce dossier existe déjà
    existing = db.get_project_by_folder(project.folder_name)
    if existing:
        raise HTTPException(status_code=400, detail="Un projet avec ce dossier existe déjà")

    project_id = db.create_project(
        name=project.name,
        folder_name=project.folder_name,
        config=project.config
    )

    if not project_id:
        raise HTTPException(status_code=500, detail="Erreur lors de la création du projet")

    return {"id": project_id, "message": "Projet créé avec succès"}


@router.patch("/{project_id}")
async def update_project(project_id: str, updates: ProjectUpdate):
    """Mettre à jour un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune mise à jour fournie")

    success = db.update_project(project_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")

    return {"message": "Projet mis à jour avec succès"}


@router.delete("/{project_id}")
async def delete_project(project_id: str, delete_files: bool = True):
    """Supprimer un projet et optionnellement ses fichiers"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    folder_name = project.get("folder_name")
    
    # Supprimer les fichiers du dossier output si demandé
    files_deleted = False
    if delete_files and folder_name:
        import shutil
        from pathlib import Path
        
        output_dir = Path("output") / folder_name
        if output_dir.exists():
            try:
                shutil.rmtree(output_dir)
                files_deleted = True
                print(f"[DELETE] Dossier supprimé: {output_dir}")
            except Exception as e:
                print(f"[DELETE] Erreur suppression dossier: {e}")

    # Supprimer l'entrée en base de données
    success = db.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")

    return {
        "message": "Projet supprimé avec succès",
        "files_deleted": files_deleted,
        "folder_name": folder_name
    }


@router.post("/{project_id}/start")
async def start_project_pipeline(project_id: str, start_step: int = 1, end_step: int = 10):
    """Démarrer le pipeline pour un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    # Import Celery task
    try:
        from tasks import process_partial_pipeline
        
        # Lancer la tâche Celery (ajouter output/ au chemin)
        video_folder_path = f"output/{project['folder_name']}"
        task = process_partial_pipeline.delay(
            video_folder_path,
            start_step,
            end_step
        )

        # Mettre à jour le projet avec le task ID
        db.update_project(project_id, {
            "celery_task_id": task.id,
            "status": ProjectStatus.PROCESSING.value
        })

        return {
            "message": "Pipeline démarré",
            "task_id": task.id,
            "project_id": project_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur démarrage pipeline: {str(e)}")


@router.get("/{project_id}/files")
async def get_project_files(project_id: str):
    """Récupérer les fichiers générés d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    import os
    import json
    from pathlib import Path
    
    folder_name = project["folder_name"]
    output_dir = Path("output") / folder_name
    
    result = {
        "illustrated": None,
        "nosilence": None,
        "original": None,
        "thumbnail": None,
        "shorts": [],
        "seo": None,
        "transcription": None,
        "schedule": None
    }
    
    # Vérifier les fichiers vidéo
    if (output_dir / "illustrated.mp4").exists():
        result["illustrated"] = "illustrated.mp4"
    if (output_dir / "nosilence.mp4").exists():
        result["nosilence"] = "nosilence.mp4"
    if (output_dir / "original.mp4").exists():
        result["original"] = "original.mp4"
    if (output_dir / "thumbnail.png").exists():
        result["thumbnail"] = "thumbnail.png"
    
    # Shorts
    shorts_dir = output_dir / "shorts"
    if shorts_dir.exists():
        result["shorts"] = [f.name for f in shorts_dir.glob("*.mp4")]
    
    # SEO
    seo_path = output_dir / "seo.json"
    if seo_path.exists():
        with open(seo_path, 'r', encoding='utf-8') as f:
            result["seo"] = json.load(f)
    
    # Transcription
    transcription_path = output_dir / "transcription.txt"
    if transcription_path.exists():
        with open(transcription_path, 'r', encoding='utf-8') as f:
            result["transcription"] = f.read()
    
    # Schedule (programmation YouTube)
    schedule_path = output_dir / "schedule.json"
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            result["schedule"] = json.load(f)
    
    return result


@router.get("/{project_id}/status")
async def get_project_pipeline_status(project_id: str):
    """Récupérer le statut du pipeline d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    # Si on a un task ID Celery, récupérer son statut
    celery_status = None
    if project.get("celery_task_id"):
        try:
            from celery.result import AsyncResult
            from celery_app import celery_app
            
            result = AsyncResult(project["celery_task_id"], app=celery_app)
            celery_status = {
                "task_id": project["celery_task_id"],
                "state": result.state,
                "info": result.info if result.info else None
            }
        except Exception as e:
            celery_status = {"error": str(e)}

    return {
        "project_id": project_id,
        "status": project["status"],
        "current_step": project.get("current_step"),
        "progress": project.get("progress", 0),
        "steps": project.get("steps", {}),
        "celery": celery_status
    }


@router.get("/{project_id}/logs")
async def get_project_logs(project_id: str, limit: int = Query(100, ge=10, le=500)):
    """Récupérer les logs Celery d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    celery_task_id = project.get("celery_task_id")
    folder_name = project.get("folder_name", "")
    
    if not celery_task_id:
        return {
            "logs": ["[INFO] Aucune tâche Celery associée à ce projet"],
            "task_id": None,
            "task_state": None,
            "total_lines": 0
        }

    try:
        from celery.result import AsyncResult
        from celery_app import celery_app
        
        result = AsyncResult(celery_task_id, app=celery_app)
        task_state = result.state
        
        # Récupérer les logs depuis Celery Flower ou les logs système
        # Pour l'instant, on retourne le statut de la tâche et les infos disponibles
        logs = []
        
        if result.info:
            if isinstance(result.info, dict):
                if "step" in result.info:
                    logs.append(f"[Step {result.info.get('step', '?')}] {result.info.get('status', 'En cours...')}")
                else:
                    logs.append(f"[INFO] {str(result.info)[:200]}")
            else:
                logs.append(f"[INFO] {str(result.info)[:200]}")
        
        # Ajouter le statut actuel du projet
        logs.append(f"[STATUS] Étape {project.get('current_step', '?')}: {project.get('step_name', 'En attente...')}")
        logs.append(f"[PROGRESS] {project.get('progress', 0)}%")
        
        # Si la tâche est en cours, indiquer qu'elle tourne
        if task_state in ['PENDING', 'STARTED', 'PROGRESS']:
            logs.append(f"[ACTIVE] Tâche en cours d'exécution (state: {task_state})")
        elif task_state == 'SUCCESS':
            logs.append("[SUCCESS] Tâche terminée avec succès")
        elif task_state == 'FAILURE':
            logs.append(f"[ERROR] Tâche échouée: {str(result.info)[:200]}")
        
        return {
            "logs": logs,
            "task_id": celery_task_id,
            "task_state": task_state,
            "folder_name": folder_name,
            "total_lines": len(logs)
        }
            
    except Exception as e:
        return {
            "logs": [f"[ERROR] Erreur récupération logs: {str(e)}"],
            "task_id": celery_task_id,
            "task_state": None,
            "total_lines": 0
        }


@router.get("/{project_id}/minio")
async def get_project_minio_files(project_id: str):
    """Récupérer les fichiers MinIO d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    folder_name = project["folder_name"]
    
    try:
        from services.storage import storage
        
        if not storage.is_connected():
            return {"error": "MinIO non connecté", "files": []}
        
        files = storage.list_project_files(folder_name)
        
        # Ajouter les URLs présignées
        for f in files:
            f['url'] = storage.get_presigned_url(f['bucket'], f['name'])
        
        return {
            "project_id": project_id,
            "folder_name": folder_name,
            "files": files,
            "total_size": sum(f.get('size', 0) for f in files)
        }
        
    except Exception as e:
        return {"error": str(e), "files": []}


class CalibrateConfig(BaseModel):
    layout: str = "overlay"
    webcam_x: int = 1486
    webcam_y: int = 645
    webcam_size: int = 389
    webcam_shape: str = "circle"
    border_color: str = "#FFB6C1"
    border_width: int = 4


@router.post("/{project_id}/calibrate")
async def calibrate_project(project_id: str, config: CalibrateConfig):
    """Recréer le fichier config.json d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    import json
    from pathlib import Path
    
    folder_name = project["folder_name"]
    output_dir = Path("output") / folder_name
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Dossier du projet non trouvé")
    
    config_path = output_dir / "config.json"
    
    config_data = {
        "layout": config.layout,
        "webcam_x": config.webcam_x,
        "webcam_y": config.webcam_y,
        "webcam_size": config.webcam_size,
        "webcam_shape": config.webcam_shape,
        "border_color": config.border_color,
        "border_width": config.border_width
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        
        return {
            "message": "Configuration recréée avec succès",
            "config": config_data,
            "path": str(config_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la sauvegarde: {str(e)}")


@router.get("/{project_id}/config")
async def get_project_config(project_id: str):
    """Récupérer le fichier config.json d'un projet"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    import json
    from pathlib import Path
    
    folder_name = project["folder_name"]
    output_dir = Path("output") / folder_name
    config_path = output_dir / "config.json"
    
    if not config_path.exists():
        return {
            "exists": False,
            "config": None,
            "message": "Fichier config.json non trouvé"
        }
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        return {
            "exists": True,
            "config": config_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture: {str(e)}")


@router.post("/{project_id}/reboot")
async def reboot_project(project_id: str):
    """Reboot un projet: stoppe les workers, nettoie les fichiers et relance le pipeline"""
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    import shutil
    from pathlib import Path
    
    folder_name = project["folder_name"]
    output_dir = Path("output") / folder_name
    
    # Fichiers à conserver
    files_to_keep = {"config.json", "screen.mp4", "webcam.mp4"}
    
    # 1. Révoquer la tâche Celery en cours si elle existe
    celery_task_id = project.get("celery_task_id")
    task_revoked = False
    if celery_task_id:
        try:
            from celery_app import celery_app
            celery_app.control.revoke(celery_task_id, terminate=True)
            task_revoked = True
            print(f"[REBOOT] Tâche Celery {celery_task_id} révoquée")
        except Exception as e:
            print(f"[REBOOT] Erreur révocation tâche: {e}")
    
    # 2. Supprimer les fichiers et dossiers sauf ceux à conserver
    files_deleted = []
    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.name not in files_to_keep:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    files_deleted.append(item.name)
                    print(f"[REBOOT] Supprimé: {item.name}")
                except Exception as e:
                    print(f"[REBOOT] Erreur suppression {item.name}: {e}")
    
    # 3. Reset le statut du projet
    db.update_project(project_id, {
        "status": "created",
        "current_step": None,
        "step_name": None,
        "progress": 0,
        "celery_task_id": None,
        "steps": {}
    })
    
    # 4. Relancer le pipeline depuis le début
    try:
        from tasks import process_partial_pipeline
        
        video_folder_path = f"output/{folder_name}"
        task = process_partial_pipeline.delay(video_folder_path, 1, 12)
        
        db.update_project(project_id, {
            "celery_task_id": task.id,
            "status": "processing"
        })
        
        return {
            "message": "Projet rebooté avec succès",
            "task_revoked": task_revoked,
            "files_deleted": files_deleted,
            "files_kept": list(files_to_keep),
            "new_task_id": task.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur relance pipeline: {str(e)}")


@router.post("/{project_id}/stop")
async def stop_pipeline(project_id: str):
    """
    Stoppe le pipeline en cours sans supprimer les fichiers.
    """
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    
    celery_task_id = project.get("celery_task_id")
    task_revoked = False
    
    # Révoquer la tâche Celery en cours
    if celery_task_id:
        try:
            from celery_app import celery_app
            celery_app.control.revoke(celery_task_id, terminate=True, signal='SIGKILL')
            task_revoked = True
            print(f"[STOP] Tâche Celery {celery_task_id} arrêtée")
        except Exception as e:
            print(f"[STOP] Erreur arrêt tâche: {e}")
    
    # Mettre à jour le statut
    current_step = project.get("current_step", 0)
    step_name = project.get("step_name", "")
    
    db.update_project(project_id, {
        "status": "stopped",
        "celery_task_id": None,
        "step_name": f"Arrêté à l'étape {current_step}: {step_name}" if step_name else "Arrêté"
    })
    
    return {
        "message": "Pipeline arrêté",
        "task_revoked": task_revoked,
        "stopped_at_step": current_step,
        "step_name": step_name
    }


class ThumbnailCorrection(BaseModel):
    corrections: str


@router.post("/{project_id}/regenerate-thumbnail")
async def regenerate_project_thumbnail(project_id: str, data: ThumbnailCorrection):
    """
    Régénère la miniature avec des corrections utilisateur.
    Le visage de la webcam est conservé.
    """
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    folder_name = project["folder_name"]
    video_folder_path = f"output/{folder_name}"
    
    try:
        from services.step9_thumbnail import regenerate_thumbnail_with_corrections
        
        result = regenerate_thumbnail_with_corrections(video_folder_path, data.corrections)
        
        if result['success']:
            return {
                "message": "Miniature régénérée avec succès",
                "output_path": result['output_path']
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Échec de la régénération'))
            
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Module non disponible: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur régénération: {str(e)}")


@router.post("/{project_id}/upload")
async def start_youtube_upload(project_id: str):
    """
    Lance l'upload YouTube manuellement (étape 11).
    Disponible uniquement quand le projet est en statut 'ready_to_upload'.
    """
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    # Vérifier que le projet est prêt pour l'upload
    if project.get("status") not in ["ready_to_upload", "completed", "failed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Le projet doit être en statut 'ready_to_upload'. Statut actuel: {project.get('status')}"
        )

    try:
        from tasks import task_step11_upload
        
        # Lancer la tâche d'upload
        video_folder_path = f"output/{project['folder_name']}"
        task = task_step11_upload.delay({
            'video_folder': video_folder_path,
            'success': True
        })

        # Mettre à jour le projet avec le task ID
        db.update_project(project_id, {
            "celery_task_id": task.id,
            "status": "processing",
            "current_step": 11,
            "step_name": "Upload YouTube en cours..."
        })

        return {
            "message": "Upload YouTube lancé",
            "task_id": task.id,
            "project_id": project_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lancement upload: {str(e)}")


class CutSegment(BaseModel):
    start: float
    end: float


class CutRequest(BaseModel):
    cuts: list[CutSegment]


@router.post("/{project_id}/cut")
async def cut_video(project_id: str, request: CutRequest):
    """
    Découpe les fichiers screen.mp4 et webcam.mp4 en supprimant les segments spécifiés,
    puis relance le pipeline depuis le début.
    """
    if not db.is_connected():
        raise HTTPException(status_code=503, detail="Base de données non disponible")

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    import subprocess
    import shutil
    from pathlib import Path
    
    folder_name = project["folder_name"]
    output_dir = Path("output") / folder_name
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Dossier du projet non trouvé")
    
    screen_path = output_dir / "screen.mp4"
    webcam_path = output_dir / "webcam.mp4"
    
    if not screen_path.exists():
        raise HTTPException(status_code=404, detail="screen.mp4 non trouvé")
    
    # Trier les segments par ordre chronologique
    cuts = sorted(request.cuts, key=lambda x: x.start)
    
    if not cuts:
        raise HTTPException(status_code=400, detail="Aucun segment à couper")
    
    # Obtenir la durée totale de la vidéo
    def get_duration(file_path: str) -> float:
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0', file_path
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    
    duration = get_duration(str(screen_path))
    
    # Construire les segments à GARDER (inverse des segments à couper)
    keep_segments = []
    current_start = 0.0
    
    for cut in cuts:
        if cut.start > current_start:
            keep_segments.append({'start': current_start, 'end': cut.start})
        current_start = cut.end
    
    # Ajouter le dernier segment si nécessaire
    if current_start < duration:
        keep_segments.append({'start': current_start, 'end': duration})
    
    if not keep_segments:
        raise HTTPException(status_code=400, detail="Impossible de couper toute la vidéo")
    
    print(f"[CUT] Segments à garder: {keep_segments}")
    
    # Fonction pour découper un fichier
    async def cut_file(input_path: Path, output_path: Path, segments: list):
        temp_dir = output_dir / "temp_cut"
        temp_dir.mkdir(exist_ok=True)
        
        # Créer les segments temporaires
        segment_files = []
        for i, seg in enumerate(segments):
            seg_file = temp_dir / f"seg_{i:03d}.ts"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(input_path),
                '-ss', str(seg['start']),
                '-t', str(seg['end'] - seg['start']),
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-c:a', 'aac', '-b:a', '192k',
                '-f', 'mpegts',
                str(seg_file)
            ]
            proc = subprocess.run(cmd, capture_output=True)
            if seg_file.exists():
                segment_files.append(str(seg_file))
        
        # Concaténer les segments
        if segment_files:
            concat_input = 'concat:' + '|'.join(segment_files)
            cmd = [
                'ffmpeg', '-y',
                '-i', concat_input,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-c:a', 'copy',
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True)
        
        # Nettoyer
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    try:
        # Sauvegarder les originaux
        screen_backup = output_dir / "screen_original.mp4"
        webcam_backup = output_dir / "webcam_original.mp4" if webcam_path.exists() else None
        
        shutil.copy2(screen_path, screen_backup)
        if webcam_path.exists():
            shutil.copy2(webcam_path, webcam_backup)
        
        # Découper screen.mp4
        screen_temp = output_dir / "screen_cut.mp4"
        await cut_file(screen_path, screen_temp, keep_segments)
        
        if screen_temp.exists():
            screen_path.unlink()
            screen_temp.rename(screen_path)
            print(f"[CUT] screen.mp4 découpé avec succès")
        
        # Découper webcam.mp4 si existe
        if webcam_path.exists():
            webcam_temp = output_dir / "webcam_cut.mp4"
            await cut_file(webcam_path, webcam_temp, keep_segments)
            
            if webcam_temp.exists():
                webcam_path.unlink()
                webcam_temp.rename(webcam_path)
                print(f"[CUT] webcam.mp4 découpé avec succès")
        
        # Supprimer les fichiers générés pour relancer le pipeline
        files_to_delete = [
            "original.mp4", "nosilence.mp4", "illustrated.mp4",
            "transcription.json", "transcription.txt",
            "seo.json", "schedule.json", "thumbnail.png",
            "broll_suggestions.json", "broll_clips.json",
            "shorts_suggestions.json"
        ]
        
        for f in files_to_delete:
            file_path = output_dir / f
            if file_path.exists():
                file_path.unlink()
        
        # Supprimer les dossiers shorts et broll
        shorts_dir = output_dir / "shorts"
        broll_dir = output_dir / "broll"
        if shorts_dir.exists():
            shutil.rmtree(shorts_dir)
        if broll_dir.exists():
            shutil.rmtree(broll_dir)
        
        # Relancer le pipeline
        from celery import chain
        from tasks import (
            task_step1_merge, task_step2_silence, task_step3_cut_sources,
            task_step4_transcribe, task_step5_shorts, task_step6_broll,
            task_step7_integrate_broll, task_step8_seo, task_step9_thumbnail,
            task_step10_schedule
        )
        
        # Réinitialiser le projet
        db.update_project(project_id, {
            "status": "processing",
            "current_step": 1,
            "step_name": "Fusion vidéos",
            "progress": 8,
            "outputs": {}
        })
        
        # Lancer le pipeline depuis l'étape 1
        video_folder_path = f"output/{folder_name}"
        pipeline = chain(
            task_step1_merge.s(video_folder_path),
            task_step2_silence.s(),
            task_step3_cut_sources.s(),
            task_step4_transcribe.s(),
            task_step5_shorts.s(),
            task_step6_broll.s(),
            task_step7_integrate_broll.s(),
            task_step8_seo.s(),
            task_step9_thumbnail.s(),
            task_step10_schedule.s(),
        )
        
        result = pipeline.apply_async()
        
        db.update_project(project_id, {"celery_task_id": result.id})
        
        return {
            "success": True,
            "message": f"Vidéo découpée, {len(cuts)} segment(s) supprimé(s). Pipeline relancé.",
            "task_id": result.id,
            "segments_removed": len(cuts),
            "segments_kept": len(keep_segments)
        }
        
    except Exception as e:
        import traceback
        print(f"[CUT] Erreur: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors de la découpe: {str(e)}")


