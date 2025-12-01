"""
Etape 7 : Integration des clips B-roll dans la video
- Lit les clips telecharges (broll_clips.json)
- Insere les clips en overlay ou en remplacement
- Cree illustrated.mp4
"""
import subprocess
import json
import os
from pathlib import Path

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')


def get_duration(file_path: str) -> float:
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def integrate_broll(video_folder: str, broll_duration: float = 3.0) -> dict:
    """
    Integre les clips B-roll dans la video
    Le clip B-roll remplace la video principale pendant sa duree (max 3s)
    L'audio original continue pendant le B-roll
    
    Args:
        video_folder: Dossier video
        broll_duration: Duree max de chaque B-roll (defaut 3s)
    
    Returns:
        dict avec success, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'output_path': None,
        'clips_used': 0
    }
    
    # Fichiers
    input_path = video_folder / "nosilence.mp4"
    clips_json = video_folder / "broll_clips.json"
    output_path = video_folder / "illustrated.mp4"
    temp_dir = video_folder / "temp_broll"
    
    if not input_path.exists():
        result['error'] = 'nosilence.mp4 manquant'
        return result
    
    # Si pas de B-roll (fichier absent ou vide), copier directement la vidéo
    clips = []
    if clips_json.exists():
        with open(clips_json, 'r', encoding='utf-8') as f:
            clips = json.load(f)
    
    if not clips:
        # Pas de B-roll à intégrer - copier nosilence.mp4 vers illustrated.mp4
        print("[Step7] Pas de B-roll à intégrer - copie directe")
        import shutil
        shutil.copy(input_path, output_path)
        result['success'] = True
        result['output_path'] = str(output_path)
        result['clips_used'] = 0
        print(f"[Step7] OK: {output_path.name} (sans B-roll)")
        return result
    
    # Creer dossier temp
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(exist_ok=True)
    
    # Filtrer et pre-traiter les clips
    video_duration = get_duration(str(input_path))
    prepared_clips = []
    
    print(f"[Step7] Video source: {video_duration:.1f}s")
    print(f"[Step7] Preparation des clips B-roll (max {broll_duration}s chacun)...")
    
    for i, clip in enumerate(clips):
        clip_path = Path(clip.get('path', ''))
        if not clip_path.exists():
            print(f"[Step7] Clip {i+1} introuvable: {clip_path}")
            continue
        
        timestamp = clip.get('timestamp', 0)
        duration = min(broll_duration, clip.get('duration', broll_duration))
        
        # S'assurer que le clip est dans les limites
        if timestamp < 0 or timestamp >= video_duration:
            print(f"[Step7] Clip {i+1} hors limites: timestamp={timestamp}")
            continue
        
        # Ajuster si depasse la fin
        if timestamp + duration > video_duration:
            duration = video_duration - timestamp
        
        # Preparer le clip: couper a 3s, redimensionner 1920x1080, 30fps
        prepared_path = temp_dir / f"prepared_{i}.mp4"
        
        cmd_prepare = [
            FFMPEG, '-y',
            '-i', str(clip_path),
            '-t', str(duration),  # Couper a la duree max
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30',
            '-an',  # Pas d'audio du B-roll
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            str(prepared_path)
        ]
        
        proc = subprocess.run(cmd_prepare, capture_output=True, text=True)
        
        if prepared_path.exists():
            actual_duration = get_duration(str(prepared_path))
            prepared_clips.append({
                'path': str(prepared_path),
                'timestamp': timestamp,
                'duration': actual_duration
            })
            print(f"[Step7] Clip {i+1} OK: {timestamp:.1f}s - {timestamp + actual_duration:.1f}s ({actual_duration:.1f}s)")
        else:
            print(f"[Step7] Clip {i+1} ERREUR preparation")
    
    if not prepared_clips:
        result['error'] = 'Aucun clip valide prepare'
        shutil.rmtree(temp_dir, ignore_errors=True)
        return result
    
    # Trier par timestamp
    prepared_clips.sort(key=lambda x: x['timestamp'])
    
    print(f"[Step7] {len(prepared_clips)} clips prepares, construction du filtre...")
    
    # Construire le filtre FFmpeg avec overlay
    # On utilise trim pour extraire exactement la portion necessaire du B-roll
    # et setpts pour synchroniser avec le timestamp de la video principale
    
    inputs = ['-i', str(input_path)]
    filter_parts = []
    
    for i, clip in enumerate(prepared_clips):
        inputs.extend(['-i', clip['path']])
        
        # Le B-roll doit commencer a t=0 dans son propre flux
        # mais etre affiche au timestamp specifie sur la video principale
        # On utilise setpts pour decaler le B-roll au bon moment
        filter_parts.append(
            f"[{i+1}:v]setpts=PTS+{clip['timestamp']}/TB[broll{i}]"
        )
    
    # Construire la chaine d'overlay
    filter_complex = ";".join(filter_parts) + ";"
    
    if len(prepared_clips) == 1:
        clip = prepared_clips[0]
        end_time = clip['timestamp'] + clip['duration']
        filter_complex += (
            f"[0:v][broll0]overlay=0:0:"
            f"enable='between(t,{clip['timestamp']},{end_time})':eof_action=pass[vout]"
        )
    else:
        # Premier overlay
        clip = prepared_clips[0]
        end_time = clip['timestamp'] + clip['duration']
        filter_complex += (
            f"[0:v][broll0]overlay=0:0:"
            f"enable='between(t,{clip['timestamp']},{end_time})':eof_action=pass[v1]"
        )
        
        # Overlays suivants
        for i in range(1, len(prepared_clips)):
            clip = prepared_clips[i]
            end_time = clip['timestamp'] + clip['duration']
            prev = f"[v{i}]"
            
            if i == len(prepared_clips) - 1:
                out = "[vout]"
            else:
                out = f"[v{i+1}]"
            
            filter_complex += (
                f";{prev}[broll{i}]overlay=0:0:"
                f"enable='between(t,{clip['timestamp']},{end_time})':eof_action=pass{out}"
            )
    
    cmd = [
        FFMPEG, '-y',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-map', '0:a',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'copy',
        '-t', str(video_duration),  # Garder la meme duree
        str(output_path)
    ]
    
    print(f"[Step7] Encodage final...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    if proc.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        final_duration = get_duration(str(output_path))
        result['success'] = True
        result['output_path'] = str(output_path)
        result['clips_used'] = len(prepared_clips)
        print(f"[Step7] OK: illustrated.mp4 ({final_duration:.1f}s, {size_mb:.1f} MB)")
    else:
        error_msg = proc.stderr[-1000:] if proc.stderr else 'Erreur FFmpeg inconnue'
        result['error'] = error_msg
        print(f"[Step7] ERREUR: {error_msg}")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    mode = "replace"  # ou "overlay"
    result = integrate_broll(folder, mode)
    print(f"\nResultat: {result}")

