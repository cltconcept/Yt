"""
Etape 4 : Transcription de nosilence.mp4
- Extrait l'audio
- Transcrit avec Groq Whisper
- Sauvegarde transcription.json et transcription.txt
"""
import os
import asyncio
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def extract_audio(video_path: str, audio_path: str) -> bool:
    """Extrait l'audio en MP3"""
    cmd = [
        FFMPEG, '-y',
        '-i', video_path,
        '-vn',
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def correct_words_with_openrouter(text: str, segments: list) -> tuple:
    """
    Corrige l'orthographe/grammaire sans changer le nombre de mots
    Utilise GPT-4o-mini via OpenRouter
    
    Returns:
        tuple (corrected_text, corrected_segments)
    """
    if not OPENROUTER_API_KEY:
        print("[Step4] OpenRouter API key manquante, skip correction")
        return text, segments
    
    import httpx
    
    # Corriger le texte global
    prompt = f"""Corrige UNIQUEMENT l'orthographe et la grammaire du texte suivant.
REGLES STRICTES:
- NE PAS ajouter de mots
- NE PAS supprimer de mots
- NE PAS changer l'ordre des mots
- Garder EXACTEMENT le meme nombre de mots
- Corriger uniquement les fautes d'orthographe et de grammaire

TERMES TECHNIQUES A RESPECTER (ne pas traduire/modifier):
- "VibeAcademy" (en un seul mot, pas "Vibe Academy")
- "Cursor" (pas "curseur")
- "Claude" (l'IA, pas "cloud")
- "GPT" (pas "JiPiTi")
- "API" (pas "a pis")
- "GitHub" (pas "git hub")
- "VS Code" ou "VSCode"
- "Python", "JavaScript", "TypeScript", "React", "Next.js"
- "FFmpeg" (pas "ff mpeg")
- Tout autre terme technique anglais doit rester en anglais

Texte a corriger:
{text}

Reponds UNIQUEMENT avec le texte corrige, rien d'autre."""

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
                "temperature": 0.1  # Basse temperature pour etre precis
            },
            timeout=60
        )
        
        if response.status_code == 200:
            corrected_text = response.json()['choices'][0]['message']['content'].strip()
            
            # Verifier que le nombre de mots est le meme
            original_words = text.split()
            corrected_words = corrected_text.split()
            
            # Accepter une difference de +/- 3 mots (pour les termes techniques fusionnes)
            word_diff = abs(len(original_words) - len(corrected_words))
            if word_diff <= 3:
                print(f"[Step4] Correction OK: {len(original_words)} -> {len(corrected_words)} mots (diff: {word_diff})")
                
                # Corriger chaque segment individuellement
                corrected_segments = []
                for seg in segments:
                    seg_text = seg.get('text', '')
                    if seg_text.strip():
                        # Corriger ce segment
                        seg_prompt = f"""Corrige UNIQUEMENT l'orthographe et la grammaire.
NE CHANGE PAS le nombre de mots. Respecte les termes techniques: VibeAcademy, Cursor, Claude, GPT, API, GitHub, etc.
Reponds UNIQUEMENT avec le texte corrige.

Texte: {seg_text}"""
                        
                        seg_response = httpx.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "openai/gpt-4o-mini",
                                "messages": [{"role": "user", "content": seg_prompt}],
                                "temperature": 0.1
                            },
                            timeout=30
                        )
                        
                        if seg_response.status_code == 200:
                            corrected_seg_text = seg_response.json()['choices'][0]['message']['content'].strip()
                            # Verifier nombre de mots (tolerance +/- 2)
                            seg_diff = abs(len(seg_text.split()) - len(corrected_seg_text.split()))
                            if seg_diff <= 2:
                                seg['text'] = corrected_seg_text
                    
                    corrected_segments.append(seg)
                
                return corrected_text, corrected_segments
            else:
                print(f"[Step4] Correction rejetee: {len(original_words)} -> {len(corrected_words)} mots (diff trop grande)")
                return text, segments
        else:
            print(f"[Step4] Erreur OpenRouter: {response.status_code}")
            return text, segments
            
    except Exception as e:
        print(f"[Step4] Erreur correction: {e}")
        return text, segments


def transcribe_with_groq(audio_path: str, language: str = "fr") -> dict:
    """Transcrit avec Groq Whisper API"""
    import httpx
    
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    with open(audio_path, 'rb') as f:
        files = {
            'file': (Path(audio_path).name, f, 'audio/mpeg'),
            'model': (None, 'whisper-large-v3'),
            'language': (None, language),
            'response_format': (None, 'verbose_json'),
        }
        
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}'
        }
        
        response = httpx.post(url, files=files, headers=headers, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")


def transcribe_video(video_folder: str, language: str = "fr") -> dict:
    """
    Transcrit nosilence.mp4 et sauvegarde les resultats
    
    Args:
        video_folder: Chemin du dossier video
        language: Langue (fr, en, etc.)
    
    Returns:
        dict avec success, text, segments, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'text': None,
        'segments': [],
        'language': language
    }
    
    # Fichiers
    video_path = video_folder / 'nosilence.mp4'
    audio_path = video_folder / 'audio_temp.mp3'
    json_path = video_folder / 'transcription.json'
    txt_path = video_folder / 'transcription.txt'
    
    # Verifier video
    if not video_path.exists():
        result['error'] = 'nosilence.mp4 manquant'
        return result
    
    # Verifier API key
    if not GROQ_API_KEY:
        result['error'] = 'GROQ_API_KEY manquante dans .env'
        return result
    
    try:
        # Extraire audio
        print(f"[Step4] Extraction audio...")
        if not extract_audio(str(video_path), str(audio_path)):
            result['error'] = 'Erreur extraction audio'
            return result
        
        audio_size = audio_path.stat().st_size / 1024 / 1024
        print(f"[Step4] Audio extrait: {audio_size:.2f} MB")
        
        # Transcrire
        print(f"[Step4] Transcription avec Groq Whisper...")
        groq_result = transcribe_with_groq(str(audio_path), language)
        
        # Extraire resultats
        text = groq_result.get('text', '')
        segments = groq_result.get('segments', [])
        
        print(f"[Step4] Transcription: {len(text)} caracteres, {len(segments)} segments")
        
        # Corriger l'orthographe avec GPT-4o-mini
        print(f"[Step4] Correction orthographique...")
        text, segments = correct_words_with_openrouter(text, segments)
        
        # Sauvegarder JSON complet
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'text': text,
                'segments': segments,
                'language': language,
                'duration': groq_result.get('duration', 0)
            }, f, ensure_ascii=False, indent=2)
        print(f"[Step4] Sauvegarde: {json_path.name}")
        
        # Sauvegarder texte simple
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[Step4] Sauvegarde: {txt_path.name}")
        
        # Nettoyer audio temp
        audio_path.unlink(missing_ok=True)
        
        result['success'] = True
        result['text'] = text
        result['segments'] = segments
        
        print(f"[Step4] OK!")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"[Step4] ERREUR: {e}")
        # Nettoyer
        audio_path.unlink(missing_ok=True)
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = transcribe_video(folder)
    print(f"\nResultat: {result['success']}")
    if result['text']:
        print(f"Texte: {result['text'][:200]}...")

