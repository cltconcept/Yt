# YouTube Pipeline

Application Python locale pour le traitement automatisé de vidéos YouTube avec transcription, sous-titres et publication.

## Fonctionnalités

- **3 sources vidéo** : fichier local, téléchargement YouTube, enregistrement d'écran
- **Transcription automatique** avec Whisper (faster-whisper)
- **Correction IA** des sous-titres avec OpenRouter (GPT-4o-mini)
- **Incrustation des sous-titres** avec FFmpeg
- **Génération SEO** : titre, description, tags optimisés
- **Publication YouTube** directe avec OAuth

## Prérequis

- Python 3.10+
- FFmpeg installé et dans le PATH
- Clé API OpenRouter

## Installation

```bash
# Cloner le projet
cd C:\Dev\Yt

# Installer les dépendances de base
pip install -r requirements.txt

# Pour la transcription (optionnel, ~2GB)
pip install faster-whisper torch
```

## Configuration

1. Copier `env.template.txt` en `.env`
2. Remplir les clés API :
   - `OPENROUTER_API_KEY` : Clé depuis https://openrouter.ai/keys
   - `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` : Depuis Google Cloud Console

## Utilisation

```bash
python main.py
```

## Structure du projet

```
├── main.py              # Point d'entrée
├── config.py            # Configuration
├── database.py          # SQLite
├── models.py            # Modèles de données
├── gui/
│   ├── app.py           # Fenêtre principale
│   └── widgets.py       # Composants UI
├── services/
│   ├── ffmpeg.py        # Traitement vidéo
│   ├── downloader.py    # Téléchargement YouTube
│   ├── recorder.py      # Enregistrement écran
│   ├── whisper.py       # Transcription
│   ├── openrouter.py    # IA (correction, SEO)
│   └── youtube.py       # API YouTube
└── output/              # Fichiers générés
```

## Pipeline de traitement

1. **Source** : Sélection/téléchargement/enregistrement de la vidéo
2. **Transcription** : Conversion audio → texte avec Whisper
3. **Correction** : Amélioration du texte avec GPT-4o-mini
4. **Sous-titres** : Incrustation avec FFmpeg
5. **SEO** : Génération du titre, description, tags
6. **Publication** : Upload sur YouTube

## Technologies

- **GUI** : CustomTkinter
- **Base de données** : SQLite
- **Transcription** : faster-whisper
- **IA** : OpenRouter (GPT-4o-mini)
- **Vidéo** : FFmpeg, yt-dlp, mss, opencv
- **YouTube** : google-api-python-client
