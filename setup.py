#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Pipeline - Setup Wizard
Ce script configure automatiquement l'environnement pour le projet.
"""

import os
import sys
import subprocess
import platform
import shutil
import urllib.request
import zipfile
import tempfile
from pathlib import Path

# Fixer l'encodage pour Windows
if platform.system() == 'Windows':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================================
# CONFIGURATION
# ============================================================================

FFMPEG_WINDOWS_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# Couleurs ANSI pour le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def supports_color():
    """Verifie si le terminal supporte les couleurs"""
    if platform.system() == 'Windows':
        os.system('color')
        return True
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

USE_COLORS = supports_color()

def c(text, color):
    """Applique une couleur au texte"""
    if USE_COLORS:
        return f"{color}{text}{Colors.END}"
    return text

# ============================================================================
# AFFICHAGE
# ============================================================================

def print_banner():
    """Affiche la banniere de bienvenue"""
    banner = r"""
    __  __            ______      __            ____  _            ___          
    \ \/ /___  __  __/_  __/_  __/ /_  ___     / __ \(_)___  ___  / (_)___  ___ 
     \  / __ \/ / / / / / / / / / __ \/ _ \   / /_/ / / __ \/ _ \/ / / __ \/ _ \
     / / /_/ / /_/ / / / / /_/ / /_/ /  __/  / ____/ / /_/ /  __/ / / / / /  __/
    /_/\____/\__,_/ /_/  \__,_/_.___/\___/  /_/   /_/ .___/\___/_/_/_/ /_/\___/ 
                                                   /_/                          
    
                          [[ Setup Wizard v1.0 ]]
    """
    print(c(banner, Colors.CYAN))
    print(c("=" * 76, Colors.BLUE))
    print()

def print_step(step_num, total, title):
    """Affiche un titre d'etape"""
    print()
    print(c("=" * 76, Colors.BLUE))
    print(c(f"  [{step_num}/{total}] {title}", Colors.BOLD + Colors.BLUE))
    print(c("=" * 76, Colors.BLUE))
    print()

def print_success(msg):
    print(c(f"  [OK] {msg}", Colors.GREEN))

def print_error(msg):
    print(c(f"  [ERREUR] {msg}", Colors.RED))

def print_warning(msg):
    print(c(f"  [ATTENTION] {msg}", Colors.YELLOW))

def print_info(msg):
    print(c(f"  [INFO] {msg}", Colors.CYAN))

def print_doc(title, content):
    """Affiche une documentation formatee"""
    print()
    print(c(f"  +{'-' * 72}+", Colors.YELLOW))
    print(c(f"  | {title:<70} |", Colors.YELLOW + Colors.BOLD))
    print(c(f"  +{'-' * 72}+", Colors.YELLOW))
    for line in content.strip().split('\n'):
        if len(line) > 70:
            line = line[:67] + "..."
        print(c(f"  | {line:<70} |", Colors.YELLOW))
    print(c(f"  +{'-' * 72}+", Colors.YELLOW))
    print()

# ============================================================================
# VERIFICATIONS SYSTEME
# ============================================================================

def check_python_version():
    """Verifie la version de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ requis (version actuelle: {version.major}.{version.minor})")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro} detecte")
    return True

def check_ffmpeg():
    """Verifie si FFmpeg est installe"""
    script_dir = Path(__file__).parent
    local_ffmpeg = script_dir / "ffmpeg" / ("ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
    
    if local_ffmpeg.exists():
        print_success(f"FFmpeg trouve localement: {local_ffmpeg}")
        return True
    
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print_success(f"FFmpeg trouve dans le PATH: {ffmpeg_path}")
        return True
    
    return False

def check_docker():
    """Verifie si Docker est installe et en cours d'execution"""
    docker_path = shutil.which("docker")
    if not docker_path:
        return False, "not_installed"
    
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print_success("Docker est installe et en cours d'execution")
            return True, "running"
        else:
            return True, "not_running"
    except subprocess.TimeoutExpired:
        return True, "not_running"
    except Exception:
        return False, "error"

def check_docker_compose():
    """Verifie si Docker Compose est disponible"""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print_success("Docker Compose (v2) disponible")
            return True
    except:
        pass
    
    compose_path = shutil.which("docker-compose")
    if compose_path:
        print_success("Docker Compose (v1) disponible")
        return True
    
    return False

# ============================================================================
# INSTALLATION
# ============================================================================

