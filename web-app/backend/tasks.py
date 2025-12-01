"""
Tâches Celery pour le pipeline vidéo YouTube
Chaque étape du pipeline est une tâche asynchrone
"""
import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from celery import shared_task, chain, group
from celery.utils.log import get_task_logger

from celery_app import celery_app

logger = get_task_logger(__name__)

# Import des services
from services.step1_merge import merge_videos
from services.step2_silence import remove_silences
from services.step3_cut_sources import cut_sources
from services.step4_transcribe import transcribe_video
from services.step5_shorts import generate_shorts
from services.step6_broll import add_broll
from services.step7_integrate_broll import integrate_broll
from services.step8_seo import generate_seo
from services.step9_thumbnail import generate_thumbnail
from services.step10_schedule import prepare_schedule
from services.step11_upload import upload_to_youtube
from services.database import db
from services.storage import storage

TOTAL_STEPS = 12  # 0 (convert) + 11 étapes

STEP_NAMES = {
    0: "Conversion 60fps",
    1: "Fusion vidéos",
    2: "Suppression silences",
    3: "Découpe sources",
    4: "Transcription",
    5: "Génération shorts",
    6: "Téléchargement B-roll",
    7: "Intégration B-roll",
    8: "Génération SEO",
    9: "Génération miniature",
    10: "Programmation YouTube",
    11: "Upload YouTube"
}


def update_project_status(video_folder: str, step: int, status: str, error: str = None):
    """Met à jour le statut du projet dans MongoDB"""
    try:
        # Extraire le folder_name depuis video_folder (ex: output/video_xxx -> video_xxx)
        folder_name = Path(video_folder).name
        
        # Trouver le projet par folder_name
        project = db.get_project_by_folder(folder_name)
        
        if project:
            update_data = {
                "status": status,
                "current_step": step,
                "step_name": STEP_NAMES.get(step, f"Étape {step}"),
                "progress": int((step / TOTAL_STEPS) * 100)
            }
            if error:
                update_data["error"] = error
            if status == "completed":
                update_data["progress"] = 100
            
            db.update_project(project['_id'], update_data)
            logger.info(f"[DB] Projet {folder_name} mis à jour: step={step}, status={status}")
    except Exception as e:
        logger.warning(f"[DB] Erreur mise à jour projet: {e}")


