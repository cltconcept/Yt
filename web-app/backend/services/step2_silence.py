"""
Etape 2 : Suppression des silences -> nosilence.mp4
- Detecte les silences dans original.mp4
- Coupe et concatene les segments parles
- Cree nosilence.mp4
- Sauvegarde les segments dans segments.json pour Step 3
"""
import subprocess
import os
import shutil
import re
import json
from pathlib import Path

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')

# Parametres par defaut
DEFAULT_SILENCE_THRESHOLD = -30  # dB
DEFAULT_SILENCE_DURATION = 1.0   # secondes (silences > 1s seront supprimes)
DEFAULT_PADDING = 0.1            # secondes de padding pour transitions douces


def get_duration(file_path: str) -> float:
    """Retourne la duree d'une video en secondes"""
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def detect_silences(file_path: str, threshold_db: int, min_duration: float) -> list:
    """Detecte les silences dans une video"""
    result = subprocess.run([
        FFMPEG, '-i', str(file_path),
        '-af', f'silencedetect=noise={threshold_db}dB:d={min_duration}',
        '-f', 'null', '-'
    ], capture_output=True, text=True)
    
    silences = []
    for line in result.stderr.split('\n'):
        if 'silence_start' in line:
            match = re.search(r'silence_start: ([\d.]+)', line)
            if match:
                silences.append({'start': float(match.group(1)), 'end': None})
        elif 'silence_end' in line:
            match = re.search(r'silence_end: ([\d.]+)', line)
            if match and silences and silences[-1]['end'] is None:
                silences[-1]['end'] = float(match.group(1))
    
    return silences


def get_speech_segments(silences: list, total_duration: float, padding: float) -> list:
    """Convertit les silences en segments parles avec padding"""
    segments = []
    last_end = 0.0
    
    for s in silences:
        seg_start = max(0, last_end - padding) if last_end > 0 else last_end
        seg_end = min(total_duration, s['start'] + padding)
        if seg_end > seg_start + 0.1:
            segments.append({'start': seg_start, 'end': seg_end})
        last_end = s['end'] if s['end'] else s['start']
    
    # Dernier segment
    if last_end < total_duration:
        segments.append({'start': max(0, last_end - padding), 'end': total_duration})
    
    # Fusionner segments proches (< 0.5s)
    merged = []
    for seg in segments:
        if merged and seg['start'] - merged[-1]['end'] < 0.5:
            merged[-1]['end'] = seg['end']
        else:
            merged.append(seg.copy())
    
    return merged


def remove_silences(video_folder: str,
                    threshold_db: int = DEFAULT_SILENCE_THRESHOLD,
                    min_silence: float = DEFAULT_SILENCE_DURATION,
                    padding: float = DEFAULT_PADDING) -> dict:
    """
    Supprime les silences de original.mp4 -> nosilence.mp4
    
    Args:
        video_folder: Chemin du dossier contenant original.mp4
        threshold_db: Seuil de detection en dB (default -30)
        min_silence: Duree minimum d'un silence en secondes (default 1.0)
        padding: Padding avant/apres chaque segment (default 0.1)
    
    Returns:
        dict avec success, original_duration, final_duration, segments, reduction, error
    """
    video_folder = Path(video_folder)
    input_path = video_folder / 'original.mp4'
    output_path = video_folder / 'nosilence.mp4'
    temp_dir = video_folder / 'temp_segments'
    
    result = {
        'success': False,
        'error': None,
        'original_duration': None,
        'final_duration': None,
        'segments': 0,
        'reduction': 0
    }
    
    # Verifier fichier source
    if not input_path.exists():
        result['error'] = 'original.mp4 manquant'
        return result
    
    # Obtenir duree
    duration = get_duration(str(input_path))
    result['original_duration'] = duration
    
    # Detecter silences
    print(f"[Step2] Detection des silences (seuil: {min_silence}s, {threshold_db}dB)...")
    silences = detect_silences(str(input_path), threshold_db, min_silence)
    print(f"[Step2] {len(silences)} silence(s) detecte(s)")
    
    # Obtenir segments parles
    segments = get_speech_segments(silences, duration, padding)
    total_speech = sum(s['end'] - s['start'] for s in segments)
    print(f"[Step2] {len(segments)} segment(s), duree: {total_speech:.1f}s")
    
    # Sauvegarder les segments pour Step 3
    segments_file = video_folder / 'segments.json'
    with open(segments_file, 'w', encoding='utf-8') as f:
        json.dump({
            'segments': segments,
            'silences': silences,
            'original_duration': duration,
            'threshold_db': threshold_db,
            'min_silence': min_silence,
            'padding': padding
        }, f, indent=2)
    print(f"[Step2] Segments sauvegardes dans segments.json")
    
    # Nettoyer
    if output_path.exists():
        output_path.unlink()
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(exist_ok=True)
    
    # Méthode 1: Utiliser le filtre select + concat pour éviter les ré-encodages multiples
    # Construire le filtre pour sélectionner les segments à garder
    print(f"[Step2] Construction du filtre de sélection...")
    
    # Construire l'expression select pour la vidéo et l'audio
    select_parts = []
    for seg in segments:
        select_parts.append(f"between(t,{seg['start']},{seg['end']})")
    
    select_expr = '+'.join(select_parts)
    
    # Utiliser le filtre select + aselect pour couper précisément
    filter_complex = (
        f"[0:v]select='{select_expr}',setpts=N/FRAME_RATE/TB[outv];"
        f"[0:a]aselect='{select_expr}',asetpts=N/SR/TB[outa]"
    )
    
    cmd = [
        FFMPEG, '-y',
        '-i', str(input_path),
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '192k',  # Un seul encodage audio
        '-movflags', '+faststart',
        str(output_path)
    ]
    
    print(f"[Step2] Encodage en cours...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    if proc.returncode == 0 and output_path.exists():
        final_dur = get_duration(str(output_path))
        size_mb = output_path.stat().st_size / 1024 / 1024
        
        result['success'] = True
        result['final_duration'] = final_dur
        result['segments'] = len(segments)
        result['reduction'] = round((1 - final_dur / duration) * 100)
        
        print(f"[Step2] OK: nosilence.mp4 - {final_dur:.2f}s ({size_mb:.2f} MB) - reduction {result['reduction']}%")
    else:
        result['error'] = proc.stderr[-500:] if proc.stderr else 'Erreur inconnue'
        print(f"[Step2] ERREUR: {result['error']}")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = remove_silences(folder)
    print(f"\nResultat: {result}")

