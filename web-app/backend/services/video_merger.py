"""
Service de fusion vidéo avec FFmpeg
"""
import subprocess
import asyncio
from pathlib import Path
from typing import Optional


class VideoMerger:
    """Gère la fusion et conversion vidéo avec FFmpeg"""
    
    def __init__(self):
        # Utiliser FFmpeg portable dans le projet
        import os
        possible_paths = [
            r"C:\Dev\Yt\ffmpeg\ffmpeg.exe",  # FFmpeg portable du projet
            "ffmpeg",  # Dans le PATH
        ]
        
        self.ffmpeg_path = "ffmpeg"
        for path in possible_paths:
            if os.path.exists(path):
                self.ffmpeg_path = path
                print(f"[FFmpeg] Utilisation: {path}")
                break
    
    def check_ffmpeg(self) -> bool:
        """Vérifier si FFmpeg est disponible"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    async def merge(
        self,
        screen_path: str,
        webcam_path: Optional[str],
        output_path: str,
        layout: str = "overlay",
        webcam_x: int = 50,
        webcam_y: int = 50,
        webcam_size: int = 300,
        webcam_shape: str = "circle",
        border_color: str = "#FFB6C1",
        border_width: int = 4
    ) -> bool:
        """
        Fusionner écran + webcam selon le layout
        
        Args:
            screen_path: Chemin vidéo écran
            webcam_path: Chemin vidéo webcam (optionnel)
            output_path: Chemin de sortie
            layout: overlay, side_by_side, screen_only, webcam_only
            webcam_x, webcam_y: Position webcam (pour overlay)
            webcam_size: Taille webcam
            webcam_shape: circle, rounded, square
            border_color: Couleur du bord
        """
        try:
            print(f"[Merge] screen={screen_path}, webcam={webcam_path}, layout={layout}")
            print(f"[Merge] Position: x={webcam_x}, y={webcam_y}, size={webcam_size}, shape={webcam_shape}")
            
            # Vérifier que les fichiers existent
            from pathlib import Path
            if not Path(screen_path).exists():
                print(f"[Merge] ERREUR: Fichier écran introuvable: {screen_path}")
                return False
            if webcam_path and not Path(webcam_path).exists():
                print(f"[Merge] ERREUR: Fichier webcam introuvable: {webcam_path}")
                return False
                
            print(f"[Merge] Fichiers OK - Ecran: {Path(screen_path).stat().st_size} bytes")
            if webcam_path:
                print(f"[Merge] Fichiers OK - Webcam: {Path(webcam_path).stat().st_size} bytes")
            
            # Si pas de webcam ou layout écran seul
            if not webcam_path or layout == "screen_only":
                print("[Merge] Mode: conversion simple")
                return await self.convert(screen_path, output_path, "1080p")
            
            # Si webcam seule - avec fond dégradé et coins arrondis
            if layout == "webcam_only":
                print("[Merge] Mode: webcam seule avec fond dégradé")
                return await self._convert_webcam_only(webcam_path, output_path)
            
            # Côte à côte
            if layout == "side_by_side":
                print("[Merge] Mode: côte à côte")
                return await self._merge_side_by_side(
                    screen_path, webcam_path, output_path, webcam_shape
                )
            
            # Overlay (défaut)
            print("[Merge] Mode: overlay")
            return await self._merge_overlay(
                screen_path, webcam_path, output_path,
                webcam_x, webcam_y, webcam_size, webcam_shape, border_color, border_width
            )
            
        except Exception as e:
            import traceback
            print(f"[Merge] Exception: {e}")
            print(traceback.format_exc())
            return False
    
    async def _merge_overlay(
        self,
        screen_path: str,
        webcam_path: str,
        output_path: str,
        webcam_x: int,
        webcam_y: int,
        webcam_size: int,
        webcam_shape: str,
        border_color: str = "#FFB6C1",
        border_width: int = 4
    ) -> bool:
        """Fusion overlay (webcam sur écran)"""
        
        # Convertir la couleur hex en RGB pour FFmpeg
        border_color_hex = border_color.lstrip('#')
        if len(border_color_hex) == 6:
            border_rgb = f"0x{border_color_hex}"
        else:
            border_rgb = "0xFFB6C1"  # Défaut rose
        
        # Crop carré centré + redimensionnement final avec lanczos pour qualité optimale
        inner_size = webcam_size - (border_width * 2) if border_width > 0 else webcam_size
        # Directement depuis la source HD : crop carré → scale final avec lanczos
        # Pas de pré-réduction pour conserver la qualité maximale
        crop_scale_fps = f"fps=60,crop='min(iw,ih)':'min(iw,ih)',scale={inner_size}:{inner_size}:flags=lanczos"
        
        if webcam_shape == "circle":
            shape_filter = (
                f"[1:v]{crop_scale_fps},"
                f"format=rgba,"
                f"geq=lum='p(X,Y)':a='if(lt(pow(X-{inner_size//2},2)+pow(Y-{inner_size//2},2),pow({inner_size//2},2)),255,0)'"
                f"[webcam_shaped]"
            )
        elif webcam_shape == "rounded":
            shape_filter = f"[1:v]{crop_scale_fps},format=rgba[webcam_shaped]"
        else:
            shape_filter = f"[1:v]{crop_scale_fps}[webcam_shaped]"
        
        # Ajouter la bordure si nécessaire
        if border_width > 0:
            if webcam_shape == "circle":
                # Bordure CIRCULAIRE: créer un cercle coloré puis overlay la webcam au centre
                border_filter = (
                    f"color=c={border_rgb}:s={webcam_size}x{webcam_size}:d=1,format=rgba,"
                    f"geq=lum='p(X,Y)':a='if(lt(pow(X-{webcam_size//2},2)+pow(Y-{webcam_size//2},2),pow({webcam_size//2},2)),255,0)'"
                    f"[border_circle];"
                    f"[border_circle][webcam_shaped]overlay={border_width}:{border_width}[webcam_with_border];"
                )
            else:
                # Bordure carrée pour les autres formes
                border_filter = (
                    f"color=c={border_rgb}:s={webcam_size}x{webcam_size}:d=1[border];"
                    f"[border][webcam_shaped]overlay={border_width}:{border_width}[webcam_with_border];"
                )
            webcam_output = "[webcam_with_border]"
        else:
            border_filter = ""
            webcam_output = "[webcam_shaped]"
        
        filter_complex = (
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=60[screen];"
            f"{shape_filter};"
            f"{border_filter}"
            f"[screen]{webcam_output}overlay={webcam_x}:{webcam_y}[out]"
        )
        
        cmd = [
            self.ffmpeg_path,
            "-i", screen_path,
            "-r", "60",  # Forcer lecture webcam à 30 fps (important pour VFR)
            "-i", webcam_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-maxrate", "8M",  # Limiter le bitrate max pour éviter le lag
            "-bufsize", "16M",  # Buffer pour le bitrate
            "-threads", "0",  # Utiliser tous les threads disponibles
            "-vsync", "cfr",  # Framerate constant en sortie
            "-c:a", "aac",
            "-b:a", "256k",  # Bitrate audio amélioré
            "-ar", "48000",  # Sample rate standard pour YouTube
            "-y",
            output_path
        ]
        
        return await self._run_ffmpeg(cmd)
    
    async def _merge_side_by_side(
        self,
        screen_path: str,
        webcam_path: str,
        output_path: str,
        webcam_shape: str
    ) -> bool:
        """Fusion côte à côte"""
        
        screen_width = 1280
        webcam_width = 640
        height = 1080
        wc_size = min(webcam_width - 40, height - 40)
        
        # Directement depuis la source HD avec lanczos pour qualité optimale
        if webcam_shape == "circle":
            webcam_filter = (
                f"[1:v]fps=60,crop='min(iw,ih)':'min(iw,ih)',scale={wc_size}:{wc_size}:flags=lanczos,"
                f"format=rgba,"
                f"geq=lum='p(X,Y)':a='if(lt(pow(X-{wc_size//2},2)+pow(Y-{wc_size//2},2),pow({wc_size//2},2)),255,0)'"
                f"[webcam_shaped]"
            )
        else:
            webcam_filter = f"[1:v]fps=60,crop='min(iw,ih)':'min(iw,ih)',scale={wc_size}:{wc_size}:flags=lanczos,format=rgba[webcam_shaped]"
        
        filter_complex = (
            f"color=c=black:s=1920x1080:d=1[bg];"
            f"[0:v]scale={screen_width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={screen_width}:{height}:(ow-iw)/2:(oh-ih)/2,fps=60[screen];"
            f"{webcam_filter};"
            f"[bg][screen]overlay=0:0[with_screen];"
            f"[with_screen][webcam_shaped]overlay={screen_width + (webcam_width - wc_size)//2}:{(height - wc_size)//2}[out]"
        )
        
        cmd = [
            self.ffmpeg_path,
            "-i", screen_path,
            "-r", "60",  # Forcer lecture webcam à 30 fps (important pour VFR)
            "-i", webcam_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-vsync", "cfr",  # Framerate constant en sortie
            "-t", "shortest",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-y",
            output_path
        ]
        
        return await self._run_ffmpeg(cmd)
    
    async def _convert_webcam_only(
        self,
        webcam_path: str,
        output_path: str
    ) -> bool:
        """
        Convertir webcam seule avec fond dégradé violet/noir et coins arrondis
        """
        # Dimensions finales 1080p
        width = 1920
        height = 1080
        
        # Taille webcam (85% du conteneur comme dans le frontend)
        webcam_width = int(width * 0.85)  # ~1632
        webcam_height = int(height * 0.85)  # ~918
        
        # Position centrée
        x_offset = (width - webcam_width) // 2
        y_offset = (height - webcam_height) // 2
        
        # Rayon des coins arrondis (équivalent au rounded-3xl de Tailwind)
        r = 24
        
        print(f"[Merge] Webcam only: {webcam_width}x{webcam_height} centré sur {width}x{height}")
        
        # Filtre complexe avec fond dégradé et coins arrondis
        # Note: On utilise une approche simplifiée avec un fond solide foncé
        # car les gradients FFmpeg sont complexes à gérer
        filter_complex = (
            # Fond dégradé via superposition de couleurs
            # Base noire
            f"color=c=0x0d0d0d:s={width}x{height}:d=1[bg_black];"
            # Cercle violet en haut à gauche pour effet dégradé
            f"color=c=0x581c87:s={width}x{height}:d=1,"
            f"format=rgba,"
            f"geq=r='p(X,Y)':g='p(X,Y)':b='p(X,Y)':"
            f"a='255*exp(-((X-200)*(X-200)+(Y-200)*(Y-200))/(2*400*400))'"
            f"[purple_glow];"
            # Superposer le violet sur le noir
            f"[bg_black][purple_glow]overlay=format=auto[bg];"
            
            # Webcam redimensionnée avec lanczos pour qualité optimale
            f"[0:v]scale={webcam_width}:{webcam_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={webcam_width}:{webcam_height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps=60[webcam];"
            
            # Overlay webcam centrée sur le fond
            f"[bg][webcam]overlay={x_offset}:{y_offset}:shortest=1[out]"
        )
        
        cmd = [
            self.ffmpeg_path,
            "-r", "60",
            "-i", webcam_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-vsync", "cfr",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-y",
            output_path
        ]
        
        success = await self._run_ffmpeg(cmd)
        
        # Fallback simplifié si le premier filtre échoue
        if not success:
            print("[Merge] Fallback: fond violet simple")
            filter_complex_simple = (
                # Fond violet/noir simple
                f"color=c=0x1a0a2e:s={width}x{height}:d=1[bg];"
                
                # Webcam redimensionnée avec lanczos
                f"[0:v]scale={webcam_width}:{webcam_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={webcam_width}:{webcam_height}:(ow-iw)/2:(oh-ih)/2:black,fps=60[webcam];"
                
                # Overlay simple
                f"[bg][webcam]overlay={x_offset}:{y_offset}:shortest=1[out]"
            )
            
            cmd_simple = [
                self.ffmpeg_path,
                "-r", "60",
                "-i", webcam_path,
                "-filter_complex", filter_complex_simple,
                "-map", "[out]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-vsync", "cfr",
                "-c:a", "aac",
                "-b:a", "256k",
                "-ar", "48000",
                "-y",
                output_path
            ]
            
            return await self._run_ffmpeg(cmd_simple)
        
        return success
    
    async def convert(
        self,
        input_path: str,
        output_path: str,
        resolution: str = "1080p"
    ) -> bool:
        """Convertir une vidéo"""
        
        res_map = {
            "720p": "1280:720",
            "1080p": "1920:1080",
            "1440p": "2560:1440",
            "4k": "3840:2160"
        }
        
        scale = res_map.get(resolution, "1920:1080")
        
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-vf", f"scale={scale}:force_original_aspect_ratio=decrease:flags=lanczos,pad={scale}:(ow-iw)/2:(oh-ih)/2",
            "-map", "0:v",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-y",
            output_path
        ]
        
        return await self._run_ffmpeg(cmd)
    
    async def _run_ffmpeg(self, cmd: list) -> bool:
        """Exécuter une commande FFmpeg"""
        try:
            print(f"[FFmpeg] Commande: {' '.join(cmd[:3])}...")
            
            # Sur Windows, utiliser subprocess.run dans un thread pool
            def run_ffmpeg():
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5 minutes max
                )
                return result
            
            # Exécuter dans un thread pool pour ne pas bloquer
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_ffmpeg)
            
            if result.returncode == 0:
                print("[FFmpeg] Succes!")
                return True
            
            print(f"[FFmpeg] Erreur (code {result.returncode}): {result.stderr[:500]}")
            return False
            
        except Exception as e:
            import traceback
            print(f"[FFmpeg] Exception: {e}")
            print(traceback.format_exc())
            return False

