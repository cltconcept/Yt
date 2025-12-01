"""
Etape 3 : Couper les silences sur les fichiers sources
- Reutilise les segments detectes par Step 2 (segments.json)
- Applique les memes coupures sur screen.mp4 -> screennosilence.mp4
- Applique les memes coupures sur webcam.mp4 -> webcamnosilence.mp4
"""
import subprocess
import os
import shutil
import re
import json
from pathlib import Path

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')

DEFAULT_SILENCE_THRESHOLD = -30
DEFAULT_SILENCE_DURATION = 1.0
DEFAULT_PADDING = 0.1


def get_duration(file_path: str) -> float:
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def detect_silences(file_path: str, threshold_db: int, min_duration: float) -> list:
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
    segments = []
    last_end = 0.0
    
    for s in silences:
        seg_start = max(0, last_end - padding) if last_end > 0 else last_end
        seg_end = min(total_duration, s['start'] + padding)
        if seg_end > seg_start + 0.1:
            segments.append({'start': seg_start, 'end': seg_end})
        last_end = s['end'] if s['end'] else s['start']
    
    if last_end < total_duration:
        segments.append({'start': max(0, last_end - padding), 'end': total_duration})
    
    merged = []
    for seg in segments:
        if merged and seg['start'] - merged[-1]['end'] < 0.5:
            merged[-1]['end'] = seg['end']
        else:
            merged.append(seg.copy())
    
    return merged


def cut_video_with_segments(input_path: Path, output_path: Path, segments: list, 
                            temp_dir: Path, include_audio: bool = True) -> bool:
    """Coupe une video selon les segments donnes en utilisant les filtres select/aselect"""
    
    # Construire l'expression select pour les segments à garder
    select_parts = []
    for seg in segments:
        select_parts.append(f"between(t,{seg['start']},{seg['end']})")
    
    select_expr = '+'.join(select_parts)
    
    # Construire la commande FFmpeg avec select filter
    if include_audio:
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
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            str(output_path)
        ]
    else:
        filter_complex = f"[0:v]select='{select_expr}',setpts=N/FRAME_RATE/TB[outv]"
        cmd = [
            FFMPEG, '-y',
            '-i', str(input_path),
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-an',
            '-movflags', '+faststart',
            str(output_path)
        ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    return proc.returncode == 0 and output_path.exists()


def cut_sources(video_folder: str,
                threshold_db: int = DEFAULT_SILENCE_THRESHOLD,
                min_silence: float = DEFAULT_SILENCE_DURATION,
                padding: float = DEFAULT_PADDING) -> dict:
    """
    Coupe screen.mp4 et webcam.mp4 avec les memes segments
    
    Args:
        video_folder: Chemin du dossier video
    
    Returns:
        dict avec success, screen_duration, webcam_duration, segments, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'screen_duration': None,
        'webcam_duration': None,
        'segments': 0
    }
    
    # Fichiers
    original_path = video_folder / 'original.mp4'
    screen_path = video_folder / 'screen.mp4'
    webcam_path = video_folder / 'webcam.mp4'
    combined_path = video_folder / 'combined.webm'  # Mode Canvas compositing
    screen_output = video_folder / 'screennosilence.mp4'
    webcam_output = video_folder / 'webcamnosilence.mp4'
    temp_dir = video_folder / 'temp_cut'
    
    # Mode Canvas compositing : pas de fichiers sources séparés
    if combined_path.exists() and not screen_path.exists():
        print("[Step3] Mode Canvas détecté - pas de fichiers sources séparés à couper")
        result['success'] = True
        result['segments'] = 0
        return result
    
    # Verifier fichiers (mode classique)
    if not screen_path.exists():
        result['error'] = 'screen.mp4 manquant'
        return result
    
    # Charger les segments depuis Step 2 (au lieu de redetecter)
    segments_file = video_folder / 'segments.json'
    if segments_file.exists():
        print(f"[Step3] Chargement des segments depuis segments.json...")
        with open(segments_file, 'r', encoding='utf-8') as f:
            segments_data = json.load(f)
        segments = segments_data['segments']
        print(f"[Step3] {len(segments)} segment(s) charges depuis Step 2")
        result['segments'] = len(segments)
    else:
        # Fallback: detection si segments.json n'existe pas
        print(f"[Step3] segments.json non trouve, detection des silences sur original.mp4...")
        if not original_path.exists():
            result['error'] = 'original.mp4 et segments.json manquants'
            return result
        duration = get_duration(str(original_path))
        silences = detect_silences(str(original_path), threshold_db, min_silence)
        segments = get_speech_segments(silences, duration, padding)
        print(f"[Step3] {len(silences)} silence(s), {len(segments)} segment(s)")
        result['segments'] = len(segments)
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(exist_ok=True)
    
    # Couper screen (avec audio)
    print(f"[Step3] Coupe screen.mp4...")
    temp_screen = temp_dir / 'screen'
    temp_screen.mkdir(exist_ok=True)
    
    if cut_video_with_segments(screen_path, screen_output, segments, temp_screen, include_audio=True):
        dur = get_duration(str(screen_output))
        size = screen_output.stat().st_size / 1024 / 1024
        result['screen_duration'] = dur
        print(f"[Step3] OK: screennosilence.mp4 - {dur:.2f}s ({size:.2f} MB)")
    else:
        result['error'] = 'Erreur coupe screen'
        shutil.rmtree(temp_dir, ignore_errors=True)
        return result
    
    # Couper webcam (sans audio)
    if webcam_path.exists():
        print(f"[Step3] Coupe webcam.mp4...")
        temp_webcam = temp_dir / 'webcam'
        temp_webcam.mkdir(exist_ok=True)
        
        if cut_video_with_segments(webcam_path, webcam_output, segments, temp_webcam, include_audio=False):
            dur = get_duration(str(webcam_output))
            size = webcam_output.stat().st_size / 1024 / 1024
            result['webcam_duration'] = dur
            print(f"[Step3] OK: webcamnosilence.mp4 - {dur:.2f}s ({size:.2f} MB)")
        else:
            result['error'] = 'Erreur coupe webcam'
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result
    else:
        print(f"[Step3] Pas de webcam.mp4, skip")
    
    # Nettoyer
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    result['success'] = True
    print(f"[Step3] Termine!")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = cut_sources(folder)
    print(f"\nResultat: {result}")

