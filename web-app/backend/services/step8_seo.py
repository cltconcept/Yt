"""
Etape 8 : Generation SEO pour la video illustree et les shorts
- Titre accrocheur
- Description optimisee YouTube
- Tags/mots-cles
- Hashtags pour shorts
"""
import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Signature pour les descriptions
SIGNATURE = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Rejoins-moi sur https://vibeacademy.eu
💬 Communauté: https://skool.com/vibeacademy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

# Signature courte pour shorts
SIGNATURE_SHORT = "\n\n🚀 https://vibeacademy.eu | 💬 https://skool.com/vibeacademy"


def call_openrouter(prompt: str, max_tokens: int = 1500) -> str:
    """Appel GPT-4o-mini via OpenRouter"""
    if not OPENROUTER_API_KEY:
        raise Exception("OPENROUTER_API_KEY manquante dans .env")
    
    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens
        },
        timeout=60
    )
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        raise Exception(f"OpenRouter error: {response.status_code} - {response.text}")


def generate_main_video_seo(transcription: str, video_duration: float) -> dict:
    """
    Genere le SEO pour la video principale
    
    Returns:
        dict avec title, description, tags, category, pinned_comment
    """
    prompt = f"""Tu es un expert SEO YouTube. Genere le SEO optimal pour une video YouTube.

TRANSCRIPTION DE LA VIDEO:
{transcription[:3000]}

DUREE: {video_duration:.0f} secondes

GENERE UN JSON VALIDE avec exactement cette structure:
{{
    "title": "Titre accrocheur de 50-70 caracteres max, avec emoji au debut",
    "description": "Description complete de 200-400 mots avec:\\n- Resume du contenu\\n- Points cles\\n- Chapitres/timestamps si pertinent\\n- Call to action (like/subscribe)\\nOptimisee pour le SEO YouTube. NE PAS inclure de liens, ils seront ajoutes automatiquement.",
    "tags": ["tag1", "tag2", "tag3", "..."],
    "category": "Education ou Science & Technology ou Howto & Style",
    "pinned_comment": "Commentaire engageant a epingler, avec question pour encourager les reponses et emoji"
}}

REGLES:
- Titre: accrocheur, avec emoji, max 70 caracteres
- Description: informative, avec emojis, mots-cles naturels, CTA (like/subscribe)
- Tags: 15-25 tags pertinents, melangeant populaires et specifiques
- Commentaire epingle: question engageante pour creer de l'interaction
- Tout en francais

Reponds UNIQUEMENT avec le JSON, rien d'autre."""

    try:
        result = call_openrouter(prompt)
        
        # Nettoyer la reponse (enlever ```json si present)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        seo_data = json.loads(result)
        
        # Ajouter la signature a la description
        seo_data['description'] = seo_data.get('description', '') + SIGNATURE
        
        return seo_data
        
    except json.JSONDecodeError as e:
        print(f"[Step8] Erreur parsing JSON: {e}")
        return {
            "title": "Video sans titre",
            "description": "Description a completer" + SIGNATURE,
            "tags": [],
            "category": "Education",
            "pinned_comment": "Qu'en pensez-vous ? 🤔"
        }


def generate_short_seo(transcription: str, short_index: int, short_start: float, short_end: float) -> dict:
    """
    Genere le SEO pour un short specifique
    
    Returns:
        dict avec title, description, hashtags, pinned_comment
    """
    duration = short_end - short_start
    
    prompt = f"""Tu es un expert YouTube Shorts. Genere le SEO optimal pour ce Short.

EXTRAIT DE LA TRANSCRIPTION (segment du short):
{transcription[:1500]}

DUREE DU SHORT: {duration:.0f} secondes
NUMERO: Short #{short_index + 1}

GENERE UN JSON VALIDE avec exactement cette structure:
{{
    "title": "Titre court et accrocheur, max 40 caracteres, avec emoji",
    "description": "Description courte 1-2 phrases avec CTA. NE PAS inclure de liens.",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#shorts", "#youtube"],
    "pinned_comment": "Commentaire court et engageant avec question et emoji"
}}

REGLES:
- Titre: tres court, percutant, emoji au debut
- Description: courte, avec emojis, CTA simple
- Hashtags: 5-8 hashtags, TOUJOURS inclure #shorts
- Commentaire epingle: question courte pour engagement
- Tout en francais

Reponds UNIQUEMENT avec le JSON, rien d'autre."""

    try:
        result = call_openrouter(prompt, max_tokens=500)
        
        # Nettoyer
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        seo_data = json.loads(result)
        
        # S'assurer que #shorts est present dans les hashtags
        if "#shorts" not in seo_data.get("hashtags", []):
            seo_data["hashtags"].append("#shorts")
        
        # S'assurer que #shorts est dans le titre
        title = seo_data.get("title", "")
        if "#shorts" not in title.lower():
            seo_data["title"] = f"{title} #shorts"
        
        # Ajouter la signature courte a la description
        seo_data['description'] = seo_data.get('description', '') + SIGNATURE_SHORT
        
        return seo_data
        
    except json.JSONDecodeError as e:
        print(f"[Step8] Erreur parsing JSON short: {e}")
        return {
            "title": f"Short #{short_index + 1} #shorts",
            "description": "A voir!" + SIGNATURE_SHORT,
            "hashtags": ["#shorts", "#youtube", "#viral"],
            "pinned_comment": "Tu en penses quoi ? 🤔"
        }


