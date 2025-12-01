"""
Configuration Celery pour le pipeline vidéo YouTube
- Redis comme broker et backend
- Tâches asynchrones pour chaque étape du pipeline
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Configuration Redis
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Créer l'application Celery
celery_app = Celery(
    'youtube_pipeline',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['tasks']
)

# Configuration Celery
celery_app.conf.update(
    # Sérialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='Europe/Paris',
    enable_utc=True,
    
    # Résultats
    result_expires=86400,  # 24h
    task_track_started=True,
    task_time_limit=3600,  # 1h max par tâche
    task_soft_time_limit=3000,  # 50min soft limit
    
    # Worker
    worker_prefetch_multiplier=1,  # Une tâche à la fois (vidéo = lourd)
    worker_concurrency=2,  # 2 workers max
    
    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Beat scheduler (si besoin de tâches périodiques)
    beat_schedule={},
)

# Toutes les tâches dans la queue par défaut 'celery'
celery_app.conf.task_default_queue = 'celery'
celery_app.conf.task_routes = {}