def run_async(coro):
    """Helper pour exécuter des coroutines async dans Celery"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# FFmpeg path (dans le container Docker)
FFMPEG = "/usr/bin/ffmpeg"


@celery_app.task(bind=True, name='tasks.step0_convert')
def task_step0_convert(self, video_folder: str):
    """
    Étape 0: Conversion des fichiers bruts (WebM/MP4) en MP4 60fps CFR
    - screen_raw.* → screen.mp4
    - webcam_raw.* → webcam.mp4
    """
    logger.info(f"[Step0] Démarrage conversion 60fps pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 0, 'status': 'Conversion 60fps en cours...'})
    update_project_status(video_folder, 0, "processing")
    
    try:
        video_path = Path(video_folder)
        
        # Trouver les fichiers bruts
        screen_raw = None
        webcam_raw = None
        for f in video_path.glob("screen_raw.*"):
            screen_raw = f
            break
        for f in video_path.glob("webcam_raw.*"):
            webcam_raw = f
            break
        
        if not screen_raw or not screen_raw.exists():
            raise FileNotFoundError(f"Fichier screen_raw non trouvé dans {video_folder}")
        
        screen_path = video_path / "screen.mp4"
        webcam_path = video_path / "webcam.mp4"
        
        # Convertir screen (avec audio)
        logger.info(f"[Step0] Conversion screen: {screen_raw} -> screen.mp4")
        screen_cmd = [
            FFMPEG, '-y', '-i', str(screen_raw),
            '-r', '60', '-vsync', 'cfr',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            str(screen_path)
        ]
        result = subprocess.run(screen_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[Step0] Erreur FFmpeg screen: {result.stderr}")
            raise Exception(f"FFmpeg screen failed: {result.stderr[:500]}")
        
        screen_size = screen_path.stat().st_size / 1024 / 1024
        logger.info(f"[Step0] screen.mp4 créé: {screen_size:.1f} MB")
        
        # Convertir webcam (sans audio)
        if webcam_raw and webcam_raw.exists():
            logger.info(f"[Step0] Conversion webcam: {webcam_raw} -> webcam.mp4")
            webcam_cmd = [
                FFMPEG, '-y', '-i', str(webcam_raw),
                '-r', '60', '-vsync', 'cfr',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-an',  # Pas d'audio
                '-movflags', '+faststart',
                str(webcam_path)
            ]
            result = subprocess.run(webcam_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"[Step0] Erreur FFmpeg webcam: {result.stderr}")
                raise Exception(f"FFmpeg webcam failed: {result.stderr[:500]}")
            
            webcam_size = webcam_path.stat().st_size / 1024 / 1024
            logger.info(f"[Step0] webcam.mp4 créé: {webcam_size:.1f} MB")
        
        # Supprimer les fichiers bruts
        screen_raw.unlink(missing_ok=True)
        if webcam_raw:
            webcam_raw.unlink(missing_ok=True)
        logger.info(f"[Step0] Fichiers bruts supprimés")
        
        logger.info(f"[Step0] Conversion terminée avec succès")
        return {'success': True, 'step': 0, 'video_folder': video_folder}
        
    except Exception as e:
        logger.error(f"[Step0] Erreur: {str(e)}")
        update_project_status(video_folder, 0, "failed", str(e))
        raise


@celery_app.task(bind=True, name='tasks.step1_merge')
def task_step1_merge(self, result_or_folder):
    """
    Étape 1: Fusion screen + webcam → original.mp4
    Accepte soit un dict (résultat de step0) soit un str (chemin direct)
    """
    # Extraire video_folder du résultat ou utiliser directement
    if isinstance(result_or_folder, dict):
        video_folder = result_or_folder.get('video_folder')
    else:
        video_folder = result_or_folder
    
    logger.info(f"[Step1] Démarrage merge pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 1, 'status': 'Fusion des vidéos...'})
    update_project_status(video_folder, 1, "processing")
    
    try:
        result = merge_videos(video_folder)
        if result.get('success'):
            logger.info(f"[Step1] OK: {result.get('output_path')}")
            return {'success': True, 'step': 1, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step1] Erreur: {e}")
        update_project_status(video_folder, 1, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 1, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step2_silence')
def task_step2_silence(self, previous_result: dict):
    """
    Étape 2: Suppression des silences → nosilence.mp4
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step2] Démarrage suppression silences pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 2, 'status': 'Suppression des silences...'})
    update_project_status(video_folder, 2, "processing")
    
    try:
        result = remove_silences(video_folder)
        if result.get('success'):
            logger.info(f"[Step2] OK: {result.get('output_path')}")
            return {'success': True, 'step': 2, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step2] Erreur: {e}")
        update_project_status(video_folder, 2, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 2, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step3_cut_sources')
def task_step3_cut_sources(self, previous_result: dict):
    """
    Étape 3: Couper les sources → screennosilence.mp4, webcamnosilence.mp4
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step3] Démarrage découpe sources pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 3, 'status': 'Découpe des sources...'})
    update_project_status(video_folder, 3, "processing")
    
    try:
        result = cut_sources(video_folder)
        if result.get('success'):
            logger.info(f"[Step3] OK")
            return {'success': True, 'step': 3, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step3] Erreur: {e}")
        update_project_status(video_folder, 3, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 3, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step4_transcribe')
def task_step4_transcribe(self, previous_result: dict):
    """
    Étape 4: Transcription → transcription.json, transcription.txt
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step4] Démarrage transcription pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 4, 'status': 'Transcription en cours...'})
    update_project_status(video_folder, 4, "processing")
    
    try:
        result = transcribe_video(video_folder)
        if result.get('success'):
            logger.info(f"[Step4] OK")
            return {'success': True, 'step': 4, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step4] Erreur: {e}")
        update_project_status(video_folder, 4, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 4, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step5_shorts')
def task_step5_shorts(self, previous_result: dict):
    """
    Étape 5: Génération des shorts → shorts/*.mp4
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step5] Démarrage génération shorts pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 5, 'status': 'Génération des shorts...'})
    update_project_status(video_folder, 5, "processing")
    
    try:
        result = generate_shorts(video_folder)
        if result.get('success'):
            logger.info(f"[Step5] OK: {len(result.get('shorts', []))} shorts générés")
            return {'success': True, 'step': 5, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step5] Erreur: {e}")
        update_project_status(video_folder, 5, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 5, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step6_broll')
def task_step6_broll(self, previous_result: dict):
    """
    Étape 6: Téléchargement B-roll → broll/*.mp4
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step6] Démarrage téléchargement B-roll pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 6, 'status': 'Téléchargement B-roll...'})
    update_project_status(video_folder, 6, "processing")
    
    try:
        result = add_broll(video_folder)
        if result.get('success'):
            logger.info(f"[Step6] OK: {len(result.get('clips', []))} clips téléchargés")
            return {'success': True, 'step': 6, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step6] Erreur: {e}")
        update_project_status(video_folder, 6, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 6, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step7_integrate_broll')
def task_step7_integrate_broll(self, previous_result: dict):
    """
    Étape 7: Intégration B-roll → illustrated.mp4
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step7] Démarrage intégration B-roll pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 7, 'status': 'Intégration B-roll...'})
    update_project_status(video_folder, 7, "processing")
    
    try:
        result = integrate_broll(video_folder)
        if result.get('success'):
            logger.info(f"[Step7] OK: {result.get('output_path')}")
            return {'success': True, 'step': 7, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step7] Erreur: {e}")
        update_project_status(video_folder, 7, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 7, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step8_seo')
def task_step8_seo(self, previous_result: dict):
    """
    Étape 8: Génération SEO → seo.json
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step8] Démarrage génération SEO pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 8, 'status': 'Génération SEO...'})
    update_project_status(video_folder, 8, "processing")
    
    try:
        result = generate_seo(video_folder)
        if result.get('success'):
            logger.info(f"[Step8] OK")
            return {'success': True, 'step': 8, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step8] Erreur: {e}")
        update_project_status(video_folder, 8, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 8, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step9_thumbnail')
def task_step9_thumbnail(self, previous_result: dict):
    """
    Étape 9: Génération miniature → thumbnail.png
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step9] Démarrage génération miniature pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 9, 'status': 'Génération miniature...'})
    update_project_status(video_folder, 9, "processing")
    
    try:
        result = generate_thumbnail(video_folder)
        if result.get('success'):
            logger.info(f"[Step9] OK: {result.get('output_path')}")
            return {'success': True, 'step': 9, 'video_folder': video_folder}
        else:
            raise Exception(result.get('error', 'Erreur inconnue'))
    except Exception as e:
        logger.error(f"[Step9] Erreur: {e}")
        update_project_status(video_folder, 9, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 9, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step10_schedule')
def task_step10_schedule(self, previous_result: dict):
    """
    Étape 10: Programmation YouTube → schedule.json + Upload MinIO
    Prépare les uploads avec dates optimales et sauvegarde dans MinIO
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step10] Démarrage programmation YouTube pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 10, 'status': 'Programmation YouTube...'})
    update_project_status(video_folder, 10, "processing")
    
    try:
        result = prepare_schedule(video_folder)
        
        # Mettre à jour les outputs du projet
        folder_name = Path(video_folder).name
        project = db.get_project_by_folder(folder_name)
        
        # Upload vers MinIO
        minio_files = {}
        try:
            logger.info(f"[Step10] Upload vers MinIO...")
            minio_files = storage.upload_project_folder(video_folder)
            logger.info(f"[Step10] MinIO: {len(minio_files)} fichiers uploadés")
        except Exception as minio_err:
            logger.warning(f"[Step10] MinIO non disponible: {minio_err}")
        
        if project:
            # Récupérer les outputs existants et ajouter le schedule + minio
            outputs = project.get('outputs', {})
            outputs['schedule'] = result
            outputs['minio'] = minio_files
            
            # Marquer comme prêt pour upload (l'utilisateur doit lancer manuellement l'étape 11)
            db.update_project(project['_id'], {
                'outputs': outputs,
                'status': 'ready_to_upload',
                'progress': 90,
                'current_step': 10,
                'step_name': 'Prêt pour upload YouTube'
            })
        
        logger.info(f"[Step10] OK: {len(result.get('uploads', []))} uploads programmés - Prêt pour upload")
        return {'success': True, 'step': 10, 'video_folder': video_folder, 'schedule': result, 'minio': minio_files}
    except Exception as e:
        logger.error(f"[Step10] Erreur: {e}")
        update_project_status(video_folder, 10, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 10, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.step11_upload')
def task_step11_upload(self, previous_result: dict):
    """
    Étape 11: Upload automatique vers YouTube
    Upload toutes les vidéos programmées
    """
    video_folder = previous_result.get('video_folder')
    logger.info(f"[Step11] Démarrage upload YouTube pour {video_folder}")
    self.update_state(state='PROGRESS', meta={'step': 11, 'status': 'Upload YouTube...'})
    update_project_status(video_folder, 11, "processing")
    
    try:
        result = upload_to_youtube(video_folder)
        
        # Mettre à jour les outputs du projet
        folder_name = Path(video_folder).name
        project = db.get_project_by_folder(folder_name)
        
        if project:
            outputs = project.get('outputs', {})
            outputs['youtube_uploads'] = result
            
            # Marquer comme terminé
            db.update_project(project['_id'], {
                'outputs': outputs,
                'status': 'completed',
                'progress': 100,
                'current_step': 11,
                'step_name': 'Terminé - Uploadé sur YouTube'
            })
        
        uploaded_count = len(result.get('uploads', []))
        error_count = len(result.get('errors', []))
        
        logger.info(f"[Step11] OK: {uploaded_count} uploadés, {error_count} erreurs")
        update_project_status(video_folder, 11, "completed")
        
        return {
            'success': result.get('success', False),
            'step': 11,
            'video_folder': video_folder,
            'completed': True,
            'youtube': result
        }
        
    except Exception as e:
        logger.error(f"[Step11] Erreur: {e}")
        update_project_status(video_folder, 11, "error", str(e))
        self.update_state(state='FAILURE', meta={'step': 11, 'error': str(e)})
        raise


@celery_app.task(bind=True, name='tasks.process_full_pipeline')
def process_full_pipeline(self, video_folder: str):
    """
    Pipeline complet: enchaîne toutes les étapes (1-10)
    S'arrête à l'étape 10 (schedule) - L'upload YouTube nécessite une approbation manuelle
    """
    logger.info(f"[Pipeline] Démarrage pipeline complet pour {video_folder}")
    
    # Créer la chaîne de tâches (10 étapes - upload manuel requis)
    pipeline = chain(
        task_step1_merge.s(video_folder),
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
    
    # Exécuter la chaîne
    result = pipeline.apply_async()
    
    return {
        'pipeline_id': result.id,
        'video_folder': video_folder,
        'status': 'started'
    }


@celery_app.task(bind=True, name='tasks.process_partial_pipeline')
def process_partial_pipeline(self, video_folder: str, start_step: int = 1, end_step: int = 11):
    """
    Pipeline partiel: exécute seulement certaines étapes
    """
    logger.info(f"[Pipeline] Démarrage partiel steps {start_step}-{end_step} pour {video_folder}")
    
    # Mapping des étapes
    steps = {
        1: task_step1_merge,
        2: task_step2_silence,
        3: task_step3_cut_sources,
        4: task_step4_transcribe,
        5: task_step5_shorts,
        6: task_step6_broll,
        7: task_step7_integrate_broll,
        8: task_step8_seo,
        9: task_step9_thumbnail,
        10: task_step10_schedule,
        11: task_step11_upload,
    }
    
    # Construire la chaîne partielle
    selected_steps = []
    for i in range(start_step, end_step + 1):
        if i in steps:
            selected_steps.append(steps[i].s())
    
    if not selected_steps:
        return {'error': 'Aucune étape sélectionnée'}
    
    # La première étape prend le video_folder directement
    first_task = selected_steps[0]
    if start_step == 1:
        first_task = steps[1].s(video_folder)
    else:
        # Pour les étapes > 1, on simule le résultat précédent
        first_task = steps[start_step].s({'video_folder': video_folder, 'success': True})
    
    # Construire et exécuter la chaîne
    if len(selected_steps) > 1:
        pipeline = chain(first_task, *selected_steps[1:])
    else:
        pipeline = first_task
    
    result = pipeline.apply_async()
    
    return {
        'pipeline_id': result.id,
        'video_folder': video_folder,
        'start_step': start_step,
        'end_step': end_step,
        'status': 'started'
    }