def generate_seo(video_folder: str) -> dict:
    """
    Genere le SEO complet pour la video et les shorts
    
    Args:
        video_folder: Chemin du dossier video
    
    Returns:
        dict avec main_video et shorts
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'main_video': None,
        'shorts': []
    }
    
    # Verifier transcription
    transcription_path = video_folder / 'transcription.json'
    if not transcription_path.exists():
        transcription_txt = video_folder / 'transcription.txt'
        if transcription_txt.exists():
            transcription = transcription_txt.read_text(encoding='utf-8')
            segments = []
            duration = 30.0  # Defaut
        else:
            result['error'] = 'transcription.json ou .txt manquant'
            return result
    else:
        with open(transcription_path, 'r', encoding='utf-8') as f:
            trans_data = json.load(f)
        transcription = trans_data.get('text', '')
        segments = trans_data.get('segments', [])
        duration = trans_data.get('duration', 30.0)
    
    if not transcription:
        result['error'] = 'Transcription vide'
        return result
    
    print(f"[Step8] Transcription: {len(transcription)} caracteres")
    
    # Verifier API key
    if not OPENROUTER_API_KEY:
        result['error'] = 'OPENROUTER_API_KEY manquante dans .env'
        return result
    
    try:
        # 1. SEO video principale
        print(f"[Step8] Generation SEO video principale...")
        main_seo = generate_main_video_seo(transcription, duration)
        result['main_video'] = main_seo
        print(f"[Step8] Titre: {main_seo.get('title', 'N/A')}")
        print(f"[Step8] Tags: {len(main_seo.get('tags', []))} tags")
        
        # 2. SEO shorts (chercher les fichiers short_*.mp4)
        shorts_folder = video_folder / 'shorts'
        if shorts_folder.exists():
            short_files = sorted(shorts_folder.glob('short_*.mp4'))
            
            # Chercher les metadonnees des shorts
            shorts_meta_path = video_folder / 'shorts_meta.json'
            shorts_meta = {}
            if shorts_meta_path.exists():
                with open(shorts_meta_path, 'r', encoding='utf-8') as f:
                    shorts_meta = json.load(f)
            
            for i, short_file in enumerate(short_files):
                print(f"[Step8] Generation SEO short #{i+1}...")
                
                # Trouver les timestamps du short
                short_key = short_file.stem  # ex: "short_0"
                meta = shorts_meta.get(short_key, {})
                start = meta.get('start', i * 30)
                end = meta.get('end', start + 30)
                
                # Extraire la partie de transcription correspondante
                short_transcript = ""
                for seg in segments:
                    seg_start = seg.get('start', 0)
                    seg_end = seg.get('end', 0)
                    if seg_start >= start and seg_end <= end + 5:  # +5s de marge
                        short_transcript += " " + seg.get('text', '')
                
                if not short_transcript:
                    short_transcript = transcription[:500]
                
                short_seo = generate_short_seo(short_transcript.strip(), i, start, end)
                short_seo['file'] = short_file.name
                short_seo['start'] = start
                short_seo['end'] = end
                result['shorts'].append(short_seo)
                print(f"[Step8] Short #{i+1}: {short_seo.get('title', 'N/A')}")
        
        # Sauvegarder
        seo_path = video_folder / 'seo.json'
        with open(seo_path, 'w', encoding='utf-8') as f:
            json.dump({
                'main_video': result['main_video'],
                'shorts': result['shorts']
            }, f, ensure_ascii=False, indent=2)
        print(f"[Step8] Sauvegarde: {seo_path.name}")
        
        result['success'] = True
        print(f"[Step8] OK! Video + {len(result['shorts'])} shorts")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"[Step8] ERREUR: {e}")
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = generate_seo(folder)
    print(f"\nResultat: {result['success']}")
    if result['main_video']:
        print(f"\n=== VIDEO PRINCIPALE ===")
        print(f"Titre: {result['main_video'].get('title')}")
        print(f"Description: {result['main_video'].get('description', '')[:200]}...")
        print(f"Tags: {', '.join(result['main_video'].get('tags', [])[:10])}...")
    
    if result['shorts']:
        print(f"\n=== SHORTS ({len(result['shorts'])}) ===")
        for short in result['shorts']:
            print(f"- {short.get('title')} | {' '.join(short.get('hashtags', []))}")

