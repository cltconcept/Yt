"""
Etape 6 : Ajout de B-roll (clips Pexels)
- Analyse la transcription pour trouver les moments a illustrer
- Telecharge des clips Pexels correspondants
- Insere les clips dans la video
"""
import subprocess
import json
import os
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def get_duration(file_path: str) -> float:
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def analyze_for_broll(video_folder: str, max_clips: int = 3) -> list:
    """
    Analyse la transcription pour trouver les moments a illustrer avec B-roll
    
    Returns:
        Liste de moments: [{keyword, timestamp, duration, description}]
    """
    video_folder = Path(video_folder)
    transcription_path = video_folder / "transcription.json"
    
    if not transcription_path.exists():
        print("[Step6] Transcription manquante")
        return []
    
    with open(transcription_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    text = data.get('text', '')
    segments = data.get('segments', [])
    
    if not OPENROUTER_API_KEY:
        print("[Step6] OPENROUTER_API_KEY manquante")
        return []
    
    # Construire le contexte
    segments_text = ""
    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        seg_text = seg.get('text', '')
        segments_text += f"[{start:.1f}s - {end:.1f}s]: {seg_text}\n"
    
    prompt = f"""Analyse cette transcription et suggère SEULEMENT les moments où un B-roll serait VRAIMENT utile.

Transcription avec timestamps:
{segments_text}

RÈGLES STRICTES - NE PAS mettre de B-roll si:
- C'est un tutoriel où on montre l'écran (le contenu à l'écran EST le visuel)
- On fait une démonstration pratique
- On code ou on montre une interface
- La vidéo est courte (< 2 minutes) → maximum 1 B-roll
- On est en train d'expliquer quelque chose visuellement à l'écran

QUAND utiliser un B-roll:
- Moment "talking head" où on parle sans rien montrer à l'écran
- Transition entre deux sujets
- Concept abstrait qui mérite une illustration (ex: "le cloud", "la sécurité")
- Introduction ou conclusion

QUANTITÉ:
- Vidéo < 2 min: 0-1 B-roll maximum
- Vidéo 2-5 min: 1-2 B-roll maximum  
- Vidéo > 5 min: {max_clips} B-roll maximum
- Si aucun moment n'est pertinent, retourne une liste vide []

Pour chaque moment (si pertinent):
1. keyword: mot-clé en ANGLAIS pour Pexels
2. timestamp: moment d'insertion (en secondes)
3. duration: durée du clip (2-4 secondes MAX)
4. description: justification de pourquoi ce B-roll est utile

Réponds en JSON valide (peut être vide []):
[
  {{"keyword": "cloud computing", "timestamp": 15.0, "duration": 3, "description": "Illustre le concept abstrait de cloud"}}
]"""

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                moments = json.loads(json_match.group())
                print(f"[Step6] {len(moments)} moments B-roll suggeres")
                return moments
        
        print(f"[Step6] Erreur API: {response.status_code}")
        return []
        
    except Exception as e:
        print(f"[Step6] Erreur analyse: {e}")
        return []


def download_pexels_clip(keyword: str, output_path: Path) -> bool:
    """Telecharge un clip video depuis Pexels"""
    if not PEXELS_API_KEY:
        print(f"[Step6] PEXELS_API_KEY manquante")
        return False
    
    try:
        # Rechercher le clip
        response = httpx.get(
            f"https://api.pexels.com/videos/search?query={keyword}&per_page=3&size=small",
            headers={"Authorization": PEXELS_API_KEY},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[Step6] Erreur Pexels: {response.status_code}")
            return False
        
        data = response.json()
        videos = data.get("videos", [])
        
        if not videos:
            print(f"[Step6] Aucun clip trouve pour '{keyword}'")
            return False
        
        # Prendre le premier resultat
        video_files = videos[0].get("video_files", [])
        if not video_files:
            return False
        
        # Trier par qualite (prendre SD/HD, pas 4K)
        video_files.sort(key=lambda x: x.get("width", 9999))
        # Prendre une qualite moyenne (pas la plus petite, pas la plus grande)
        video_url = video_files[min(1, len(video_files)-1)].get("link")
        
        if not video_url:
            return False
        
        # Telecharger
        print(f"[Step6] Telechargement clip '{keyword}'...")
        video_response = httpx.get(video_url, timeout=60, follow_redirects=True)
        
        if video_response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(video_response.content)
            size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"[Step6] Clip telecharge: {output_path.name} ({size_mb:.1f} MB)")
            return True
        
        return False
        
    except Exception as e:
        print(f"[Step6] Erreur telechargement: {e}")
        return False


def insert_broll_clips(video_folder: str, clips: list) -> dict:
    """
    Insere les clips B-roll dans la video
    
    Args:
        video_folder: Dossier video
        clips: Liste de clips [{path, timestamp, duration}]
    
    Returns:
        dict avec success, output_path, error
    """
    video_folder = Path(video_folder)
    input_path = video_folder / "nosilence.mp4"
    output_path = video_folder / "illustrated.mp4"
    
    result = {'success': False, 'error': None, 'output_path': None}
    
    if not input_path.exists():
        result['error'] = 'nosilence.mp4 manquant'
        return result
    
    if not clips:
        result['error'] = 'Pas de clips a inserer'
        return result
    
    video_duration = get_duration(str(input_path))
    
    # Construire le filtre complexe pour inserer les clips
    # On va superposer les clips sur la video principale
    filter_parts = []
    inputs = ['-i', str(input_path)]
    
    for i, clip in enumerate(clips):
        clip_path = clip.get('path')
        timestamp = clip.get('timestamp', 0)
        duration = clip.get('duration', 3)
        
        if not Path(clip_path).exists():
            continue
        
        inputs.extend(['-i', clip_path])
        
        # Filtre pour ce clip: redimensionner et positionner
        # Le clip apparait en overlay pendant sa duree
        filter_parts.append(
            f"[{i+1}:v]scale=480:-1,setpts=PTS-STARTPTS[clip{i}];"
            f"[tmp{i}][clip{i}]overlay=10:10:enable='between(t,{timestamp},{timestamp+duration})'[tmp{i+1}]"
        )
    
    if not filter_parts:
        result['error'] = 'Aucun clip valide'
        return result
    
    # Construire le filtre complet
    filter_complex = f"[0:v]copy[tmp0];" + ";".join(filter_parts)
    final_output = f"[tmp{len(clips)}]"
    
    cmd = [
        FFMPEG, '-y',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', final_output,
        '-map', '0:a',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'copy',
        str(output_path)
    ]
    
    print(f"[Step6] Insertion des clips...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    if proc.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        result['success'] = True
        result['output_path'] = str(output_path)
        print(f"[Step6] OK: illustrated.mp4 ({size_mb:.1f} MB)")
    else:
        result['error'] = proc.stderr[-300:] if proc.stderr else 'Erreur FFmpeg'
        print(f"[Step6] ERREUR: {result['error']}")
    
    return result


def add_broll(video_folder: str, max_clips: int = 3) -> dict:
    """
    Pipeline complet B-roll:
    1. Analyse transcription pour trouver moments
    2. Telecharge clips Pexels
    3. Insere dans la video
    
    Returns:
        dict avec success, clips, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'clips': [],
        'output_path': None
    }
    
    # 1. Analyser pour trouver les moments
    print(f"[Step6] Analyse de la transcription...")
    moments = analyze_for_broll(str(video_folder), max_clips)
    
    if not moments:
        # Pas d'erreur - c'est OK de ne pas avoir de B-roll (tutoriel, vidéo courte, etc.)
        result['success'] = True
        result['clips'] = []
        print("[Step6] Aucun B-roll suggéré (contenu ne nécessite pas d'illustration) - OK")
        return result
    
    # Sauvegarder les suggestions
    suggestions_path = video_folder / "broll_suggestions.json"
    with open(suggestions_path, 'w', encoding='utf-8') as f:
        json.dump(moments, f, ensure_ascii=False, indent=2)
    print(f"[Step6] Suggestions sauvegardees: {suggestions_path.name}")
    
    # 2. Telecharger les clips
    broll_dir = video_folder / "broll"
    broll_dir.mkdir(exist_ok=True)
    
    downloaded_clips = []
    for i, moment in enumerate(moments):
        keyword = moment.get('keyword', '')
        if not keyword:
            continue
        
        clip_path = broll_dir / f"clip_{i}_{keyword.replace(' ', '_')}.mp4"
        
        if download_pexels_clip(keyword, clip_path):
            downloaded_clips.append({
                'path': str(clip_path),
                'keyword': keyword,
                'timestamp': moment.get('timestamp', 0),
                'duration': moment.get('duration', 3),
                'description': moment.get('description', '')
            })
    
    if not downloaded_clips:
        result['error'] = 'Aucun clip telecharge'
        return result
    
    # Sauvegarder les infos des clips
    clips_path = video_folder / "broll_clips.json"
    with open(clips_path, 'w', encoding='utf-8') as f:
        json.dump(downloaded_clips, f, ensure_ascii=False, indent=2)
    
    result['clips'] = downloaded_clips
    print(f"[Step6] {len(downloaded_clips)} clips prets")
    
    # 3. Inserer les clips (optionnel - peut etre fait manuellement)
    # insert_result = insert_broll_clips(str(video_folder), downloaded_clips)
    # if insert_result['success']:
    #     result['output_path'] = insert_result['output_path']
    
    result['success'] = True
    print(f"[Step6] B-roll termine!")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = add_broll(folder)
    print(f"\nResultat: {result}")


