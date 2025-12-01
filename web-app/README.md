# 🎬 YouTube Pipeline

Application complète pour enregistrer, traiter et optimiser des vidéos YouTube avec génération automatique de shorts, SEO et miniatures.

## ✨ Fonctionnalités

- 📹 **Enregistrement** : Écran + Webcam + Audio
- 🔇 **Suppression des silences** : Automatique avec FFmpeg
- 📝 **Transcription** : Ultra-rapide avec Groq (Whisper)
- 🎬 **Shorts automatiques** : 9:16 avec sous-titres karaoké
- 🎨 **B-roll Pexels** : Illustrations vidéo automatiques
- 🔍 **SEO YouTube** : Titre, description, hashtags optimisés
- 🖼️ **Miniatures IA** : Générées avec Gemini
- 📤 **Upload YouTube** : Publication automatique avec programmation

## 🚀 Installation rapide (Docker)

### Prérequis

- [Docker](https://www.docker.com/get-started) installé
- [Docker Compose](https://docs.docker.com/compose/install/) installé

### Étapes

1. **Cloner le projet**
```bash
git clone <repo-url>
cd youtube-pipeline/web-app
```

2. **Configurer les variables d'environnement**
```bash
cp env.example .env
# Éditer .env avec vos clés API
```

3. **Lancer l'application**
```bash
docker-compose up -d --build
```

4. **Accéder à l'application**
- 🖥️ Frontend : http://localhost:3010
- 🔧 Backend API : http://localhost:8010
- 🌸 Flower (monitoring Celery) : http://localhost:5555
- 🗄️ Mongo Express : http://localhost:8081
- 📦 MinIO Console : http://localhost:9001

5. **Configurer les clés API**
- Aller sur http://localhost:3010/settings
- Entrer vos clés API (voir section "Clés API" ci-dessous)

## 🔑 Clés API

| Service | Utilisation | Obtention | Coût |
|---------|-------------|-----------|------|
| **Groq** | Transcription (requis) | [console.groq.com/keys](https://console.groq.com/keys) | ✅ GRATUIT |
| **OpenRouter** | Shorts, SEO, Miniatures | [openrouter.ai/keys](https://openrouter.ai/keys) | 💰 $5 offerts |
| **Pexels** | Clips B-roll | [pexels.com/api](https://www.pexels.com/api/new/) | ✅ GRATUIT |
| **Google OAuth** | Upload YouTube (optionnel) | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) | ✅ GRATUIT |

### Configuration via l'interface (recommandé)

1. Accéder à http://localhost:3010/settings
2. Entrer chaque clé API
3. Cliquer "Sauvegarder"

### Configuration via .env

```bash
# Copier le fichier exemple
cp env.example .env

# Éditer avec vos clés
nano .env
```

Variables disponibles :
```env
GROQ_API_KEY=gsk_...          # Transcription
OPENROUTER_API_KEY=sk-or-...  # IA (shorts, SEO, miniatures)
PEXELS_API_KEY=...            # Clips B-roll

# Optionnel - Upload YouTube
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 📁 Structure du projet

```
web-app/
├── backend/               # API FastAPI
│   ├── main.py           # Point d'entrée
│   ├── services/         # Services (transcription, IA, etc.)
│   ├── routers/          # Routes API
│   └── assets/           # Fichiers statiques (outro, logo)
├── frontend/             # Application Next.js
│   └── src/app/          # Pages et composants
├── data/                 # Données générées
│   ├── output/           # Vidéos traitées
│   └── uploads/          # Fichiers temporaires
├── docker-compose.yml    # Configuration Docker
└── env.example           # Template variables d'environnement
```

## 🛠️ Commandes Docker

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs en temps réel
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Arrêter les services
docker-compose down

# Reconstruire après modification du code
docker-compose up -d --build

# Nettoyer tout (⚠️ supprime les données)
docker-compose down -v
```

## 💻 Développement local (sans Docker)

### Prérequis
- Python 3.11+
- Node.js 18+
- FFmpeg installé
- Redis (pour Celery)
- MongoDB

### Backend (Python)
```bash
cd backend

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: .\venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd frontend

# Installer les dépendances
npm install

# Lancer en développement
npm run dev
```

### Services Docker (pour dev local)
```bash
# Lancer uniquement Redis, MongoDB, MinIO
docker-compose -f docker-compose.dev.yml up -d
```

## 📝 Workflow de traitement

```
1. 📹 Enregistrement    → screen.mp4 + webcam.mp4
2. 🔗 Fusion            → original.mp4
3. 🔇 Suppression silences → nosilence.mp4
4. 📝 Transcription     → transcription.json
5. 🎬 Génération shorts → shorts/short_*.mp4
6. 🎨 B-roll Pexels     → illustrated.mp4
7. 🔍 SEO               → seo.json (titre, description, hashtags)
8. 🖼️ Miniature         → thumbnail.png
9. 📤 Upload YouTube    → (optionnel)
```

## 🔧 Services inclus

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3010 | Interface utilisateur Next.js |
| Backend | 8010 | API FastAPI |
| Redis | 6379 | Broker pour Celery |
| MongoDB | 27017 | Base de données |
| MinIO | 9000/9001 | Stockage S3 |
| Flower | 5555 | Monitoring Celery |
| Mongo Express | 8081 | Interface MongoDB |

## 🆘 Dépannage

### Les vidéos ne se traitent pas
1. Vérifier les logs Celery : `docker-compose logs -f celery_worker`
2. S'assurer que Redis est démarré
3. Vérifier les clés API dans /settings

### Erreur de transcription
1. Vérifier la clé GROQ_API_KEY
2. S'assurer que le fichier audio n'est pas corrompu

### Erreur miniature/SEO
1. Vérifier la clé OPENROUTER_API_KEY
2. Consulter les logs : `docker-compose logs -f backend`

### Réinitialiser tout
```bash
docker-compose down -v
rm -rf data/output/* data/uploads/*
docker-compose up -d --build
```

## 📄 Licence

MIT