def install_ffmpeg():
    """Telecharge et installe FFmpeg"""
    script_dir = Path(__file__).parent
    ffmpeg_dir = script_dir / "ffmpeg"
    ffmpeg_dir.mkdir(exist_ok=True)
    
    system = platform.system()
    
    if system == "Windows":
        print_info("Telechargement de FFmpeg pour Windows...")
        url = FFMPEG_WINDOWS_URL
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                tmp_path = tmp.name
            
            print_info("Telechargement en cours (environ 80 MB)...")
            urllib.request.urlretrieve(url, tmp_path, _download_progress)
            print()
            
            print_info("Extraction des fichiers...")
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(('ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe')):
                        filename = os.path.basename(file)
                        target_path = ffmpeg_dir / filename
                        with zip_ref.open(file) as source, open(target_path, 'wb') as target:
                            target.write(source.read())
                        print_success(f"Extrait: {filename}")
            
            os.unlink(tmp_path)
            print_success("FFmpeg installe avec succes!")
            return True
            
        except Exception as e:
            print_error(f"Erreur lors de l'installation: {e}")
            return False
    
    elif system == "Darwin":
        print_info("Installation de FFmpeg via Homebrew...")
        try:
            subprocess.run(["brew", "install", "ffmpeg"], check=True)
            print_success("FFmpeg installe avec succes!")
            return True
        except subprocess.CalledProcessError:
            print_error("Echec de l'installation via Homebrew")
            print_info("Installez Homebrew: https://brew.sh")
            return False
        except FileNotFoundError:
            print_error("Homebrew non trouve")
            print_info("Installez Homebrew: https://brew.sh")
            return False
    
    elif system == "Linux":
        print_info("Installation de FFmpeg via apt...")
        try:
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)
            print_success("FFmpeg installe avec succes!")
            return True
        except subprocess.CalledProcessError:
            print_error("Echec de l'installation via apt")
            return False
        except FileNotFoundError:
            print_error("apt non trouve - essayez d'installer FFmpeg manuellement")
            return False
    
    return False

def _download_progress(count, block_size, total_size):
    """Affiche la progression du telechargement"""
    percent = int(count * block_size * 100 / total_size)
    percent = min(percent, 100)
    bar_length = 40
    filled = int(bar_length * percent / 100)
    bar = '#' * filled + '-' * (bar_length - filled)
    sys.stdout.write(f"\r  [{bar}] {percent}%")
    sys.stdout.flush()

def show_docker_install_instructions():
    """Affiche les instructions d'installation de Docker"""
    system = platform.system()
    
    if system == "Windows":
        doc = """
Pour installer Docker sur Windows:

1. Telechargez Docker Desktop:
   https://www.docker.com/products/docker-desktop/

2. Executez l'installateur et suivez les instructions

3. Redemarrez votre ordinateur si demande

4. Lancez Docker Desktop depuis le menu Demarrer

5. Attendez que Docker soit "Running" (icone verte)

6. Relancez ce script de setup
"""
    elif system == "Darwin":
        doc = """
Pour installer Docker sur macOS:

1. Telechargez Docker Desktop:
   https://www.docker.com/products/docker-desktop/

2. Ouvrez le fichier .dmg et glissez Docker dans Applications

3. Lancez Docker depuis Applications

4. Autorisez les permissions demandees

5. Attendez que Docker soit pret

6. Relancez ce script de setup
"""
    else:
        doc = """
Pour installer Docker sur Linux (Ubuntu/Debian):

curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

Puis deconnectez-vous et reconnectez-vous, ou executez:
newgrp docker

Verifiez l'installation:
docker run hello-world
"""
    
    print_doc("Installation de Docker", doc)

# ============================================================================
# CONFIGURATION DES CLES API
# ============================================================================

