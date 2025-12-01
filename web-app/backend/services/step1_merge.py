"""
Etape 1 : Fusion screen + webcam -> original.mp4
- Lit screen.mp4, webcam.mp4 et config.json depuis le dossier video
- Cree original.mp4 avec la webcam en overlay (cercle, bordure)
- Supporte les layout_switches pour le switch auto (overlay ↔ webcam_only)
- Optimisations : 30fps, CRF 18, profile high, audio 48kHz
"""
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')


def get_duration(file_path: str) -> float:
    """Retourne la duree d'une video en secondes"""
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(file_path)
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def build_switch_overlay_filter(
    layout_switches: List[Dict],
    webcam_x: int, webcam_y: int,
    webcam_size: int, webcam_shape: str,
    border_color: str, border_width: int,
    video_duration: float
) -> str:
    """
    Construit un filtre FFmpeg avec overlay dynamique selon les timestamps.
    
    layout_switches: [{"timestamp": 5.0, "layout": "webcam_only"}, {"timestamp": 10.0, "layout": "overlay"}, ...]
    
    Utilise enable='between(t,start,end)' pour activer/désactiver les overlays.
    """
    inner_size = webcam_size - (border_width * 2)
    half_inner = inner_size // 2
    half_size = webcam_size // 2
    
    # Trier les switches par timestamp
    switches = sorted(layout_switches, key=lambda x: x['timestamp'])
    
    # Créer les intervalles avec leur layout
    # On commence toujours en mode overlay (layout par défaut)
    intervals = []
    current_start = 0.0
    current_layout = 'overlay'
    
    for switch in switches:
        ts = switch['timestamp']
        new_layout = switch['layout']
        
        if ts > current_start:
            intervals.append({
                'start': current_start,
                'end': ts,
                'layout': current_layout
            })
        
        current_start = ts
        current_layout = new_layout
    
    # Ajouter le dernier intervalle jusqu'à la fin
    if current_start < video_duration:
        intervals.append({
            'start': current_start,
            'end': video_duration + 1,  # +1 pour être sûr de couvrir la fin
            'layout': current_layout
        })
    
    print(f"[Step1] Switch auto: {len(intervals)} intervalle(s) détecté(s)")
    for i, interval in enumerate(intervals):
        print(f"  {i+1}. {interval['start']:.1f}s → {interval['end']:.1f}s : {interval['layout']}")
    
    # Construire les conditions enable pour overlay (quand layout == 'overlay')
    overlay_conditions = []
    for interval in intervals:
        if interval['layout'] == 'overlay':
            overlay_conditions.append(f"between(t,{interval['start']},{interval['end']})")
    
    # Construire les conditions enable pour webcam plein écran (quand layout == 'webcam_only')
    webcam_full_conditions = []
    for interval in intervals:
        if interval['layout'] == 'webcam_only':
            webcam_full_conditions.append(f"between(t,{interval['start']},{interval['end']})")
    
    # Si pas de switch vers webcam_only, retourner None pour utiliser le mode normal
    if not webcam_full_conditions:
        print(f"[Step1] Pas de mode webcam_only, utilisation du mode standard")
        return None
    
    overlay_enable = "+".join(overlay_conditions) if overlay_conditions else "0"
    webcam_full_enable = "+".join(webcam_full_conditions) if webcam_full_conditions else "0"
    
    # Construire le filtre webcam selon la forme
    if webcam_shape == 'circle':
        webcam_small_filter = (
            f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos,"
            f"format=rgba,geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
            f"a='if(lt(pow(X-{half_inner},2)+pow(Y-{half_inner},2),pow({half_inner},2)),255,0)'[wc_small];"
            f"color=c={border_color}:s={webcam_size}x{webcam_size},format=rgba,"
            f"geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
            f"a='if(lt(pow(X-{half_size},2)+pow(Y-{half_size},2),pow({half_size},2)),255,0)'[bd];"
            f"[bd][wc_small]overlay={border_width}:{border_width}[wcb]"
        )
    elif webcam_shape == 'rounded':
        n = 10
        webcam_small_filter = (
            f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos,"
            f"format=rgba,geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
            f"a='if(lt(pow(abs(X-{half_inner}),{n})+pow(abs(Y-{half_inner}),{n}),pow({half_inner},{n})),255,0)'[wc_small];"
            f"color=c={border_color}:s={webcam_size}x{webcam_size},format=rgba,"
            f"geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
            f"a='if(lt(pow(abs(X-{half_size}),{n})+pow(abs(Y-{half_size}),{n}),pow({half_size},{n})),255,0)'[bd];"
            f"[bd][wc_small]overlay={border_width}:{border_width}[wcb]"
        )
    else:
        webcam_small_filter = (
            f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos[wc_small];"
            f"color=c={border_color}:s={webcam_size}x{webcam_size}[bd];"
            f"[bd][wc_small]overlay={border_width}:{border_width}[wcb]"
        )
    
    # Taille et position du screen en miniature (pour mode webcam_only)
    SCREEN_MINI_SIZE = 800  # Taille du rectangle screen en mode webcam_only
    SCREEN_MINI_HEIGHT = int(SCREEN_MINI_SIZE * 1080 / 1920)  # Ratio 16:9
    SCREEN_MINI_MARGIN = 20  # Marge depuis le bord
    screen_mini_x = 1920 - SCREEN_MINI_SIZE - SCREEN_MINI_MARGIN  # En bas à droite
    screen_mini_y = 1080 - SCREEN_MINI_HEIGHT - SCREEN_MINI_MARGIN
    
    # Filtre complexe avec overlay conditionnel
    # Mode overlay : screen plein écran + webcam en petit
    # Mode webcam_only : webcam plein écran + screen en petit rectangle en bas à droite
    filter_complex = (
        # Screen plein écran (pour mode overlay)
        f"[0:v]fps=30,scale=1920:1080:flags=lanczos[screen];"
        # Screen en miniature avec bordure (pour mode webcam_only)
        f"[0:v]fps=30,scale={SCREEN_MINI_SIZE}:{SCREEN_MINI_HEIGHT}:flags=lanczos,"
        f"drawbox=x=0:y=0:w={SCREEN_MINI_SIZE}:h={SCREEN_MINI_HEIGHT}:c={border_color}:t=3[screen_mini];"
        # Webcam plein écran (pour mode webcam_only)
        f"[1:v]fps=30,scale=1920:1080:flags=lanczos[wc_full];"
        # Webcam en petit avec bordure (pour mode overlay)
        f"{webcam_small_filter};"
        # Commencer avec le screen plein écran
        # Overlay webcam plein écran par dessus (quand webcam_only)
        f"[screen][wc_full]overlay=0:0:enable='{webcam_full_enable}'[with_wc_full];"
        # Overlay screen miniature en bas à droite (quand webcam_only)
        f"[with_wc_full][screen_mini]overlay={screen_mini_x}:{screen_mini_y}:enable='{webcam_full_enable}'[with_screen_mini];"
        # Overlay webcam petit (quand overlay)
        f"[with_screen_mini][wcb]overlay={webcam_x}:{webcam_y}:enable='{overlay_enable}'[out]"
    )
    
    return filter_complex


