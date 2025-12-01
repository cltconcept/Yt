"""
Etape 9 : Generation de la miniature YouTube
- Utilise OpenRouter avec Gemini 3 Pro pour generer une miniature virale
- Style: fond dynamique, effets lumineux, texte accrocheur
- Logo VibeAcademy en haut a droite
- VARIETE: couleurs, positions, backgrounds changeants
"""
import subprocess
import json
import os
import base64
import asyncio
import random
from pathlib import Path
from dotenv import load_dotenv

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Charger .env
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

FFMPEG = os.environ.get('FFMPEG_PATH', 'C:/Dev/Yt/ffmpeg/ffmpeg.exe')
FFPROBE = os.environ.get('FFPROBE_PATH', 'C:/Dev/Yt/ffmpeg/ffprobe.exe')
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Chemin du logo
LOGO_PATH = Path(__file__).parent.parent / "assets" / "vibeacademy_logo.png"

# ===== VARIETE DES MINIATURES =====

# Palettes de couleurs (primary_gradient, secondary_color, text_color, accent_color, clothing_color)
COLOR_PALETTES = [
    {
        "name": "Purple Energy",
        "gradient": "PURPLE (#9333ea) to CYAN (#00FFFF)",
        "text": "YELLOW (#FFFF00)",
        "accent": "RED",
        "clothing": "purple/violet hoodie",
        "clothing_hex": "#9333ea"
    },
    {
        "name": "Fire Orange",
        "gradient": "ORANGE (#FF6B00) to RED (#FF0000)",
        "text": "WHITE (#FFFFFF)",
        "accent": "YELLOW",
        "clothing": "dark orange/burnt orange hoodie",
        "clothing_hex": "#CC5500"
    },
    {
        "name": "Electric Blue",
        "gradient": "DARK BLUE (#1E3A8A) to ELECTRIC BLUE (#00D4FF)",
        "text": "YELLOW (#FFFF00)",
        "accent": "WHITE",
        "clothing": "navy blue/royal blue hoodie",
        "clothing_hex": "#1E3A8A"
    },
    {
        "name": "Matrix Green",
        "gradient": "BLACK (#0A0A0A) to NEON GREEN (#00FF00)",
        "text": "NEON GREEN (#00FF00)",
        "accent": "WHITE",
        "clothing": "black hoodie",
        "clothing_hex": "#1A1A1A"
    },
    {
        "name": "Sunset Pink",
        "gradient": "HOT PINK (#FF1493) to ORANGE (#FF8C00)",
        "text": "WHITE (#FFFFFF)",
        "accent": "YELLOW",
        "clothing": "pink/magenta hoodie",
        "clothing_hex": "#C71585"
    },
    {
        "name": "Golden Power",
        "gradient": "BLACK (#0D0D0D) to GOLD (#FFD700)",
        "text": "GOLD (#FFD700)",
        "accent": "WHITE",
        "clothing": "black hoodie with gold accents",
        "clothing_hex": "#1A1A1A"
    },
    {
        "name": "Ocean Teal",
        "gradient": "TEAL (#008080) to TURQUOISE (#40E0D0)",
        "text": "WHITE (#FFFFFF)",
        "accent": "ORANGE",
        "clothing": "teal/dark green hoodie",
        "clothing_hex": "#006666"
    },
    {
        "name": "Red Alert",
        "gradient": "DARK RED (#8B0000) to BRIGHT RED (#FF0000)",
        "text": "WHITE (#FFFFFF)",
        "accent": "YELLOW",
        "clothing": "dark red/burgundy hoodie",
        "clothing_hex": "#8B0000"
    }
]