API_KEYS_INFO = {
    "GROQ_API_KEY": {
        "name": "Groq",
        "required": True,
        "description": "Transcription audio ultra-rapide (Whisper)",
        "doc": """
GROQ - Cle API GRATUITE

Groq permet la transcription audio avec Whisper.
C'est GRATUIT et tres rapide!

1. Allez sur: https://console.groq.com/keys

2. Creez un compte (gratuit) ou connectez-vous

3. Cliquez sur "Create API Key"

4. Copiez la cle qui commence par "gsk_..."
""",
        "placeholder": "gsk_...",
        "url": "https://console.groq.com/keys"
    },
    "OPENROUTER_API_KEY": {
        "name": "OpenRouter",
        "required": False,
        "description": "IA pour SEO, shorts, miniatures (GPT-4, Claude, Gemini)",
        "doc": """
OPENROUTER - $5 offerts a l'inscription!

OpenRouter donne acces a GPT-4, Claude, Gemini, etc.
Utilise pour: generation SEO, suggestions shorts, miniatures.

1. Allez sur: https://openrouter.ai/keys

2. Creez un compte (vous recevez $5 de credit gratuit!)

3. Cliquez sur "Create Key"

4. Copiez la cle qui commence par "sk-or-..."

Avec $5, vous pouvez traiter des centaines de videos!
""",
        "placeholder": "sk-or-...",
        "url": "https://openrouter.ai/keys"
    },
    "PEXELS_API_KEY": {
        "name": "Pexels",
        "required": False,
        "description": "Clips video B-roll gratuits",
        "doc": """
PEXELS - Cle API 100% GRATUITE

Pexels fournit des clips video de haute qualite gratuits
pour illustrer vos videos (B-roll).

1. Allez sur: https://www.pexels.com/api/new/

2. Creez un compte Pexels (gratuit)

3. Remplissez le formulaire de demande d'API

4. Copiez votre cle API

Utilisation illimitee et gratuite!
""",
        "placeholder": "Votre cle Pexels",
        "url": "https://www.pexels.com/api/new/"
    }
}

def configure_api_keys():
    """Configure les cles API de maniere interactive"""
    script_dir = Path(__file__).parent
    env_file = script_dir / "web-app" / ".env"
    
    existing_keys = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_keys[key.strip()] = value.strip()
    
    new_keys = {}
    
    for key_name, info in API_KEYS_INFO.items():
        print()
        print(c(f"  {'-' * 74}", Colors.CYAN))
        required_tag = c(" [REQUIS]", Colors.RED) if info['required'] else c(" [Optionnel]", Colors.YELLOW)
        print(c(f"  ** {info['name']}{required_tag}", Colors.BOLD))
        print(c(f"     {info['description']}", Colors.CYAN))
        print()
        
        print_doc(f"Comment obtenir la cle {info['name']}", info['doc'])
        
        current = existing_keys.get(key_name, "")
        if current:
            masked = current[:8] + "..." + current[-4:] if len(current) > 12 else "****"
            print_info(f"Valeur actuelle: {masked}")
        
        prompt = f"  Entrez votre cle {info['name']} ({info['placeholder']})"
        if not info['required']:
            prompt += " ou Entree pour passer"
        prompt += ": "
        
        try:
            value = input(c(prompt, Colors.BOLD)).strip()
        except KeyboardInterrupt:
            print("\n")
            print_warning("Configuration annulee")
            return False
        
        if value:
            new_keys[key_name] = value
            print_success(f"Cle {info['name']} configuree!")
        elif current:
            new_keys[key_name] = current
            print_info(f"Cle {info['name']} conservee")
        elif info['required']:
            print_error(f"Cle {info['name']} requise!")
            return False
        else:
            new_keys[key_name] = ""
            print_info(f"Cle {info['name']} non configuree (optionnelle)")
    
    print()
    print_info("Creation du fichier .env...")
    
    env_content = f"""# ============================================
# YouTube Pipeline - Variables d'environnement
# Genere automatiquement par setup.py
# ============================================

# ============ CLES API ============
GROQ_API_KEY={new_keys.get('GROQ_API_KEY', '')}
OPENROUTER_API_KEY={new_keys.get('OPENROUTER_API_KEY', '')}
PEXELS_API_KEY={new_keys.get('PEXELS_API_KEY', '')}

# ============ GOOGLE/YOUTUBE (Optionnel) ============
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ============ MINIO (Stockage) ============
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# ============ MONGO EXPRESS (Debug) ============
MONGO_EXPRESS_USER=admin
MONGO_EXPRESS_PASS=admin
"""
    
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print_success(f"Fichier .env cree: {env_file}")
    return True

# ============================================================================
# LANCEMENT DE L'APPLICATION
# ============================================================================