def merge_videos(video_folder: str) -> dict:
    """
    Fusionne screen.mp4 + webcam.mp4 -> original.mp4
    OU optimise combined.webm -> original.mp4 (mode Canvas compositing)
    Utilise les parametres de config.json
    
    Args:
        video_folder: Chemin du dossier contenant screen.mp4, webcam.mp4, config.json
                      OU combined.webm (mode Canvas)
    
    Returns:
        dict avec success, duration, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'output_path': None,
        'duration': None
    }
    
    output_path = video_folder / 'original.mp4'
    
    # ===== MODE CANVAS COMPOSITING =====
    # Si combined.webm existe, juste optimiser avec FFmpeg (pas besoin de merge)
    combined_path = video_folder / 'combined.webm'
    if combined_path.exists():
        print(f"[Step1] Mode Canvas détecté - Optimisation de combined.webm...")
        
        cmd = [
            FFMPEG, '-y',
            '-i', str(combined_path),
            '-vf', 'fps=30,scale=1920:1080:flags=lanczos',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-profile:v', 'high', '-level', '4.1',
            '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
            str(output_path)
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        
        if proc.returncode == 0 and output_path.exists():
            duration = get_duration(str(output_path))
            size_mb = output_path.stat().st_size / 1024 / 1024
            
            result['success'] = True
            result['output_path'] = str(output_path)
            result['duration'] = duration
            
            print(f"[Step1] OK (Canvas): original.mp4 - {duration:.2f}s ({size_mb:.2f} MB)")
        else:
            result['error'] = proc.stderr[-500:] if proc.stderr else 'Erreur inconnue'
            print(f"[Step1] ERREUR (Canvas): {result['error']}")
        
        return result
    # ===== FIN MODE CANVAS COMPOSITING =====
    
    # Verifier fichiers requis (mode classique)
    screen_path = video_folder / 'screen.mp4'
    webcam_path = video_folder / 'webcam.mp4'
    config_path = video_folder / 'config.json'
    
    if not screen_path.exists():
        result['error'] = 'screen.mp4 manquant'
        return result
    
    if not config_path.exists():
        result['error'] = 'config.json manquant'
        return result
    
    # Charger config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    webcam_x = config.get('webcam_x', 1486)
    webcam_y = config.get('webcam_y', 645)
    webcam_size = config.get('webcam_size', 389)
    webcam_shape = config.get('webcam_shape', 'circle')
    border_color = config.get('border_color', '#FFB6C1')
    border_width = config.get('border_width', 4)
    layout_switches = config.get('layout_switches', [])
    
    print(f"[Step1] Config: position=({webcam_x},{webcam_y}), size={webcam_size}, shape={webcam_shape}")
    if layout_switches:
        print(f"[Step1] Switch auto: {len(layout_switches)} switch(es) détecté(s)")
    
    # Calculer dimensions
    inner_size = webcam_size - (border_width * 2)
    half_inner = inner_size // 2
    half_size = webcam_size // 2
    
    # Construire le filtre selon la presence de webcam
    if webcam_path.exists():
        # Avec webcam - overlay avec bordure
        # Optimisations : 30fps, scaling lanczos pour texte net
        
        # Vérifier si on a des layout_switches pour le switch auto
        filter_complex = None
        if layout_switches:
            video_duration = get_duration(str(screen_path))
            filter_complex = build_switch_overlay_filter(
                layout_switches=layout_switches,
                webcam_x=webcam_x, webcam_y=webcam_y,
                webcam_size=webcam_size, webcam_shape=webcam_shape,
                border_color=border_color, border_width=border_width,
                video_duration=video_duration
            )
        
        # Si pas de switch auto ou pas de mode webcam_only, utiliser le mode standard
        if filter_complex is None:
            # Construire le filtre selon la forme
            if webcam_shape == 'circle':
                # Cercle : masque circulaire avec geq
                webcam_filter = (
                    f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos,"
                    f"format=rgba,geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                    f"a='if(lt(pow(X-{half_inner},2)+pow(Y-{half_inner},2),pow({half_inner},2)),255,0)'[wc];"
                    f"color=c={border_color}:s={webcam_size}x{webcam_size},format=rgba,"
                    f"geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                    f"a='if(lt(pow(X-{half_size},2)+pow(Y-{half_size},2),pow({half_size},2)),255,0)'[bd];"
                    f"[bd][wc]overlay={border_width}:{border_width}[wcb]"
                )
            elif webcam_shape == 'rounded':
                # Coins arrondis : superellipse avec n=10 (côtés plats, coins arrondis)
                n = 10
                webcam_filter = (
                    f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos,"
                    f"format=rgba,geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                    f"a='if(lt(pow(abs(X-{half_inner}),{n})+pow(abs(Y-{half_inner}),{n}),pow({half_inner},{n})),255,0)'[wc];"
                    f"color=c={border_color}:s={webcam_size}x{webcam_size},format=rgba,"
                    f"geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                    f"a='if(lt(pow(abs(X-{half_size}),{n})+pow(abs(Y-{half_size}),{n}),pow({half_size},{n})),255,0)'[bd];"
                    f"[bd][wc]overlay={border_width}:{border_width}[wcb]"
                )
            else:
                # Square : pas de masque de transparence, juste un carré avec bordure
                webcam_filter = (
                    f"[1:v]fps=30,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos[wc];"
                    f"color=c={border_color}:s={webcam_size}x{webcam_size}[bd];"
                    f"[bd][wc]overlay={border_width}:{border_width}[wcb]"
                )
            
            filter_complex = (
                f"[0:v]fps=30,scale=1920:1080:flags=lanczos[screen];"
                f"{webcam_filter};"
                f"[screen][wcb]overlay={webcam_x}:{webcam_y}[out]"
            )
        
        cmd = [
            FFMPEG, '-y',
            '-i', str(screen_path),
            '-i', str(webcam_path),
            '-filter_complex', filter_complex,
            '-map', '[out]', '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-profile:v', 'high', '-level', '4.1',
            '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
            '-shortest',
            str(output_path)
        ]
    else:
        # Sans webcam - juste copier screen avec optimisations
        cmd = [
            FFMPEG, '-y',
            '-i', str(screen_path),
            '-vf', 'fps=30,scale=1920:1080:flags=lanczos',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-profile:v', 'high', '-level', '4.1',
            '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
            str(output_path)
        ]
    
    print(f"[Step1] Fusion en cours...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    if proc.returncode == 0 and output_path.exists():
        duration = get_duration(str(output_path))
        size_mb = output_path.stat().st_size / 1024 / 1024
        
        result['success'] = True
        result['output_path'] = str(output_path)
        result['duration'] = duration
        
        print(f"[Step1] OK: original.mp4 - {duration:.2f}s ({size_mb:.2f} MB)")
    else:
        result['error'] = proc.stderr[-500:] if proc.stderr else 'Erreur inconnue'
        print(f"[Step1] ERREUR: {result['error']}")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = merge_videos(folder)
    print(f"\nResultat: {result}")


