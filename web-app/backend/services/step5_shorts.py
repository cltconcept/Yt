"""
Etape 5 : Creation des shorts YouTube/TikTok
- Analyse la transcription pour trouver les meilleurs moments
- Cree des shorts en format 9:16 (ecran en haut, webcam en bas)
- Ajoute les sous-titres karaoke
"""
import subprocess
import json
import os
import httpx
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Chemin vers la vidéo outro (à placer dans backend/assets/)
ASSETS_DIR = Path(__file__).parent.parent / "assets"
OUTRO_VIDEO_PATH = ASSETS_DIR / "outro.mp4"

# Durée outro et limite shorts (30s max avec outro incluse)
OUTRO_DURATION = 4  # secondes
MAX_SHORT_TOTAL = 30  # durée max totale du short (outro incluse)
MAX_SHORT_CONTENT = MAX_SHORT_TOTAL - OUTRO_DURATION  # 26 secondes de contenu max

# Dimensions short
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
HALF_HEIGHT = SHORT_HEIGHT // 2


def snap_to_segment_boundaries(start: float, end: float, segments: list) -> tuple:
    """
    Ajuste les timestamps start/end aux limites des segments les plus proches.
    Garantit que le short ne coupe pas au milieu d'une phrase.
    
    Returns:
        (adjusted_start, adjusted_end)
    """
    if not segments:
        return start, end
    
    # Trouver le segment dont le début est le plus proche de start
    best_start = start
    min_start_diff = float('inf')
    for seg in segments:
        seg_start = seg.get('start', 0)
        diff = abs(seg_start - start)
        if diff < min_start_diff:
            min_start_diff = diff
            best_start = seg_start
    
    # Trouver le segment dont la fin est la plus proche de end
    best_end = end
    min_end_diff = float('inf')
    for seg in segments:
        seg_end = seg.get('end', 0)
        diff = abs(seg_end - end)
        if diff < min_end_diff:
            min_end_diff = diff
            best_end = seg_end
    
    # S'assurer que end > start
    if best_end <= best_start:
        best_end = best_start + 15  # Minimum 15 secondes
    
    return best_start, best_end