def start_application():
    """Propose de lancer l'application"""
    print()
    print(c("  +------------------------------------------------------------------------+", Colors.GREEN))
    print(c("  |                    Configuration terminee!                             |", Colors.GREEN + Colors.BOLD))
    print(c("  +------------------------------------------------------------------------+", Colors.GREEN))
    print()
    
    try:
        response = input(c("  Voulez-vous lancer l'application maintenant? (o/N): ", Colors.BOLD)).strip().lower()
    except KeyboardInterrupt:
        print("\n")
        return
    
    if response in ['o', 'oui', 'y', 'yes']:
        print()
        print_info("Lancement de Docker Compose...")
        print_info("Cela peut prendre quelques minutes lors du premier lancement...")
        print()
        
        webapp_dir = Path(__file__).parent / "web-app"
        os.chdir(webapp_dir)
        
        try:
            try:
                subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)
            except:
                subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
            
            print()
            print_success("Application lancee avec succes!")
            print()
            print(c("  +------------------------------------------------------------------------+", Colors.CYAN))
            print(c("  |                        Acces a l'application                          |", Colors.CYAN + Colors.BOLD))
            print(c("  +------------------------------------------------------------------------+", Colors.CYAN))
            print(c("  |                                                                        |", Colors.CYAN))
            print(c("  |   Frontend:        http://localhost:3010                               |", Colors.CYAN))
            print(c("  |   API Backend:     http://localhost:8010                               |", Colors.CYAN))
            print(c("  |   Flower:          http://localhost:5555                               |", Colors.CYAN))
            print(c("  |   Mongo Express:   http://localhost:8081                               |", Colors.CYAN))
            print(c("  |   MinIO Console:   http://localhost:9001                               |", Colors.CYAN))
            print(c("  |                                                                        |", Colors.CYAN))
            print(c("  +------------------------------------------------------------------------+", Colors.CYAN))
            print()
            
        except subprocess.CalledProcessError as e:
            print_error(f"Erreur lors du lancement: {e}")
            print_info("Essayez manuellement: cd web-app && docker compose up -d --build")
    else:
        print()
        print_info("Pour lancer l'application plus tard:")
        print(c("     cd web-app", Colors.BOLD))
        print(c("     docker compose up -d --build", Colors.BOLD))
        print()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Point d'entree principal"""
    print_banner()
    
    total_steps = 4
    
    # ETAPE 1: Verification Python
    print_step(1, total_steps, "Verification de Python")
    
    if not check_python_version():
        print_error("Veuillez mettre a jour Python et relancer ce script.")
        sys.exit(1)
    
    # ETAPE 2: FFmpeg
    print_step(2, total_steps, "Verification de FFmpeg")
    
    if not check_ffmpeg():
        print_warning("FFmpeg non trouve")
        print()
        
        try:
            response = input(c("  Voulez-vous installer FFmpeg automatiquement? (O/n): ", Colors.BOLD)).strip().lower()
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)
        
        if response not in ['n', 'non', 'no']:
            if not install_ffmpeg():
                print_error("Echec de l'installation de FFmpeg")
                print_info("Installez FFmpeg manuellement: https://ffmpeg.org/download.html")
        else:
            print_warning("FFmpeg non installe - certaines fonctionnalites ne marcheront pas")
    
    # ETAPE 3: Docker
    print_step(3, total_steps, "Verification de Docker")
    
    docker_ok, docker_status = check_docker()
    
    if not docker_ok:
        print_error("Docker n'est pas installe")
        show_docker_install_instructions()
        
        print_warning("Installez Docker et relancez ce script.")
        print()
        
        try:
            input(c("  Appuyez sur Entree pour quitter...", Colors.BOLD))
        except KeyboardInterrupt:
            pass
        sys.exit(1)
    
    if docker_status == "not_running":
        print_warning("Docker est installe mais n'est pas en cours d'execution")
        print_info("Lancez Docker Desktop et attendez qu'il soit pret")
        print()
        
        try:
            input(c("  Appuyez sur Entree quand Docker est pret...", Colors.BOLD))
        except KeyboardInterrupt:
            print("\n")
            sys.exit(0)
        
        docker_ok, docker_status = check_docker()
        if docker_status != "running":
            print_error("Docker n'est toujours pas pret")
            sys.exit(1)
    
    if not check_docker_compose():
        print_error("Docker Compose non disponible")
        print_info("Mettez a jour Docker Desktop pour avoir Docker Compose v2")
        sys.exit(1)
    
    # ETAPE 4: Configuration des cles API
    print_step(4, total_steps, "Configuration des cles API")
    
    print_info("Les cles API sont necessaires pour les fonctionnalites suivantes:")
    print(c("     - Groq: Transcription audio (REQUIS)", Colors.CYAN))
    print(c("     - OpenRouter: SEO, shorts, miniatures (Recommande)", Colors.CYAN))
    print(c("     - Pexels: Clips B-roll (Optionnel)", Colors.CYAN))
    print()
    
    if not configure_api_keys():
        print_error("Configuration des cles API incomplete")
        sys.exit(1)
    
    # FIN: Lancement
    start_application()
    
    print()
    print(c("  Merci d'utiliser YouTube Pipeline!", Colors.CYAN + Colors.BOLD))
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print(c("  Setup annule.", Colors.YELLOW))
        sys.exit(0)
    except Exception as e:
        print()
        print(c(f"  [ERREUR] Erreur inattendue: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        sys.exit(1)
