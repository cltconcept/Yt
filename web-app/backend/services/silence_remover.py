"""
Service de suppression des silences
- Detecte les silences dans une video
- Coupe et concatene les segments parles
"""
import subprocess
import os
import shutil
import re
from pathlib import Path

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')

# Parametres par defaut
DEFAULT_SILENCE_THRESHOLD = -40  # dB (moins sensible, ignore le bruit de fond)
DEFAULT_SILENCE_DURATION = 2.0   # secondes (uniquement les vraies pauses)
DEFAULT_PADDING = 0.15           # secondes


def get_duration(file_path: str) -> float:
    """Retourne la duree d'une video en secondes"""
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def detect_silences(file_path: str, threshold_db: int = DEFAULT_SILENCE_THRESHOLD, 
                    min_duration: float = DEFAULT_SILENCE_DURATION) -> list:
    """
    Detecte les silences dans une video
    Retourne une liste de {'start': float, 'end': float}
    """
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


def get_speech_segments(silences: list, total_duration: float, 
                        padding: float = DEFAULT_PADDING) -> list:
    """
    Convertit les silences en segments parles avec padding
    """
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


def remove_silences(input_path: str, output_path: str,
                    threshold_db: int = DEFAULT_SILENCE_THRESHOLD,
                    min_silence: float = DEFAULT_SILENCE_DURATION,
                    padding: float = DEFAULT_PADDING) -> dict:
    """
    Supprime les silences d'une video
    Decoupe en segments puis concatene avec stream copy pour sync parfaite
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    temp_dir = input_path.parent / 'temp_segments'
    
    result = {'success': False, 'error': None}
    
    # Obtenir duree
    duration = get_duration(str(input_path))
    
    # Detecter silences
    silences = detect_silences(str(input_path), threshold_db, min_silence)
    print(f"[SilenceRemover] {len(silences)} silences detectes")
    
    # Obtenir segments parles
    segments = get_speech_segments(silences, duration, padding)
    total_speech = sum(s['end'] - s['start'] for s in segments)
    print(f"[SilenceRemover] {len(segments)} segments, duree: {total_speech:.1f}s")
    
    # Nettoyer
    if output_path.exists():
        output_path.unlink()
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(exist_ok=True)
    
    # Decouper segments avec re-encodage pour precision
    print(f"[SilenceRemover] Decoupe en cours...")
    concat_list = []
    for i, seg in enumerate(segments):
        start = seg['start']
        dur = seg['end'] - seg['start']
        seg_file = temp_dir / f'seg_{i:03d}.ts'  # TS pour concat sans perte
        
        # -ss apres -i pour precision, output en TS
        cmd = [
            FFMPEG, '-y',
            '-i', str(input_path),
            '-ss', str(start),
            '-t', str(dur),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-f', 'mpegts',
            str(seg_file)
        ]
        subprocess.run(cmd, capture_output=True)
        concat_list.append(str(seg_file))
    
    # Concatener avec concat protocol (pas demux)
    concat_input = 'concat:' + '|'.join(concat_list)
    
    cmd = [
        FFMPEG, '-y',
        '-i', concat_input,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '192k',
        str(output_path)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    if proc.returncode == 0 and output_path.exists():
        final_dur = get_duration(str(output_path))
        result['success'] = True
        result['original_duration'] = duration
        result['final_duration'] = final_dur
        result['segments'] = len(segments)
        result['reduction'] = round((1 - final_dur / duration) * 100)
    else:
        result['error'] = proc.stderr[-500:] if proc.stderr else 'Erreur inconnue'
    
    return result