def suggest_shorts(video_folder: str, max_shorts: int = 3) -> list:
    """
    Analyse la transcription et suggere des moments pour des shorts
    
    Returns:
        Liste de suggestions: [{title, start, end, description}]
    """
    video_folder = Path(video_folder)
    transcription_path = video_folder / "transcription.json"
    
    if not transcription_path.exists():
        print("[Step5] Transcription manquante")
        return []
    
    with open(transcription_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    text = data.get('text', '')
    segments = data.get('segments', [])
    duration = data.get('duration', 0)
    
    if not segments:
        print("[Step5] Pas de segments dans la transcription")
        return []
    
    if not OPENROUTER_API_KEY:
        print("[Step5] OPENROUTER_API_KEY manquante")
        return []
    
    # Construire le contexte avec timestamps
    segments_text = ""
    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        seg_text = seg.get('text', '')
        segments_text += f"[{start:.1f}s - {end:.1f}s]: {seg_text}\n"
    
    prompt = f"""Analyse cette transcription video et suggere {max_shorts} moments interessants pour des shorts (15-{MAX_SHORT_CONTENT} secondes MAX).

Transcription avec timestamps:
{segments_text}

Duree totale: {duration:.1f}s

Pour chaque short suggere:
1. Un titre accrocheur (max 50 caracteres)
2. Le timestamp de debut (en secondes) - DOIT correspondre au DEBUT d'une phrase
3. Le timestamp de fin (en secondes) - DOIT correspondre a la FIN d'une phrase
4. Une breve description du contenu

Reponds en JSON valide avec ce format exact:
[
  {{"title": "...", "start": 0.0, "end": 26.0, "description": "..."}}
]

REGLES CRITIQUES:
- NE JAMAIS couper au milieu d'une phrase! Le short doit commencer et finir sur des phrases completes
- Utilise EXACTEMENT les timestamps des segments fournis pour start et end
- Chaque short doit durer entre 15 et {MAX_SHORT_CONTENT} secondes MAXIMUM (une outro de {OUTRO_DURATION}s sera ajoutée)
- Les timestamps doivent correspondre aux limites des segments [X.Xs - Y.Ys] fournis
- Choisis les moments les plus engageants/interessants avec un debut et une fin naturels"""

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
            # Extraire le JSON de la reponse
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                suggestions = json.loads(json_match.group())
                print(f"[Step5] {len(suggestions)} suggestions generees")
                return suggestions
        
        print(f"[Step5] Erreur API: {response.status_code}")
        return []
        
    except Exception as e:
        print(f"[Step5] Erreur suggestion: {e}")
        return []


def merge_outro(video_path: str, output_path: str) -> bool:
    """
    Merge la vidéo outro à la fin d'un short
    
    Args:
        video_path: Chemin du short créé
        output_path: Chemin de sortie avec outro
        
    Returns:
        True si succès, False sinon
    """
    if not OUTRO_VIDEO_PATH.exists():
        print(f"[Step5] Pas de vidéo outro trouvée dans {OUTRO_VIDEO_PATH}")
        return False
    
    try:
        # Créer fichier liste pour concat
        video_folder = Path(video_path).parent
        concat_list = video_folder / "concat_outro.txt"
        
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write(f"file '{Path(video_path).absolute()}'\n")
            f.write(f"file '{OUTRO_VIDEO_PATH.absolute()}'\n")
        
        # La vidéo outro doit être au même format (1080x1920, même codec)
        # On la reéencode pour s'assurer de la compatibilité
        outro_temp = video_folder / "outro_temp.mp4"
        
        # Reencoder l'outro au bon format
        cmd_outro = [
            FFMPEG, '-y',
            '-i', str(OUTRO_VIDEO_PATH),
            '-vf', f'scale={SHORT_WIDTH}:{SHORT_HEIGHT}:force_original_aspect_ratio=decrease,pad={SHORT_WIDTH}:{SHORT_HEIGHT}:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
            '-r', '30',
            str(outro_temp)
        ]
        
        proc_outro = subprocess.run(cmd_outro, capture_output=True, text=True)
        if proc_outro.returncode != 0:
            print(f"[Step5] Erreur reencodage outro: {proc_outro.stderr[-200:]}")
            return False
        
        # Mettre à jour la liste avec l'outro reencodée
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write(f"file '{Path(video_path).absolute()}'\n")
            f.write(f"file '{outro_temp.absolute()}'\n")
        
        # Concat les vidéos
        cmd_concat = [
            FFMPEG, '-y',
            '-f', 'concat', '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',
            str(output_path)
        ]
        
        proc_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
        
        # Nettoyer fichiers temporaires
        concat_list.unlink(missing_ok=True)
        outro_temp.unlink(missing_ok=True)
        
        if proc_concat.returncode == 0 and Path(output_path).exists():
            print(f"[Step5] Outro ajoutée avec succès")
            return True
        else:
            print(f"[Step5] Erreur concat: {proc_concat.stderr[-200:]}")
            return False
            
    except Exception as e:
        print(f"[Step5] Erreur merge outro: {e}")
        return False


def generate_karaoke_ass(segments: list, start: float, end: float, output_path: str):
    """Genere un fichier ASS - mot actuel en JAUNE et GRAND, autres en blanc petit"""
    # Style Normal = blanc, petit
    # Style Highlight = jaune, grand
    ass_content = """[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Normal,Impact,110,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,5,40,40,0,1
Style: Highlight,Impact,110,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    
    # Collecter tous les mots avec leurs timestamps
    all_words = []
    for seg in segments:
        seg_start = seg.get('start', 0)
        seg_end = seg.get('end', 0)
        text = seg.get('text', '').strip().upper()
        
        if not text:
            continue
        
        if seg_end < start or seg_start > end:
            continue
        
        words = text.split()
        if words:
            word_duration = (seg_end - seg_start) / len(words)
            for i, word in enumerate(words):
                word_start = seg_start + i * word_duration
                word_end = word_start + word_duration
                rel_start_w = max(0, word_start - start)
                rel_end_w = min(end - start, word_end - start)
                if rel_end_w > rel_start_w:
                    all_words.append({
                        'word': word,
                        'start': rel_start_w,
                        'end': rel_end_w
                    })
    
    # Grouper les mots: 2 mots par ligne, 2 lignes max = 4 mots par groupe
    WORDS_PER_LINE = 2
    LINES_PER_GROUP = 2
    WORDS_PER_GROUP = WORDS_PER_LINE * LINES_PER_GROUP
    
    groups = []
    for i in range(0, len(all_words), WORDS_PER_GROUP):
        groups.append(all_words[i:i + WORDS_PER_GROUP])
    
    # Pour chaque mot, generer le groupe avec ce mot en highlight
    for group in groups:
        for word_idx, current_word in enumerate(group):
            # Construire les 2 lignes avec le mot actuel en grand/jaune
            text_parts = []
            for i, w in enumerate(group):
                if i == word_idx:
                    text_parts.append(f"{{\\rHighlight}}{w['word']}{{\\rNormal}}")
                else:
                    text_parts.append(w['word'])
            
            # Separer en 2 lignes avec \N
            line1_words = text_parts[:WORDS_PER_LINE]
            line2_words = text_parts[WORDS_PER_LINE:]
            
            if line2_words:
                line_text = " ".join(line1_words) + "\\N" + " ".join(line2_words)
            else:
                line_text = " ".join(line1_words)
            
            ass_content += f"Dialogue: 0,{format_time(current_word['start'])},{format_time(current_word['end'])},Normal,,0,0,0,,{line_text}\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)


def create_short(video_folder: str, title: str, start: float, end: float) -> dict:
    """
    Cree un short en format 9:16
    - Ecran en haut avec pan fluide
    - Webcam en bas avec zoom
    - Sous-titres karaoke
    
    Returns:
        dict avec success, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'output_path': None,
        'duration': end - start
    }
    
    # Fichiers sources (priorite aux versions sans silence)
    screen_path = video_folder / "screennosilence.mp4"
    webcam_path = video_folder / "webcamnosilence.mp4"
    
    if not screen_path.exists():
        screen_path = video_folder / "screen.mp4"
    if not webcam_path.exists():
        webcam_path = video_folder / "webcam.mp4"
    
    if not screen_path.exists():
        result['error'] = 'screen non trouve'
        return result
    if not webcam_path.exists():
        result['error'] = 'webcam non trouve'
        return result
    
    # Charger transcription
    transcription_path = video_folder / "transcription.json"
    segments = []
    if transcription_path.exists():
        with open(transcription_path, 'r', encoding='utf-8') as f:
            segments = json.load(f).get('segments', [])
    
    # Valider duree
    duration = end - start
    if duration < 3 or duration > MAX_SHORT_CONTENT:
        result['error'] = f'Duree invalide: {duration}s (3-{MAX_SHORT_CONTENT}s requis, outro de {OUTRO_DURATION}s sera ajoutée)'
        return result
    
    print(f"[Step5] Creation short: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")
    
    # Creer dossier shorts
    shorts_dir = video_folder / "shorts"
    shorts_dir.mkdir(exist_ok=True)
    
    # Nom fichier
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:30]
    timestamp = datetime.now().strftime("%H%M%S")
    output_path = shorts_dir / f"short_{safe_title}_{timestamp}.mp4"
    
    # Generer sous-titres
    ass_path = None
    if segments:
        ass_path = shorts_dir / f"temp_{timestamp}.ass"
        generate_karaoke_ass(segments, start, end, str(ass_path))
        print(f"[Step5] Sous-titres generes")
    
    # Parametres zoom sur le screen
    ZOOM = 3.0  # Zoom x3 pour focus sur le contenu
    ZOOM_WIDTH = int(SHORT_WIDTH * ZOOM)
    ZOOM_HEIGHT = int(HALF_HEIGHT * ZOOM)
    WEBCAM_ZOOM = 1.3  # Reduit de 1.5 a 1.3
    WEBCAM_W = int(SHORT_WIDTH * WEBCAM_ZOOM)
    WEBCAM_H = int(HALF_HEIGHT * WEBCAM_ZOOM)
    
    # Construire filtre
    if ass_path and ass_path.exists():
        ass_escaped = str(ass_path.absolute()).replace("\\", "/").replace(":", "\\:")
        filter_complex = (
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,fps=30,"
            f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}:'(iw-ow)/2+(iw-ow)/4*sin(n*0.005)':'(ih-oh)/2+(ih-oh)/4*cos(n*0.004)'[screen];"
            f"[1:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
            f"scale={WEBCAM_W}:{WEBCAM_H}:force_original_aspect_ratio=increase,"
            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
            f"[screen][webcam]vstack=inputs=2[stacked];"
            f"[stacked]subtitles='{ass_escaped}'[out];"
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[audio]"
        )
    else:
        filter_complex = (
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,fps=30,"
            f"scale={ZOOM_WIDTH}:{ZOOM_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}:'(iw-ow)/2+(iw-ow)/4*sin(n*0.005)':'(ih-oh)/2+(ih-oh)/4*cos(n*0.004)'[screen];"
            f"[1:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
            f"scale={WEBCAM_W}:{WEBCAM_H}:force_original_aspect_ratio=increase,"
            f"crop={SHORT_WIDTH}:{HALF_HEIGHT}[webcam];"
            f"[screen][webcam]vstack=inputs=2[out];"
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[audio]"
        )
    
    cmd = [
        FFMPEG, '-y',
        '-i', str(screen_path),
        '-i', str(webcam_path),
        '-filter_complex', filter_complex,
        '-map', '[out]', '-map', '[audio]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart',
        str(output_path)
    ]
    
    print(f"[Step5] Encodage...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Nettoyer ASS temp
    if ass_path and ass_path.exists():
        ass_path.unlink()
    
    if proc.returncode == 0 and output_path.exists():
        # Ajouter l'outro si elle existe
        if OUTRO_VIDEO_PATH.exists():
            print(f"[Step5] Ajout de l'outro...")
            output_with_outro = shorts_dir / f"short_{safe_title}_{timestamp}_final.mp4"
            
            if merge_outro(str(output_path), str(output_with_outro)):
                # Remplacer le fichier original par celui avec outro
                output_path.unlink()
                output_with_outro.rename(output_path)
                print(f"[Step5] Short avec outro créé")
            else:
                print(f"[Step5] Outro non ajoutée, short conservé sans outro")
        
        size = output_path.stat().st_size / 1024 / 1024
        result['success'] = True
        result['output_path'] = str(output_path)
        print(f"[Step5] OK: {output_path.name} ({size:.2f} MB)")
    else:
        result['error'] = proc.stderr[-300:] if proc.stderr else 'Erreur FFmpeg'
        print(f"[Step5] ERREUR: {result['error']}")
    
    return result


def generate_shorts(video_folder: str, max_shorts: int = 3) -> dict:
    """
    Genere automatiquement des shorts
    1. Suggere les meilleurs moments
    2. Cree les shorts
    
    Returns:
        dict avec success, shorts (liste), error
    """
    result = {
        'success': False,
        'error': None,
        'shorts': []
    }
    
    # Suggerer les moments
    print(f"[Step5] Analyse de la transcription...")
    suggestions = suggest_shorts(video_folder, max_shorts)
    
    if not suggestions:
        # Pas d'erreur - la vidéo est simplement trop courte pour des shorts
        result['success'] = True
        result['shorts'] = []
        print("[Step5] Aucune suggestion (vidéo trop courte) - OK, on continue")
        return result
    
    # Sauvegarder suggestions
    video_folder = Path(video_folder)
    suggestions_path = video_folder / "shorts_suggestions.json"
    with open(suggestions_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)
    print(f"[Step5] Suggestions sauvegardees: {suggestions_path.name}")
    
    # Charger les segments pour ajuster les timestamps
    transcription_path = video_folder / "transcription.json"
    segments = []
    if transcription_path.exists():
        with open(transcription_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            segments = data.get('segments', [])
    
    # Creer chaque short
    for i, sug in enumerate(suggestions):
        title = sug.get('title', f'Short {i+1}')
        # Ajouter #shorts si pas déjà présent
        if '#shorts' not in title.lower():
            title = f"{title} #shorts"
        start = sug.get('start', 0)
        end = sug.get('end', 30)
        
        # Ajuster les timestamps aux limites des segments pour ne pas couper au milieu d'une phrase
        if segments:
            adjusted_start, adjusted_end = snap_to_segment_boundaries(start, end, segments)
            if adjusted_start != start or adjusted_end != end:
                print(f"[Step5] Timestamps ajustés: {start:.1f}-{end:.1f}s → {adjusted_start:.1f}-{adjusted_end:.1f}s")
                start, end = adjusted_start, adjusted_end
        
        print(f"\n[Step5] Short {i+1}/{len(suggestions)}: {title}")
        short_result = create_short(video_folder, title, start, end)
        
        if short_result['success']:
            result['shorts'].append({
                'title': title,  # Titre avec #shorts déjà inclus
                'start': start,
                'end': end,
                'path': short_result['output_path'],
                'duration': short_result['duration']
            })
    
    if result['shorts']:
        result['success'] = True
        print(f"\n[Step5] {len(result['shorts'])} short(s) cree(s)!")
    else:
        # Pas d'erreur - les suggestions n'ont pas donné de shorts valides
        result['success'] = True
        print("[Step5] Aucun short créé (vidéo trop courte ou pas de contenu adapté) - OK, on continue")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = generate_shorts(folder)
    print(f"\nResultat: {result}")