# Situations/contextes réels pour le personnage
PERSON_SITUATIONS = [
    {
        "name": "Coding Session",
        "context": "sitting at a desk with multiple monitors showing code",
        "environment": "modern tech office/home office with RGB lighting, multiple screens with code visible",
        "pose": "hands on keyboard or pointing at screen, focused but excited expression"
    },
    {
        "name": "Street Entrepreneur",
        "context": "standing in a modern city street",
        "environment": "urban cityscape, modern buildings, busy street atmosphere",
        "pose": "confident stance, walking or standing with energy, phone in hand or gesturing"
    },
    {
        "name": "Coffee Shop Hustle",
        "context": "in a trendy coffee shop with laptop",
        "environment": "cozy cafe interior, warm lighting, laptop and coffee on table",
        "pose": "leaning forward excitedly, pointing at laptop screen or looking at camera"
    },
    {
        "name": "Studio Creator",
        "context": "in a professional content creation studio",
        "environment": "studio setup with ring lights, camera equipment, professional backdrop",
        "pose": "presenting to camera, arms open or pointing, very expressive"
    },
    {
        "name": "Outdoor Success",
        "context": "outdoors in a beautiful location",
        "environment": "rooftop with city skyline, beach, or mountain view in background",
        "pose": "arms raised in victory, celebrating, or pointing at something amazing"
    },
    {
        "name": "Conference Speaker",
        "context": "on stage at a tech conference",
        "environment": "stage with big screen behind, conference lights, audience silhouettes",
        "pose": "presenting with microphone or gesturing to slides, commanding presence"
    },
    {
        "name": "Home Office Pro",
        "context": "in a clean modern home office",
        "environment": "minimalist desk setup, plants, good lighting, organized space",
        "pose": "sitting confidently, pointing at camera or screen, professional but approachable"
    },
    {
        "name": "Night Grind",
        "context": "working late at night with ambient lighting",
        "environment": "dark room lit by monitors, neon accents, late night coding vibe",
        "pose": "intense focus but excited, illuminated by screen glow"
    }
]

# Positions du personnage
PERSON_POSITIONS = [
    {
        "name": "left_dominant",
        "position": "LEFT side, filling 60-70% of image width",
        "text_position": "RIGHT side of the image",
        "body": "from SHOULDERS UP, EXTREMELY LARGE, filling most of the left side"
    },
    {
        "name": "right_dominant",
        "position": "RIGHT side, filling 60-70% of image width",
        "text_position": "LEFT side of the image",
        "body": "from SHOULDERS UP, EXTREMELY LARGE, filling most of the right side"
    },
    {
        "name": "center_lower",
        "position": "CENTER-BOTTOM of the image",
        "text_position": "TOP portion of the image, centered",
        "body": "from CHEST UP, person at bottom looking up at text"
    },
    {
        "name": "left_action",
        "position": "LEFT side, leaning into frame",
        "text_position": "RIGHT side with dramatic angle",
        "body": "dynamic pose, one hand pointing at text, very expressive"
    }
]

# Mises en situation / backgrounds dynamiques
BACKGROUND_STYLES = [
    {
        "name": "Light Explosion",
        "description": "Light rays emanating from center, bokeh effects and particles, lens flare",
        "effects": "explosion/burst effects around text, energy radiating outward"
    },
    {
        "name": "Tech Grid",
        "description": "Futuristic digital grid lines, holographic elements, tech patterns",
        "effects": "glowing circuit patterns, data streams, matrix-like elements"
    },
    {
        "name": "Cosmic Space",
        "description": "Deep space background with stars, nebula clouds, cosmic dust",
        "effects": "galaxy swirls, shooting stars, planetary rings in background"
    },
    {
        "name": "Fire & Smoke",
        "description": "Dramatic flames and smoke effects, ember particles",
        "effects": "fire bursting from behind text, smoke wisps, heat distortion"
    },
    {
        "name": "Lightning Storm",
        "description": "Dark stormy atmosphere with lightning bolts",
        "effects": "multiple lightning strikes, electrical arcs, storm clouds"
    },
    {
        "name": "Neon City",
        "description": "Cyberpunk neon lights, urban backdrop, glowing signs",
        "effects": "neon reflections, rain effects, futuristic city silhouette"
    },
    {
        "name": "Clean Gradient",
        "description": "Smooth professional gradient, subtle geometric shapes",
        "effects": "floating 3D shapes, smooth color transitions, minimalist style"
    },
    {
        "name": "Action Burst",
        "description": "Comic book style action lines, dynamic motion blur",
        "effects": "speed lines radiating from center, impact effects, manga style energy"
    }
]


