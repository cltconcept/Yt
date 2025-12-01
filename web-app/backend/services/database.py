"""
Service MongoDB pour la gestion des projets
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from bson import ObjectId
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoClient = None
    Collection = None
    ObjectId = None

from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'youtube_pipeline')


class ProjectStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class PipelineStep(str, Enum):
    MERGE = "merge"
    SILENCE = "silence"
    CUT_SOURCES = "cut_sources"
    TRANSCRIBE = "transcribe"
    SHORTS = "shorts"
    BROLL = "broll"
    INTEGRATE_BROLL = "integrate_broll"
    SEO = "seo"
    THUMBNAIL = "thumbnail"


class DatabaseService:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not MONGODB_AVAILABLE:
            print("[DB] PyMongo non disponible. Installez: pip install pymongo")
            return
        
        if self._client is None:
            try:
                self._client = MongoClient(MONGODB_URL)
                self._db = self._client[MONGODB_DB]
                # Test connexion
                self._client.admin.command('ping')
                print(f"[DB] Connecté à MongoDB: {MONGODB_URL}")
            except Exception as e:
                print(f"[DB] Erreur connexion MongoDB: {e}")
                self._client = None
                self._db = None

    @property
    def projects(self) -> Optional[Collection]:
        if self._db is None:
            return None
        return self._db.projects

    def is_connected(self) -> bool:
        return self._client is not None and self._db is not None

    # ==================== PROJETS ====================

    def create_project(
        self,
        name: str,
        folder_name: str,
        config: Dict[str, Any] = None,
        status: str = None
    ) -> Optional[str]:
        """Créer un nouveau projet"""
        if not self.is_connected():
            return None

        # Status par défaut ou personnalisé
        initial_status = status if status else ProjectStatus.CREATED.value

        project = {
            "name": name,
            "folder_name": folder_name,
            "status": initial_status,
            "current_step": None,
            "step_name": None,  # Nom de l'étape en cours pour affichage
            "progress": 0,
            "config": config or {},
            "steps": {
                "convert": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "merge": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "silence": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "cut_sources": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "transcribe": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "shorts": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "broll": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "integrate_broll": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "seo": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
                "thumbnail": {"status": "pending", "started_at": None, "completed_at": None, "error": None},
            },
            "outputs": {
                "original": None,
                "nosilence": None,
                "illustrated": None,
                "thumbnail": None,
                "shorts": [],
                "seo": None,
            },
            "celery_task_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
        }

        result = self.projects.insert_one(project)
        return str(result.inserted_id)

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Récupérer un projet par son ID"""
        if not self.is_connected():
            return None

        try:
            project = self.projects.find_one({"_id": ObjectId(project_id)})
            if project:
                project["_id"] = str(project["_id"])
            return project
        except Exception as e:
            print(f"[DB] Erreur get_project: {e}")
            return None

    def get_project_by_folder(self, folder_name: str) -> Optional[Dict]:
        """Récupérer un projet par son nom de dossier"""
        if not self.is_connected():
            return None

        project = self.projects.find_one({"folder_name": folder_name})
        if project:
            project["_id"] = str(project["_id"])
        return project

    def get_all_projects(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """Récupérer tous les projets"""
        if not self.is_connected():
            return []

        query = {}
        if status:
            query["status"] = status

        projects = list(
            self.projects.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        for project in projects:
            project["_id"] = str(project["_id"])

        return projects

    def get_projects_in_progress(self) -> List[Dict]:
        """Récupérer les projets en cours de traitement"""
        return self.get_all_projects(status=ProjectStatus.PROCESSING.value)

    def count_projects(self, status: Optional[str] = None) -> int:
        """Compter les projets"""
        if not self.is_connected():
            return 0

        query = {}
        if status:
            query["status"] = status

        return self.projects.count_documents(query)

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Mettre à jour un projet"""
        if not self.is_connected():
            return False

        try:
            updates["updated_at"] = datetime.utcnow()
            result = self.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[DB] Erreur update_project: {e}")
            return False

    def update_project_status(
        self,
        project_id: str,
        status: ProjectStatus,
        current_step: Optional[str] = None,
        progress: Optional[int] = None
    ) -> bool:
        """Mettre à jour le statut d'un projet"""
        updates = {"status": status.value}
        if current_step is not None:
            updates["current_step"] = current_step
        if progress is not None:
            updates["progress"] = progress
        if status == ProjectStatus.COMPLETED:
            updates["completed_at"] = datetime.utcnow()

        return self.update_project(project_id, updates)

    def update_step_status(
        self,
        project_id: str,
        step: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """Mettre à jour le statut d'une étape"""
        if not self.is_connected():
            return False

        try:
            update_data = {
                f"steps.{step}.status": status,
                "updated_at": datetime.utcnow()
            }

            if status == "processing":
                update_data[f"steps.{step}.started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                update_data[f"steps.{step}.completed_at"] = datetime.utcnow()

            if error:
                update_data[f"steps.{step}.error"] = error

            result = self.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[DB] Erreur update_step_status: {e}")
            return False

    def set_celery_task_id(self, project_id: str, task_id: str) -> bool:
        """Associer un task ID Celery au projet"""
        return self.update_project(project_id, {"celery_task_id": task_id})

    def delete_project(self, project_id: str) -> bool:
        """Supprimer un projet"""
        if not self.is_connected():
            return False

        try:
            result = self.projects.delete_one({"_id": ObjectId(project_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[DB] Erreur delete_project: {e}")
            return False


    # ==================== CLÉS API ====================

    @property
    def api_keys(self) -> Optional[Collection]:
        if self._db is None:
            return None
        return self._db.api_keys

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Récupérer une clé API par son nom"""
        if not self.is_connected():
            return None

        doc = self.api_keys.find_one({"name": key_name})
        if doc:
            return doc.get("value")
        return None

    def set_api_key(self, key_name: str, value: str, description: str = "") -> bool:
        """Définir ou mettre à jour une clé API"""
        if not self.is_connected():
            return False

        try:
            result = self.api_keys.update_one(
                {"name": key_name},
                {
                    "$set": {
                        "name": key_name,
                        "value": value,
                        "description": description,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            print(f"[DB] Erreur set_api_key: {e}")
            return False

    def delete_api_key(self, key_name: str) -> bool:
        """Supprimer une clé API"""
        if not self.is_connected():
            return False

        try:
            result = self.api_keys.delete_one({"name": key_name})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[DB] Erreur delete_api_key: {e}")
            return False

    def get_all_api_keys(self) -> List[Dict]:
        """Récupérer toutes les clés API (avec valeurs masquées)"""
        if not self.is_connected():
            return []

        keys = list(self.api_keys.find())
        result = []
        for key in keys:
            value = key.get("value", "")
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            result.append({
                "name": key.get("name"),
                "masked_value": masked_value,
                "description": key.get("description", ""),
                "has_value": bool(value),
                "updated_at": key.get("updated_at")
            })
        return result

    def get_api_keys_dict(self) -> Dict[str, str]:
        """Récupérer toutes les clés API comme dictionnaire"""
        if not self.is_connected():
            return {}

        keys = list(self.api_keys.find())
        return {key.get("name"): key.get("value", "") for key in keys}

    def init_default_api_keys(self):
        """Initialiser les clés API par défaut si elles n'existent pas"""
        default_keys = [
            {"name": "OPENROUTER_API_KEY", "description": "Clé API OpenRouter pour GPT/Claude/Gemini"},
            {"name": "GROQ_API_KEY", "description": "Clé API Groq pour Whisper transcription"},
            {"name": "PEXELS_API_KEY", "description": "Clé API Pexels pour les B-roll"},
            {"name": "GOOGLE_CLIENT_ID", "description": "Google OAuth Client ID (YouTube)"},
            {"name": "GOOGLE_CLIENT_SECRET", "description": "Google OAuth Client Secret (YouTube)"},
        ]

        for key_info in default_keys:
            existing = self.api_keys.find_one({"name": key_info["name"]})
            if not existing:
                self.api_keys.insert_one({
                    "name": key_info["name"],
                    "value": "",
                    "description": key_info["description"],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                print(f"[DB] Clé API initialisée: {key_info['name']}")


# Instance singleton
db = DatabaseService()