def get_video_duration(video_path: str) -> float:
    """Obtient la duree de la video"""
    result = subprocess.run([
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0', video_path
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 30.0


def extract_best_frame(video_path: str, output_path: str) -> bool:
    """Extrait la meilleure frame (au milieu de la video)"""
    duration = get_video_duration(video_path)
    timestamp = duration / 2
    
    cmd = [
        FFMPEG, '-y',
        '-ss', str(timestamp),
        '-i', video_path,
        '-frames:v', '1',
        '-q:v', '2',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0 and Path(output_path).exists()


def generate_catchy_title(original_title: str) -> str:
    """
    Utilise l'IA pour créer un titre court et accrocheur pour la miniature.
    Le titre doit être une phrase COMPLETE qui a du sens, pas une phrase coupée.
    """
    if not OPENAI_AVAILABLE or not OPENROUTER_API_KEY:
        # Fallback: prendre les 3-4 premiers mots importants
        words = original_title.replace('🚀', '').replace('!', '').strip().split()
        return ' '.join(words[:4]).upper()
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Tu crées des titres de miniatures YouTube VIRALES.

TITRE ORIGINAL: "{original_title}"

RÈGLES STRICTES:
1. Maximum 4-6 MOTS seulement
2. La phrase doit être COMPLÈTE et GRAMMATICALEMENT CORRECTE
3. INCLURE TOUS LES ARTICLES (le, la, l', les, un, une) - NE JAMAIS LES OMETTRE
4. ZÉRO FAUTE D'ORTHOGRAPHE - vérifie chaque mot
5. JAMAIS couper une phrase au milieu
6. Utilise des mots PUISSANTS et ACCROCHEURS
7. Pas d'emoji
8. EN FRANÇAIS CORRECT

EXEMPLES:
- "Comment utiliser Cursor pour coder plus vite" → "CODEZ 10X PLUS VITE"
- "Découvrez les secrets de ChatGPT" → "LES SECRETS DE CHATGPT"
- "L'application qui révolutionne l'entrepreneuriat" → "L'APP QUI RÉVOLUTIONNE L'ENTREPRENEURIAT"
- "Comment gagner de l'argent avec YouTube" → "GAGNEZ AVEC YOUTUBE"
- "Les meilleures techniques de productivité" → "LA PRODUCTIVITÉ ULTIME"

IMPORTANT: Vérifie que ta réponse est grammaticalement correcte avec tous les articles nécessaires.

Réponds UNIQUEMENT avec le nouveau titre (sans guillemets)."""
            }],
            max_tokens=50,
            temperature=0.5
        )
        
        catchy_title = response.choices[0].message.content.strip().upper()
        # Nettoyer les guillemets s'il y en a
        catchy_title = catchy_title.strip('"\'')
        print(f"[Step9] Titre accrocheur généré: {catchy_title}")
        return catchy_title
    except Exception as e:
        print(f"[Step9] Erreur génération titre: {e}")
        # Fallback
        words = original_title.replace('🚀', '').replace('!', '').strip().split()
        return ' '.join(words[:4]).upper()


def generate_subject_keywords(title: str) -> str:
    """
    Utilise l'IA pour générer les mots-clés du background selon le titre de la vidéo
    """
    if not OPENAI_AVAILABLE or not OPENROUTER_API_KEY:
        return "technology, abstract digital"
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Analyse ce titre de vidéo YouTube et génère les mots-clés visuels pour le BACKGROUND d'une miniature.

Titre: "{title}"

CONNAISSANCE DES OUTILS:
- Cursor = code editor / IDE (comme VS Code) → background: "dark code editor, syntax highlighting, programming IDE"
- ChatGPT / GPT = AI chatbot → background: "AI chat interface, neural network, futuristic"
- n8n / Make / Zapier = automation → background: "workflow nodes, connected automation, flowchart"
- YouTube = video platform → background: "play buttons, video grid, creator dashboard"
- Python / JavaScript = programming → background: "code syntax, programming language, developer"
- Notion = productivity app → background: "organized notes, workspace dashboard"

RÈGLES:
1. Ignore les métaphores (Ferrari = vitesse, pas une voiture)
2. Identifie le VRAI outil/technologie mentionné
3. Génère 3 mots-clés EN ANGLAIS pour des éléments visuels de BACKGROUND

Réponds UNIQUEMENT avec les mots-clés, format: "keyword1, keyword2, keyword3" """
            }],
            max_tokens=40,
            temperature=0.3
        )
        
        keywords = response.choices[0].message.content.strip()
        print(f"[Step9] Subject keywords générés: {keywords}")
        return keywords
    except Exception as e:
        print(f"[Step9] Erreur génération keywords: {e}")
        return "technology, abstract digital"


def generate_thumbnail_prompt(title: str, subject_keywords: str, transcript: str = "", style_override: dict = None) -> tuple:
    """
    Generer un prompt optimise pour creer une miniature YouTube virale.
    Utilise des variations aléatoires de couleurs, positions et backgrounds.
    
    Args:
        title: Titre original de la vidéo
        subject_keywords: Mots-clés pour les éléments de background
        transcript: Transcription (optionnel)
        style_override: Dict pour forcer un style spécifique (optionnel)
    """
    # Générer un titre court et accrocheur avec l'IA
    short_title = generate_catchy_title(title)
    
    # Sélectionner aléatoirement une palette de couleurs
    if style_override and 'color_palette' in style_override:
        color_palette = style_override['color_palette']
    else:
        color_palette = random.choice(COLOR_PALETTES)
    
    # Sélectionner aléatoirement une position
    if style_override and 'position' in style_override:
        position = style_override['position']
    else:
        position = random.choice(PERSON_POSITIONS)
    
    # Sélectionner aléatoirement un style de background
    if style_override and 'background' in style_override:
        background = style_override['background']
    else:
        background = random.choice(BACKGROUND_STYLES)
    
    # Sélectionner aléatoirement une situation/contexte
    if style_override and 'situation' in style_override:
        situation = style_override['situation']
    else:
        situation = random.choice(PERSON_SITUATIONS)
    
    print(f"[Step9] Style sélectionné:")
    print(f"  - Couleurs: {color_palette['name']}")
    print(f"  - Position: {position['name']}")
    print(f"  - Background: {background['name']}")
    print(f"  - Situation: {situation['name']}")
    
    prompt = f"""Create a VIRAL YouTube thumbnail image (1280x720 pixels, 16:9 ratio).

MAIN TITLE TEXT TO DISPLAY: "{short_title}"

REQUIREMENTS:

1. THE PERSON IN ACTION (CRITICAL - REAL SITUATION):
   - SITUATION: {situation['context']}
   - ENVIRONMENT: {situation['environment']}
   - POSE: {situation['pose']}
   - Dress the person in a {color_palette['clothing']}
   - The clothing color should be {color_palette['clothing_hex']}
   - NO headphones, no accessories unless relevant to the situation
   - Natural excited/surprised expression matching the context
   - Position: {position['position']}
   - Body: {position['body']}
   - The person is the MAIN ATTRACTION - make them HUGE and PROMINENT

2. TEXT STYLE:
   - The title "{short_title}" must be EXTREMELY LARGE (50-60% of image height)
   - BOLD, UPPERCASE letters
   - Color: {color_palette['text']} with THICK BLACK outline (8-10px)
   - Position: {position['text_position']}
   - Add drop shadow for depth
   - Text should be on 2-3 lines if needed for impact

3. BACKGROUND/ENVIRONMENT - "{situation['name']}":
   - REAL ENVIRONMENT: {situation['environment']}
   - Color scheme: {color_palette['gradient']}
   - Visual style: {background['description']}
   - Effects overlay: {background['effects']}
   - Include elements related to: {subject_keywords}
   - The environment should feel REAL and AUTHENTIC
   - Person must be clearly visible and prominent against the background

4. SHOCK ELEMENTS:
   - 2-3 large {color_palette['accent']} arrows pointing at important elements
   - Dynamic effects matching the "{background['name']}" style
   - High energy visual impact

5. COLOR HARMONY:
   - Person's clothing: {color_palette['clothing']}
   - Background: {color_palette['gradient']}
   - Text: {color_palette['text']}
   - Accents: {color_palette['accent']}
   - Everything should be color-coordinated in the "{color_palette['name']}" theme

6. STYLE:
   - Ultra high quality, sharp, photorealistic person
   - Maximum saturation and contrast
   - Professional YouTube thumbnail style
   - Every element screams "CLICK ME!"

Generate this thumbnail image NOW."""

    # Retourner le prompt ET les infos de vêtements pour generate_thumbnail_with_gemini
    return prompt, {"clothing": color_palette['clothing'], "clothing_hex": color_palette['clothing_hex']}


def generate_thumbnail_with_gemini(prompt: str, webcam_base64: str, logo_base64: str, output_path: str, clothing_info: dict = None) -> bool:
    """
    Generer une miniature avec Gemini 3 Pro via OpenRouter
    Inclut la frame webcam pour regenerer le personnage
    
    clothing_info: dict avec 'clothing' et 'clothing_hex' pour les vêtements
    """
    # Vêtements par défaut si non spécifié
    if clothing_info is None:
        clothing_info = {"clothing": "stylish hoodie", "clothing_hex": "#6B21A8"}
    if not OPENAI_AVAILABLE:
        print("[Step9] OpenAI SDK non disponible. Installez: pip install openai")
        return False
    
    if not OPENROUTER_API_KEY:
        print("[Step9] OPENROUTER_API_KEY manquante")
        return False
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )
    
    # Construire le message avec l'image de reference
    if webcam_base64:
        # Prompt avec image de reference pour le personnage
        logo_instruction = ""
        if logo_base64:
            logo_instruction = """

LOGO (SECOND IMAGE PROVIDED):
- I am providing the VibeAcademy logo (purple V with arrow)
- Place ONLY on the hoodie chest area - NOWHERE ELSE in the image
- Make it look like a NATURAL screen-printed logo on fabric
- The logo should subtly follow the fabric folds and lighting
- Keep the logo design recognizable but integrated naturally
- Size: Medium, on the chest
- DO NOT put the logo anywhere else - ONLY on the clothing"""

        full_prompt = f"""{prompt}

CRITICAL - PERSON REFERENCE (VERY IMPORTANT):
I am providing a reference image of a person. You MUST follow these rules EXACTLY:

FACE - ABSOLUTELY DO NOT CHANGE (CRITICAL):
- The person's face must be 100% IDENTICAL to the reference photo
- COPY THE EXACT FACIAL FEATURES: same eyes, same nose, same mouth, same beard, same face shape, same skin tone
- DO NOT modify, stylize, beautify, or alter ANY facial feature
- DO NOT change the face proportions or structure
- DO NOT add or remove facial hair
- DO NOT change eye color, skin color, or any physical trait
- PHOTOREALISTIC rendering - must look like a REAL PHOTOGRAPH of THIS EXACT person
- The person must be IMMEDIATELY RECOGNIZABLE as the same person from the reference
- If you cannot preserve the exact likeness, the image is FAILED

SIZE AND POSITION:
- Person must be MASSIVE - taking 60-80% of the image width
- Person should COMPLETELY DOMINATE the thumbnail - MAXIMUM SIZE POSSIBLE
- Follow the position and situation described in the main prompt above

DYNAMIC ACTION POSE:
- Follow the POSE described in the main prompt (situation-specific)
- Person should look NATURAL in the described environment
- Body language should match the context (coding, presenting, walking, etc.)
- NOT static - show MOVEMENT and ENERGY appropriate to the situation

CLOTHING AND ACCESSORIES (CRITICAL - MUST CHANGE):
- COMPLETELY IGNORE the clothing in the reference photo
- REMOVE microphone, headphones, any accessories from the reference
- DRESS THE PERSON IN: {clothing_info['clothing']}
- The clothing color MUST BE: {clothing_info['clothing_hex']}
- This is a MANDATORY clothing change - DO NOT keep the original clothing
- Hoodie/clothing should have realistic fabric folds and wrinkles
- Show the clothing in motion (fabric moving with the gesture)
{logo_instruction}

EXPRESSION:
- Natural excited/surprised expression
- Looking towards the camera or slightly towards the text

ABSOLUTELY FORBIDDEN - DO NOT:
- Do NOT change ANY facial features (eyes, nose, mouth, beard, face shape)
- Do NOT modify skin tone or complexion
- Do NOT make the face look younger, older, thinner, or different in ANY way
- Do NOT stylize, cartoonify, or beautify the face
- Do NOT shrink the person
- Do NOT add filters that alter facial appearance
- The face must be a PERFECT COPY of the reference

Generate a thumbnail where the person is LARGE, PROMINENT, and looks EXACTLY like the reference photo. THE FACE MUST BE IDENTICAL."""

        # Construire le contenu du message
        content = [
            {"type": "text", "text": full_prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{webcam_base64}"
                }
            }
        ]
        
        # Ajouter le logo si disponible
        if logo_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{logo_base64}"
                }
            })
        
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
    
    try:
        print("[Step9] Generation avec Gemini 3 Pro (avec personnage)...")
        
        response = client.chat.completions.create(
            model="google/gemini-3-pro-image-preview",
            messages=messages,
            extra_body={"modalities": ["image", "text"]}
        )
        
        # Recuperer l'image depuis la reponse
        message = response.choices[0].message
        
        # Verifier si images existe
        if hasattr(message, 'images') and message.images:
            for image in message.images:
                image_url = image.get('image_url', {}).get('url', '')
                if image_url.startswith('data:image'):
                    # Extraire le base64
                    image_data = image_url.split('base64,')[1]
                    image_bytes = base64.b64decode(image_data)
                    
                    with open(output_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    print(f"[Step9] Image generee: {output_path}")
                    return True
        
        # Fallback: chercher dans content si c'est une liste
        content = message.content
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'image_url':
                        image_url = item.get('image_url', {}).get('url', '')
                        if image_url.startswith('data:image'):
                            image_data = image_url.split('base64,')[1]
                            image_bytes = base64.b64decode(image_data)
                            with open(output_path, 'wb') as f:
                                f.write(image_bytes)
                            print(f"[Step9] Image generee: {output_path}")
                            return True
        
        # Debug: afficher la structure de la reponse
        print(f"[Step9] Structure reponse: {type(message)}")
        if hasattr(message, 'content'):
            print(f"[Step9] Content: {str(message.content)[:500]}")
        
        # Sauvegarder la reponse complete pour debug
        debug_path = Path(output_path).parent / "gemini_debug.json"
        try:
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(response.model_dump(), f, indent=2, default=str)
            print(f"[Step9] Debug sauvegarde: {debug_path}")
        except:
            pass
        
        print("[Step9] Pas d'image dans la reponse Gemini")
        return False
        
    except Exception as e:
        import traceback
        print(f"[Step9] Erreur Gemini: {e}")
        traceback.print_exc()
        return False


def add_face_overlay(background_path: str, webcam_path: str, output_path: str) -> bool:
    """
    Ajouter le visage de la webcam sur le fond genere
    """
    temp_face = Path(background_path).parent / "temp_face_overlay.png"
    
    # Extraire une frame de la webcam
    if not extract_best_frame(webcam_path, str(temp_face)):
        print("[Step9] Pas de webcam, utilisation du fond seul")
        Path(background_path).rename(output_path)
        return True
    
    # Overlay le visage a gauche
    cmd = [
        FFMPEG, '-y',
        '-i', background_path,
        '-i', str(temp_face),
        '-filter_complex',
        '[1:v]scale=-1:650[face];[0:v][face]overlay=-50:70',
        '-frames:v', '1',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    temp_face.unlink(missing_ok=True)
    
    return result.returncode == 0


def add_logo(input_path: str, output_path: str) -> bool:
    """
    Ajouter le logo VibeAcademy en haut a droite (haute qualite)
    """
    if not LOGO_PATH.exists():
        print("[Step9] Logo non trouve, skip")
        import shutil
        shutil.copy(input_path, output_path)
        return True
    
    # Logo plus grand (150px) avec haute qualite (lanczos)
    cmd = [
        FFMPEG, '-y',
        '-i', input_path,
        '-i', str(LOGO_PATH),
        '-filter_complex',
        '[1:v]scale=150:-1:flags=lanczos[logo];[0:v][logo]overlay=W-w-25:25',
        '-q:v', '1',
        '-frames:v', '1',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def generate_thumbnail(video_folder: str, custom_title: str = None) -> dict:
    """
    Genere la miniature YouTube avec OpenRouter Gemini 3 Pro
    Envoie la frame webcam pour regenerer le personnage dans l'image
    
    Args:
        video_folder: Dossier video
        custom_title: Titre personnalise (sinon utilise seo.json)
    
    Returns:
        dict avec success, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'output_path': None
    }
    
    # Fichiers
    webcam_path = video_folder / "webcam.mp4"
    output_path = video_folder / "thumbnail.png"
    temp_frame = video_folder / "temp_webcam_frame.png"
    temp_generated = video_folder / "temp_thumbnail_generated.png"
    
    # Obtenir le titre
    if custom_title:
        title = custom_title
    else:
        seo_path = video_folder / "seo.json"
        if seo_path.exists():
            with open(seo_path, 'r', encoding='utf-8') as f:
                seo_data = json.load(f)
            title = seo_data.get('main_video', {}).get('title', 'Nouvelle Video')
        else:
            title = "Nouvelle Video"
    
    # Obtenir la transcription
    transcript = ""
    trans_path = video_folder / "transcription.txt"
    if trans_path.exists():
        transcript = trans_path.read_text(encoding='utf-8')
    
    print(f"[Step9] Titre: {title}")
    
    # 1. Extraire une frame de la webcam
    webcam_base64 = ""
    if webcam_path.exists():
        print("[Step9] Extraction frame webcam...")
        if extract_best_frame(str(webcam_path), str(temp_frame)):
            with open(temp_frame, 'rb') as f:
                webcam_base64 = base64.b64encode(f.read()).decode('utf-8')
            print(f"[Step9] Frame webcam encodee ({len(webcam_base64)} chars)")
            temp_frame.unlink(missing_ok=True)
    
    # 2. Encoder le logo
    logo_base64 = ""
    if LOGO_PATH.exists():
        print("[Step9] Encodage logo...")
        with open(LOGO_PATH, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
        print(f"[Step9] Logo encode ({len(logo_base64)} chars)")
    
    # 3. Generer les mots-clés du background avec l'IA
    print("[Step9] Génération des mots-clés du background...")
    subject_keywords = generate_subject_keywords(title)
    
    # 4. Generer le prompt et les infos de vêtements
    prompt, clothing_info = generate_thumbnail_prompt(title, subject_keywords, transcript)
    print(f"[Step9] Vêtements sélectionnés: {clothing_info['clothing']}")
    
    # 5. Generer la miniature complete avec Gemini (personnage + logo inclus)
    if not generate_thumbnail_with_gemini(prompt, webcam_base64, logo_base64, str(output_path), clothing_info):
        result['error'] = 'Echec generation Gemini'
        return result
    
    # Nettoyer
    temp_generated.unlink(missing_ok=True)
    
    size_kb = output_path.stat().st_size / 1024
    print(f"[Step9] OK: thumbnail.png ({size_kb:.1f} KB)")
    result['success'] = True
    result['output_path'] = str(output_path)
    
    return result


def regenerate_thumbnail_with_corrections(video_folder: str, corrections: str) -> dict:
    """
    Régénère la miniature YouTube en appliquant des corrections utilisateur.
    Le visage de la webcam est conservé.
    
    Args:
        video_folder: Dossier vidéo
        corrections: Instructions de correction (ex: "Plus de contraste, texte plus gros...")
    
    Returns:
        dict avec success, output_path, error
    """
    video_folder = Path(video_folder)
    
    result = {
        'success': False,
        'error': None,
        'output_path': None
    }
    
    # Fichiers
    webcam_path = video_folder / "webcam.mp4"
    output_path = video_folder / "thumbnail.png"
    temp_frame = video_folder / "temp_webcam_frame.png"
    
    # Obtenir le titre depuis seo.json
    seo_path = video_folder / "seo.json"
    if seo_path.exists():
        with open(seo_path, 'r', encoding='utf-8') as f:
            seo_data = json.load(f)
        title = seo_data.get('main_video', {}).get('title', 'Nouvelle Video')
    else:
        title = "Nouvelle Video"
    
    print(f"[Step9] Régénération avec corrections...")
    print(f"[Step9] Titre: {title}")
    print(f"[Step9] Corrections: {corrections}")
    
    # 1. Extraire une frame de la webcam
    webcam_base64 = ""
    if webcam_path.exists():
        print("[Step9] Extraction frame webcam...")
        if extract_best_frame(str(webcam_path), str(temp_frame)):
            with open(temp_frame, 'rb') as f:
                webcam_base64 = base64.b64encode(f.read()).decode('utf-8')
            print(f"[Step9] Frame webcam encodée ({len(webcam_base64)} chars)")
            temp_frame.unlink(missing_ok=True)
    
    # 2. Encoder le logo
    logo_base64 = ""
    if LOGO_PATH.exists():
        with open(LOGO_PATH, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # 3. Générer les mots-clés du background
    subject_keywords = generate_subject_keywords(title)
    
    # 4. Générer le prompt de BASE et les infos de vêtements
    base_prompt, clothing_info = generate_thumbnail_prompt(title, subject_keywords, "")
    
    # 5. Ajouter les corrections utilisateur au prompt
    corrected_prompt = f"""{base_prompt}

CORRECTIONS UTILISATEUR (PRIORITAIRES):
Les modifications suivantes doivent être appliquées EN PLUS des instructions ci-dessus:
{corrections}

RAPPEL CRITIQUE:
- Le VISAGE doit rester 100% IDENTIQUE à l'image de référence fournie
- Seuls le style, les couleurs, le texte et les éléments graphiques peuvent changer
- La personne doit être immédiatement reconnaissable"""
    
    # 6. Générer la nouvelle miniature
    if not generate_thumbnail_with_gemini(corrected_prompt, webcam_base64, logo_base64, str(output_path), clothing_info):
        result['error'] = 'Échec génération Gemini'
        return result
    
    size_kb = output_path.stat().st_size / 1024
    print(f"[Step9] OK: thumbnail.png régénéré ({size_kb:.1f} KB)")
    result['success'] = True
    result['output_path'] = str(output_path)
    
    return result


# Pour test direct
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Dossier video: ")
    
    result = generate_thumbnail(folder)
    print(f"\nResultat: {result}")
