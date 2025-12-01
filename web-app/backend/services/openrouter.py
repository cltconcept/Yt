"""
Service OpenRouter pour génération SEO YouTube et suggestions de shorts
"""
import os
import json
from typing import Optional, Dict, List
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env depuis la racine du projet
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Essayer le .env local

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenRouterService:
    """Service IA via OpenRouter pour génération SEO YouTube"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "openai/gpt-4o-mini"
        self._client: Optional[OpenAI] = None
    
    def _get_client(self) -> Optional[OpenAI]:
        """Obtenir le client OpenAI configuré pour OpenRouter"""
        if not OPENAI_AVAILABLE:
            print("[OpenRouter] OpenAI SDK non disponible")
            return None
        
        if not self.api_key:
            print("[OpenRouter] Clé API non configurée")
            return None
        
        if not self._client:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "YouTube Pipeline"
                }
            )
        return self._client
    
    async def generate_youtube_seo(
        self,
        transcript: str,
        language: str = "fr",
        segments: Optional[list] = None
    ) -> Optional[Dict]:
        """
        Générer les métadonnées SEO YouTube optimisées
        
        Args:
            transcript: Transcription complète de la vidéo
            language: Langue cible (fr, en, etc.)
            segments: Liste des segments avec timestamps réels [{"start": float, "end": float, "text": str}]
            
        Returns:
            Dict avec summary, title, description, hashtags, chapters ou None si erreur
        """
        client = self._get_client()
        if not client:
            if not OPENAI_AVAILABLE:
                print("[OpenRouter] ERREUR: OpenAI SDK non disponible. Installez avec: pip install openai")
            elif not self.api_key:
                print("[OpenRouter] ERREUR: Clé API OpenRouter non configurée. Ajoutez OPENROUTER_API_KEY dans .env")
            return None
        
        # Tronquer la transcription si trop longue (limite de tokens)
        max_chars = 8000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."
        
        # Préparer les segments pour le chapitrage si disponibles
        chapters_info = ""
        if segments and len(segments) > 0:
            # Formater les segments pour le prompt
            segments_text = "\n".join([
                f"{self._format_timestamp(seg['start'])} - {self._format_timestamp(seg['end'])}: {seg['text'][:100]}"
                for seg in segments[:20]  # Limiter à 20 segments pour ne pas surcharger
            ])
            chapters_info = f"""

Segments avec timestamps réels (pour chapitrage):
{segments_text}

IMPORTANT: Utilise EXACTEMENT ces timestamps pour générer les chapitres. Ne modifie pas les timestamps."""
        
        prompt = f"""Tu es un expert SEO YouTube. Analyse cette transcription et génère des métadonnées optimisées pour YouTube en {language}.

Transcription:
{transcript}
{chapters_info}

Génère:
1. Un TITRE accrocheur (max 70 caractères) optimisé SEO avec:
   - Des mots-clés pertinents basés sur le contenu réel
   - Des chiffres ou questions si pertinent
   - Un format accrocheur pour maximiser les clics

2. Une DESCRIPTION optimisée SEO (200-300 mots) avec:
   - Un résumé engageant dans les premières lignes basé sur le contenu réel
   - Les points clés avec emojis appropriés
   - Un call-to-action pour s'abonner
   {"- Si des segments sont fournis, ajoute une section CHAPITRES avec les timestamps EXACTS au format:" if segments else ""}
   {"  CHAPITRES:" if segments else ""}
   {"  00:00:00 - Titre du chapitre 1" if segments else ""}
   {"  00:01:00 - Titre du chapitre 2" if segments else ""}
   {"  (utilise EXACTEMENT les timestamps fournis dans les segments)" if segments else ""}
   - À la fin, ajoute une ligne "Mots-clés:" suivie de 10-15 mots-clés séparés par des virgules (format YouTube, sans #)

3. 10-15 HASHTAGS pertinents séparés par des virgules, optimisés pour la découverte YouTube (format avec #). IMPORTANT: Les hashtags sont OBLIGATOIRES, génère-en toujours entre 10 et 15.

Réponds UNIQUEMENT dans ce format exact (sans texte supplémentaire):
TITRE:
[ton titre accrocheur]

DESCRIPTION:
[ta description complète avec résumé, points clés, call-to-action]
{"CHAPITRES:" if segments else ""}
{"00:00:00 - Titre du chapitre 1" if segments else ""}
{"[autres chapitres avec timestamps EXACTS]" if segments else ""}
Mots-clés:
mot1, mot2, mot3, mot4, mot5, mot6, mot7, mot8, mot9, mot10, mot11, mot12, mot13, mot14, mot15

HASHTAGS:
#tag1, #tag2, #tag3, #tag4, #tag5, #tag6, #tag7, #tag8, #tag9, #tag10, #tag11, #tag12, #tag13, #tag14, #tag15

ATTENTION: La section HASHTAGS est OBLIGATOIRE. Génère toujours entre 10 et 15 hashtags pertinents basés sur le contenu."""

        try:
            print("[OpenRouter] Génération métadonnées SEO...")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert SEO YouTube qui génère des métadonnées optimisées basées uniquement sur le contenu réel fourni. Ne génère jamais de timestamps ou d'informations non présentes dans la transcription."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parser la réponse
            result = {
                "title": "",
                "description": "",
                "keywords": [],
                "hashtags": [],
                "chapters": []
            }
            
            # Initialiser description_lines avant de l'utiliser
            description_lines = []
            chapters_from_segments = []
            
            # Générer les chapitres à partir des segments réels si disponibles
            # Les chapitres utilisent les timestamps EXACTS des segments
            if segments and len(segments) > 0:
                chapters = []
                # Grouper les segments en chapitres logiques (tous les 30-60 secondes)
                # Mais utiliser les timestamps EXACTS du premier segment de chaque groupe
                current_chapter_start = segments[0]['start']  # Timestamp EXACT du premier segment
                current_chapter_texts = [segments[0]['text']]
                
                for i, seg in enumerate(segments[1:], 1):
                    # Créer un chapitre tous les 30-60 secondes ou à la fin
                    time_diff = seg['start'] - current_chapter_start
                    is_last = i == len(segments) - 1
                    
                    if time_diff >= 60 or is_last:  # Nouveau chapitre toutes les 60 secondes ou à la fin
                        # Générer un titre de chapitre basé sur le contenu accumulé
                        combined_text = " ".join(current_chapter_texts)[:300]
                        chapter_title = await self._generate_chapter_title(combined_text)
                        # Utiliser le timestamp EXACT du début du chapitre
                        timestamp_str = self._format_timestamp(current_chapter_start)
                        chapters.append({
                            "timestamp": timestamp_str,
                            "title": chapter_title or combined_text[:50].strip() + "..."
                        })
                        # Ajouter aussi à la description si pas déjà présent
                        chapter_line = f"{timestamp_str} - {chapter_title or combined_text[:50].strip() + '...'}"
                        chapters_from_segments.append(chapter_line)
                        # Nouveau chapitre commence au timestamp EXACT de ce segment
                        current_chapter_start = seg['start']
                        current_chapter_texts = [seg['text']]
                    else:
                        # Accumuler le texte du chapitre (mais garder le timestamp du début)
                        current_chapter_texts.append(seg['text'])
                
                # Ajouter le dernier chapitre si nécessaire
                if current_chapter_texts:
                    combined_text = " ".join(current_chapter_texts)[:300]
                    chapter_title = await self._generate_chapter_title(combined_text)
                    # Utiliser le timestamp EXACT
                    timestamp_str = self._format_timestamp(current_chapter_start)
                    chapters.append({
                        "timestamp": timestamp_str,
                        "title": chapter_title or combined_text[:50].strip() + "..."
                    })
                    # Ajouter aussi à la description si pas déjà présent
                    chapter_line = f"{timestamp_str} - {chapter_title or combined_text[:50].strip() + '...'}"
                    chapters_from_segments.append(chapter_line)
                
                result["chapters"] = chapters
                print(f"[OpenRouter] {len(chapters)} chapitres générés avec timestamps réels de la vidéo")
            
            lines = content.split("\n")
            current_section = None
            # description_lines est déjà initialisé plus haut
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                
                # Détection des sections (plus tolérant)
                line_upper = line.upper()
                
                if "TITRE" in line_upper:
                    current_section = None  # On va extraire le titre maintenant
                    # Extraire le titre après le ":"
                    if ":" in line:
                        title_part = line.split(":", 1)[1].strip()
                        if title_part:
                            result["title"] = title_part
                        else:
                            # Le titre est sur la ligne suivante
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line and not any(keyword in next_line.upper() for keyword in ["DESCRIPTION", "MOTS-CLES", "KEYWORDS", "CHAPITRES"]):
                                    result["title"] = next_line
                                    i += 1  # Skip la ligne suivante car on l'a utilisée
                    else:
                        # Pas de ":", le titre est sur la ligne suivante
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line and not any(keyword in next_line.upper() for keyword in ["DESCRIPTION", "MOTS-CLES", "KEYWORDS", "CHAPITRES"]):
                                result["title"] = next_line
                                i += 1  # Skip la ligne suivante
                    i += 1
                    continue
                elif "DESCRIPTION" in line_upper or "DESCRI" in line_upper:
                    current_section = "description"
                    # Extraire le début de la description après le ":"
                    if ":" in line:
                        desc_start = line.split(":", 1)[1].strip()
                        if desc_start:
                            description_lines.append(desc_start)
                    i += 1
                    continue
                elif "CHAPITRES" in line_upper or "CHAPTERS" in line_upper:
                    current_section = "chapters"
                    i += 1
                    continue
                elif "MOTS-CLES" in line_upper or "KEYWORDS" in line_upper or "MOTS CLES" in line_upper:
                    current_section = "keywords"
                    # Extraire les mots-clés après le ":"
                    if ":" in line:
                        keywords_str = line.split(":", 1)[1].strip()
                    else:
                        keywords_str = line
                    # Parser les mots-clés (virgules)
                    if keywords_str:
                        result["keywords"] = [k.strip() for k in keywords_str.split(",") if k.strip()]
                    i += 1
                    continue
                elif "HASHTAGS" in line_upper or "TAGS" in line_upper:
                    current_section = "hashtags"
                    # Extraire les hashtags après le ":"
                    if ":" in line:
                        tags_str = line.split(":", 1)[1].strip()
                    else:
                        tags_str = ""
                    # Parser les tags (virgules ou espaces)
                    hashtags_list = []
                    if tags_str:
                        if "," in tags_str:
                            hashtags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
                        else:
                            hashtags_list = [t.strip() for t in tags_str.split() if t.strip()]
                    # Continuer à lire les lignes suivantes pour les hashtags (jusqu'à la prochaine section)
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if not next_line:
                            i += 1
                            continue
                        # Si on rencontre une nouvelle section, arrêter
                        if any(keyword in next_line.upper() for keyword in ["TITRE", "DESCRIPTION", "CHAPITRES", "MOTS-CLES", "KEYWORDS"]):
                            break
                        # Parser cette ligne pour les hashtags
                        if "," in next_line:
                            hashtags_list.extend([t.strip() for t in next_line.split(",") if t.strip()])
                        else:
                            hashtags_list.extend([t.strip() for t in next_line.split() if t.strip()])
                        i += 1
                    result["hashtags"] = hashtags_list
                    continue
                
                # Ajouter au contenu de la section actuelle
                if current_section == "description":
                    # Vérifier si c'est une ligne de chapitre (format timestamp - titre)
                    if ":" in line and any(char.isdigit() for char in line.split(":")[0]):
                        # C'est probablement un chapitre, l'ajouter à la description aussi
                        description_lines.append(line)
                    # Ignorer les lignes qui commencent une nouvelle section
                    elif not any(keyword in line.upper() for keyword in ["MOTS-CLES", "KEYWORDS", "CHAPITRES", "HASHTAGS", "TAGS"]):
                        description_lines.append(line)
                elif current_section == "chapters":
                    # Parser les chapitres (format: timestamp - titre)
                    if ":" in line and any(char.isdigit() for char in line.split(":")[0]):
                        parts = line.split(" - ", 1)
                        if len(parts) == 2:
                            timestamp = parts[0].strip()
                            title = parts[1].strip()
                            result["chapters"].append({
                                "timestamp": timestamp,
                                "title": title
                            })
                
                i += 1
            
            # Construire la description
            result["description"] = "\n".join(description_lines).strip()
            result["description"] = result["description"].strip()
            
            # Ajouter les chapitres générés à partir des segments si disponibles
            if chapters_from_segments and len(chapters_from_segments) > 0:
                # Vérifier si "CHAPITRES:" n'est pas déjà dans la description
                if "CHAPITRES" not in result["description"].upper():
                    result["description"] += "\n\nCHAPITRES:"
                # Ajouter chaque chapitre
                for chapter_line in chapters_from_segments:
                    if chapter_line not in result["description"]:
                        result["description"] += "\n" + chapter_line
            
            # Ajouter les mots-clés à la fin de la description si présents
            if result["keywords"] and len(result["keywords"]) > 0:
                keywords_line = "Mots-clés: " + ", ".join(result["keywords"])
                if "Mots-clés:" not in result["description"]:
                    result["description"] += "\n\n" + keywords_line
            
            # Fallback: Générer des hashtags si l'IA ne les a pas générés
            if not result["hashtags"] or len(result["hashtags"]) == 0:
                hashtags_fallback = []
                # Utiliser les mots-clés comme base
                if result["keywords"]:
                    for keyword in result["keywords"][:10]:
                        # Nettoyer et formater en hashtag
                        tag = keyword.strip().replace(" ", "").replace("-", "")
                        if tag and len(tag) > 2:
                            hashtags_fallback.append(f"#{tag}")
                # Ajouter des hashtags basés sur le titre
                if result["title"]:
                    title_words = result["title"].split()
                    for word in title_words[:5]:
                        word_clean = word.strip().replace(",", "").replace(".", "").replace("!", "").replace("?", "")
                        if word_clean and len(word_clean) > 3:
                            hashtags_fallback.append(f"#{word_clean}")
                # Ajouter des hashtags génériques si nécessaire
                if language == "fr":
                    hashtags_fallback.extend(["#YouTube", "#Vidéo", "#Tutoriel", "#Tech", "#Montage"])
                else:
                    hashtags_fallback.extend(["#YouTube", "#Video", "#Tutorial", "#Tech", "#Editing"])
                result["hashtags"] = hashtags_fallback[:15]  # Limiter à 15
                print(f"[OpenRouter] Hashtags générés par fallback: {len(result['hashtags'])} hashtags")
            
            # Vérifier que nous avons au moins un titre et une description
            if result["title"] and result["description"]:
                print(f"[OpenRouter] Métadonnées générées: titre={len(result['title'])} chars, description={len(result['description'])} chars")
                if result.get("chapters"):
                    print(f"  - {len(result['chapters'])} chapitres avec timestamps réels")
                if result.get("keywords"):
                    print(f"  - {len(result['keywords'])} mots-clés")
                if result.get("hashtags"):
                    print(f"  - {len(result['hashtags'])} hashtags")
                return result
            else:
                print(f"[OpenRouter] Métadonnées incomplètes:")
                print(f"  - Titre: {bool(result['title'])} ({len(result['title'])} chars)")
                print(f"  - Description: {bool(result['description'])} ({len(result['description'])} chars)")
                print(f"[OpenRouter] Réponse brute (premiers 500 chars): {content[:500]}")
                return None
            
        except Exception as e:
            import traceback
            print(f"[OpenRouter] Exception: {e}")
            print(f"[OpenRouter] Type d'erreur: {type(e).__name__}")
            print(traceback.format_exc())
            return None
    
    def _format_timestamp(self, seconds: float) -> str:
        """Formater un timestamp en format HH:MM:SS pour YouTube"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    async def _generate_chapter_title(self, text: str) -> Optional[str]:
        """Générer un titre de chapitre court basé sur le texte"""
        if not text or len(text.strip()) < 10:
            return None
        
        client = self._get_client()
        if not client:
            return None
        
        try:
            prompt = f"""Génère un titre de chapitre YouTube court (max 50 caractères) basé sur ce texte:

{text[:300]}

Réponds UNIQUEMENT avec le titre, sans commentaires."""
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip()
            # Nettoyer le titre
            title = title.replace('"', '').replace("'", "").strip()
            return title[:50] if title else None
            
        except Exception as e:
            print(f"[OpenRouter] Erreur génération titre chapitre: {e}")
            return None
    
    async def generate_shorts_suggestions(
        self,
        segments: List[Dict],
        video_duration: float,
        language: str = "fr"
    ) -> Optional[List[Dict]]:
        """
        Analyser la transcription et suggérer 1-5 shorts de 5-30 secondes
        
        Args:
            segments: Liste des segments avec timestamps [{"start": float, "end": float, "text": str}]
            video_duration: Durée totale de la vidéo en secondes
            language: Langue cible
            
        Returns:
            Liste de shorts suggérés avec start, end, title, description
        """
        client = self._get_client()
        if not client:
            print("[OpenRouter] Client non disponible pour suggestions shorts")
            return None
        
        if not segments or len(segments) == 0:
            print("[OpenRouter] Aucun segment fourni pour suggestions shorts")
            return None
        
        # Formater les segments avec timestamps
        segments_text = "\n".join([
            f"[{self._format_timestamp(seg['start'])} - {self._format_timestamp(seg['end'])}] {seg['text']}"
            for seg in segments
        ])
        
        prompt = f"""Tu es un expert en création de contenu viral pour les réseaux sociaux. Analyse cette transcription de vidéo et identifie entre 1 et 5 moments parfaits pour créer des YouTube Shorts/TikToks.

Durée totale de la vidéo: {video_duration:.1f} secondes

Transcription avec timestamps:
{segments_text}

RÈGLES STRICTES:
1. Chaque short doit durer entre 3 et 60 secondes
2. Chaque short doit avoir un DÉBUT NATUREL (début de phrase, changement de sujet)
3. Chaque short doit avoir une FIN NATURELLE (fin de phrase, conclusion d'une idée)
4. Les shorts doivent contenir des moments intéressants, drôles, éducatifs ou impactants
5. Les timestamps de début et fin doivent EXACTEMENT correspondre aux timestamps fournis dans la transcription
6. Maximum 5 shorts, MINIMUM 1 OBLIGATOIRE - trouve TOUJOURS au moins un moment

IMPORTANT: Tu DOIS toujours trouver au moins 1 short. Si le contenu semble peu intéressant, choisis quand même le meilleur moment disponible (le plus clair, le plus complet, ou simplement le début de la vidéo).

Réponds UNIQUEMENT au format JSON (sans markdown, sans ```):
[
  {{
    "start": 12.5,
    "end": 35.2,
    "title": "Titre accrocheur du short",
    "description": "Pourquoi ce moment est parfait pour un short"
  }}
]"""

        try:
            print("[OpenRouter] Génération suggestions shorts...")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en contenu viral. Tu réponds UNIQUEMENT en JSON valide, sans markdown ni commentaires."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Un peu de créativité pour trouver les meilleurs moments
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Nettoyer le JSON (enlever les éventuels markdown)
            if content.startswith("```"):
                # Trouver le premier [ et le dernier ]
                start_idx = content.find("[")
                end_idx = content.rfind("]") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    content = content[start_idx:end_idx]
            
            # Parser le JSON
            try:
                shorts = json.loads(content)
                
                if not isinstance(shorts, list):
                    print(f"[OpenRouter] Réponse non-liste: {content[:200]}")
                    return []
                
                # Valider et filtrer les shorts
                valid_shorts = []
                for short in shorts:
                    if not isinstance(short, dict):
                        continue
                    
                    start = float(short.get("start", 0))
                    end = float(short.get("end", 0))
                    duration = end - start
                    
                    # Vérifier les contraintes
                    if start < 0 or end > video_duration:
                        print(f"[OpenRouter] Short ignoré: timestamps hors limites ({start}-{end})")
                        continue
                    if duration < 3 or duration > 60:
                        print(f"[OpenRouter] Short ignoré: durée invalide ({duration:.1f}s)")
                        continue
                    if not short.get("title"):
                        continue
                    
                    valid_shorts.append({
                        "start": start,
                        "end": end,
                        "duration": round(duration, 1),
                        "title": short.get("title", "")[:100],
                        "description": short.get("description", "")[:200],
                        "timestamp_start": self._format_timestamp(start),
                        "timestamp_end": self._format_timestamp(end)
                    })
                
                print(f"[OpenRouter] {len(valid_shorts)} short(s) suggéré(s)")
                
                # Si aucun short trouvé, créer un short par défaut au début
                if len(valid_shorts) == 0:
                    default_duration = min(15.0, video_duration)  # 15s max ou durée totale
                    valid_shorts = [{
                        "start": 0,
                        "end": default_duration,
                        "duration": default_duration,
                        "title": "Extrait de la vidéo",
                        "description": "Début de la vidéo",
                        "timestamp_start": self._format_timestamp(0),
                        "timestamp_end": self._format_timestamp(default_duration)
                    }]
                    print(f"[OpenRouter] Aucun moment trouvé, short par défaut créé (0-{default_duration}s)")
                
                return valid_shorts[:5]  # Maximum 5
                
            except json.JSONDecodeError as e:
                print(f"[OpenRouter] Erreur parsing JSON: {e}")
                print(f"[OpenRouter] Contenu brut: {content[:500]}")
                # Retourner un short par défaut en cas d'erreur de parsing
                default_duration = min(15.0, video_duration)
                return [{
                    "start": 0,
                    "end": default_duration,
                    "duration": default_duration,
                    "title": "Extrait de la vidéo",
                    "description": "Début de la vidéo",
                    "timestamp_start": self._format_timestamp(0),
                    "timestamp_end": self._format_timestamp(default_duration)
                }]
                
        except Exception as e:
            import traceback
            print(f"[OpenRouter] Exception suggestions shorts: {e}")
            traceback.print_exc()
            # Retourner un short par défaut même en cas d'erreur
            default_duration = min(15.0, video_duration)
            return [{
                "start": 0,
                "end": default_duration,
                "duration": default_duration,
                "title": "Extrait de la vidéo",
                "description": "Début de la vidéo",
                "timestamp_start": self._format_timestamp(0),
                "timestamp_end": self._format_timestamp(default_duration)
            }]
    
    async def analyze_for_illustrations(
        self,
        segments: List[Dict],
        video_duration: float,
        max_illustrations: int = 5
    ) -> Optional[List[Dict]]:
        """
        Analyse la transcription pour identifier les moments à illustrer
        avec des clips/images de stock (Pexels/Unsplash)
        
        Retourne une liste de moments avec mots-clés pour la recherche
        """
        print(f"[OpenRouter] Analyse pour illustrations...")
        
        client = self._get_client()
        if not client:
            return None
        
        # Construire le texte avec timestamps
        transcript_text = ""
        for segment in segments:
            start = segment.get("start", 0)
            text = segment.get("text", "").strip()
            if text:
                timestamp = self._format_timestamp(start)
                transcript_text += f"[{timestamp}] {text}\n"
        
        prompt = f"""Analyse cette transcription vidéo et identifie les meilleurs moments pour insérer un B-ROLL (clip vidéo uniquement, PAS d'image fixe).

TRANSCRIPTION:
{transcript_text[:6000]}

DURÉE TOTALE: {video_duration:.1f} secondes

INSTRUCTIONS:
1. Identifie SEULEMENT {max_illustrations} moments clés maximum (pas plus !)
2. Choisis des moments espacés dans la vidéo
3. Pour chaque moment, fournis:
   - timestamp: le moment exact en secondes
   - duration: durée du B-roll (2-3 secondes)
   - keyword: mot-clé EN ANGLAIS pour rechercher un CLIP VIDÉO sur Pexels (1-2 mots simples)
   - reason: pourquoi ce moment mérite un B-roll

CRITÈRES:
- Privilégier les moments visuellement représentables (actions, objets, lieux)
- Éviter les concepts trop abstraits
- Espacer les B-rolls (pas 2 B-rolls consécutifs)

MOTS-CLÉS POUR CLIPS VIDÉO:
- Utiliser des termes GÉNÉRIQUES et CONCRETS (ex: "coding", "typing", "city", "nature")
- Éviter les termes trop spécifiques qui ne trouveront pas de résultats
- Penser "vidéo en mouvement" pas "image fixe"

Réponds UNIQUEMENT en JSON valide:
[
  {{"timestamp": 15.5, "duration": 4, "keyword": "coding laptop", "reason": "Moment de programmation"}},
  ...
]"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en montage vidéo. Tu identifies les moments où des B-rolls (clips d'illustration) amélioreraient une vidéo. Réponds uniquement en JSON valide."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extraire le JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            illustrations = json.loads(content)
            
            if not isinstance(illustrations, list):
                print(f"[OpenRouter] Format invalide pour illustrations")
                return None
            
            # Valider et nettoyer les résultats
            valid_illustrations = []
            for illust in illustrations:
                if not isinstance(illust, dict):
                    continue
                
                timestamp = float(illust.get("timestamp", 0))
                duration = float(illust.get("duration", 3))
                keyword = illust.get("keyword", "").strip()
                reason = illust.get("reason", "")
                
                # Vérifier la validité
                if timestamp < 0 or timestamp >= video_duration:
                    continue
                if not keyword:
                    continue
                if duration < 1 or duration > 10:
                    duration = 3
                
                valid_illustrations.append({
                    "timestamp": timestamp,
                    "duration": duration,
                    "keyword": keyword,
                    "reason": reason
                })
            
            print(f"[OpenRouter] {len(valid_illustrations)} moments d'illustration identifiés")
            return valid_illustrations[:max_illustrations]
            
        except Exception as e:
            print(f"[OpenRouter] Erreur analyse illustrations: {e}")
            return None
    
    async def generate_thumbnail_prompt(
        self,
        transcript: str,
        title: str,
        language: str = "fr"
    ) -> Optional[str]:
        """
        Générer un prompt optimisé pour créer une miniature YouTube attractive
        
        Args:
            transcript: Transcription de la vidéo
            title: Titre de la vidéo
            language: Langue
            
        Returns:
            Prompt détaillé pour génération d'image
        """
        client = self._get_client()
        if not client:
            return None
        
        # Tronquer la transcription
        short_transcript = transcript[:2000] if len(transcript) > 2000 else transcript
        
        prompt = f"""Tu es un expert en création de miniatures YouTube VIRALES qui génèrent des millions de vues. Génère un prompt détaillé en anglais pour créer une miniature ULTRA-ACCROCHEUSE.

TITRE DE LA VIDÉO: {title}

RÉSUMÉ DU CONTENU:
{short_transcript}

INSTRUCTIONS:
1. Crée d'abord un titre COURT ET VIRAL (3-5 mots max) basé sur le titre original
2. Ensuite, génère un prompt visuel détaillé incluant ce titre

EXEMPLES DE TITRES VIRAUX:
- "CURSOR = FERRARI!" (comparaison choc)
- "10X PLUS RAPIDE!" (chiffre + bénéfice)
- "C'EST CHOC!" (curiosité)
- "100% GRATUIT!" (valeur)
- "VOUS N'ALLEZ PAS Y CROIRE!" (surprise)

FORMAT DE RÉPONSE (en anglais):
TITLE: [ton titre court viral ici]

VISUAL PROMPT: [prompt détaillé de 150-200 mots décrivant l'image complète avec le texte inclus]

Le prompt visuel doit inclure:
- LE PERSONNAGE PHOTORÉALISTE: Le personnage de la webcam doit être GRAND (45-55% de l'image), apparaissant NATURELLEMENT au premier plan avec un effet de profondeur réaliste. Le personnage doit être PHOTORÉALISTE (comme une vraie photo, pas cartoon, pas illustration). Éclairage portrait réaliste (lumière clé naturelle, rim lighting subtil, ombre portée naturelle), expression naturelle mais expressive (surprise, enthousiasme), personnage naturellement positionné
- Le texte principal (le titre créé) en TRÈS GRAND (60-70% de la hauteur), BOLD, UPPERCASE, avec contour épais noir (10px) et couleur jaune vif ou blanc, positionné DERRIÈRE le personnage (créant des couches de profondeur réalistes)
- Flèches rouges géantes pointant vers le texte ET le personnage
- Cercles rouges, badges "NEW" ou "HOT" autour du personnage
- Explosions, éclairs, effets de vitesse DERRIÈRE le personnage (fond très flou avec bokeh réaliste) pour le faire ressortir naturellement
- Couleurs vives (rouge #FF0000, jaune #FFFF00, bleu #00FFFF)
- Composition photoréaliste avec profondeur: Personnage au premier plan (gauche ou droite, naturellement positionné), texte au centre/haut DERRIÈRE le personnage, effets dynamiques en arrière-plan très flou avec bokeh réaliste
- Éclairage portrait réaliste: Lumière clé naturelle sur le visage créant des ombres réalistes, rim lighting subtil autour du personnage (séparation naturelle), fond naturellement plus sombre pour contraste réaliste
- Style PHOTORÉALISTE professionnel avec profondeur de champ EXTREME (personnage net comme une photo portrait f/1.4, fond très flou avec bokeh crémeux réaliste), ombre portée naturelle derrière le personnage créant la profondeur réaliste

Réponds dans ce format exact."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extraire le titre et le prompt visuel
            thumbnail_title = None
            visual_prompt = None
            
            # Chercher le titre après "TITLE:"
            if "TITLE:" in response_text.upper():
                title_match = response_text.split("TITLE:", 1)[1].split("VISUAL PROMPT:", 1)[0].strip()
                thumbnail_title = title_match.split("\n")[0].strip()
            
            # Chercher le prompt visuel après "VISUAL PROMPT:"
            if "VISUAL PROMPT:" in response_text.upper():
                visual_prompt = response_text.split("VISUAL PROMPT:", 1)[1].strip()
            else:
                # Si pas de format structuré, utiliser tout le texte
                visual_prompt = response_text
            
            # Combiner le titre et le prompt visuel
            if thumbnail_title:
                final_prompt = f"""Create a VIRAL YouTube thumbnail with this EXACT TEXT prominently displayed:

TEXT TO DISPLAY: "{thumbnail_title.upper()}"

VISUAL DESCRIPTION:
{visual_prompt}

CRITICAL: The text "{thumbnail_title.upper()}" MUST be included in the image, VERY LARGE (70-80% of height), BOLD, with thick black outline."""
            else:
                final_prompt = visual_prompt if visual_prompt else response_text
            
            print(f"[OpenRouter] Prompt miniature généré: {len(final_prompt)} chars")
            if thumbnail_title:
                print(f"[OpenRouter] Titre viral extrait: {thumbnail_title}")
            
            return final_prompt
            
        except Exception as e:
            print(f"[OpenRouter] Erreur génération prompt miniature: {e}")
            return None
    
    async def generate_thumbnail_with_gemini(
        self,
        prompt: str,
        webcam_frame_base64: Optional[str] = None,
        output_path: str = "thumbnail.png"
    ) -> Optional[str]:
        """
        Générer une miniature YouTube avec Gemini (google/gemini-3-pro-image-preview)
        
        Args:
            prompt: Prompt de génération
            webcam_frame_base64: Frame de la webcam en base64 (pour inclure le personnage)
            output_path: Chemin de sortie de l'image
            
        Returns:
            Chemin du fichier généré ou None si erreur
        """
        import aiohttp
        import base64
        
        if not self.api_key:
            print("[OpenRouter] API key non configurée pour Gemini")
            return None
        
        # Construire le prompt avec contexte
        full_prompt = f"""Create a VIRAL YouTube thumbnail image that will get MILLIONS of clicks. Follow these specifications EXACTLY:

{prompt}

CRITICAL VIRAL THUMBNAIL REQUIREMENTS (MUST FOLLOW ALL):
1. TEXT IS MANDATORY AND DOMINANT:
   - Include the main title text EXTREMELY LARGE (70-80% of image height)
   - Text must be BOLD, UPPERCASE, with THICK black outline (10-12px) for maximum readability
   - Text color: Bright yellow (#FFFF00) or white (#FFFFFF) with black outline
   - Position: Centered or slightly diagonal for dynamism
   - Add strong drop shadow and glow effect
   - Background: Dark semi-transparent overlay (black with 50% opacity) behind text

2. ULTRA-VIBRANT COLORS:
   - Primary: Bright red (#FF0000), electric yellow (#FFFF00), neon blue (#00FFFF)
   - Extreme contrasts: Dark backgrounds with bright foregrounds
   - Saturation: MAXIMUM (100%)

3. SHOCK ELEMENTS (MUST INCLUDE):
   - Large red arrows (2-3) pointing directly at the text
   - Red circles or badges with "NEW", "HOT", "FREE", or "10X"
   - Explosion effects around key elements
   - Lightning bolts or electric effects
   - Speed lines or motion blur
   - Particle effects

4. NATURAL BUT EXPRESSIVE EMOTIONS FROM THE PERSON:
   - THE PERSON'S FACE must show NATURAL emotion (surprised, excited, but REALISTIC, not exaggerated cartoon)
   - Person's expression should be NATURAL and PHOTOREALISTIC (like a real person, not cartoon)
   - Person's hands NATURALLY positioned or gesturing (realistic gesture, not dramatic cartoon)
   - The person's expression should NATURALLY convey the emotion of the video topic
   - Person should look NATURALLY at camera or at the text (natural eye contact, photorealistic)

5. PHOTOREALISTIC COMPOSITION WITH REALISTIC 3D DEPTH:
   - THE PERSON IS THE DOMINANT ELEMENT (45-55% of image, large, naturally in foreground, PHOTOREALISTIC)
   - Person positioned naturally on left or right side (rule of thirds, realistic portrait composition)
   - Text positioned BEHIND person (creating realistic depth layers: Person in front, text behind)
   - EXTREME DEPTH LAYERS: Foreground (PERSON - crystal sharp, photorealistic), Midground (text - slightly blurred), Background (effects - heavily blurred with realistic bokeh)
   - Person naturally in front of other elements (realistic depth, not breaking frame unnaturally)
   - Natural composition: Professional portrait composition, person naturally positioned
   - Person's shadow naturally cast (realistic lighting, natural shadow)
   - Natural pose: Person naturally positioned, photorealistic

6. HOOK ELEMENTS:
   - Large numbers or percentages (if relevant)
   - Badges or stickers
   - Call-to-action elements

7. PHOTOREALISTIC QUALITY WITH REALISTIC 3D DEPTH:
   - REALISTIC PORTRAIT LIGHTING ON PERSON: 
     * REALISTIC KEY LIGHT from front-left/right creating natural shadows on face (like professional portrait)
     * NATURAL RIM LIGHT from behind creating realistic separation (not glowing, just natural highlight)
     * NATURAL BACK LIGHT creating realistic separation and volume
     * Natural light sources creating REALISTIC 3D FORM (face looks naturally rounded, photorealistic)
   - PERFECT PHOTOREALISTIC SHARPNESS: PERSON crystal sharp (like f/1.4 portrait, photorealistic), text slightly soft, background EXTREMELY blurred with realistic bokeh
   - EXTREME DEPTH OF FIELD: PERSON in perfect focus (appears close, photorealistic), background EXTREMELY blurred with CREAMY BOKEH (appears far, realistic)
   - REALISTIC COLOR GRADING: Person warm/vibrant colors (appears close), background cool/desaturated (appears far, realistic)
   - NATURAL SEPARATION: Person naturally separated from background through realistic depth of field and natural lighting (NO glowing halos on person, keep person photorealistic)
   - NATURAL CONTRAST: Person naturally contrasted (realistic highlights and shadows), background naturally softer
   - REALISTIC SHADOWS: Natural cast shadow (realistic lighting, natural shadow falloff)
   - The person should look PHOTOREALISTIC, like a REAL PROFESSIONAL PHOTOGRAPH with realistic depth of field

8. TECHNICAL SPECS:
   - Resolution: 1280x720 pixels (16:9 aspect ratio)
   - Format: High quality, sharp, no compression artifacts
   - Every pixel must be optimized for maximum clickability

MAXIMUM CLICKABILITY RULE: Every single element must scream "CLICK ME NOW!" The thumbnail should be impossible to ignore.

Generate the COMPLETE thumbnail image WITH ALL TEXT AND ELEMENTS NOW. Make it ULTRA-VIRAL, CLICKABLE, and PROFESSIONAL!"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "YouTube Pipeline",
            "Content-Type": "application/json"
        }
        
        # Construire le message
        messages = []
        
        if webcam_frame_base64:
            # Inclure la frame webcam pour que Gemini puisse extraire le personnage
            person_prompt = """
CRITICAL: THE PERSON FROM THE PROVIDED IMAGE MUST BE PHOTOREALISTIC (REAL-LIFE PHOTO) BUT WITH EXTREME 3D DEPTH:

1. PHOTOREALISTIC PERSON WITH 3D DEPTH:
   - The person must look like a REAL PHOTOGRAPH (photorealistic, not cartoon, not illustration)
   - Use REALISTIC forced perspective: Person appears MUCH CLOSER than background (like real portrait photography)
   - Create REALISTIC illusion of depth: Person's face/body should appear naturally in foreground
   - The person should look like they're NATURALLY IN FRONT OF THE CAMERA (realistic close-up portrait)

2. REALISTIC BUT DRAMATIC 3D LIGHTING:
   - REALISTIC KEY LIGHT: Bright but natural spotlight from front-left or front-right (like professional portrait studio)
   - REALISTIC RIM LIGHTING: Natural edge light around the person creating realistic separation (not glowing, just natural highlight)
   - REALISTIC FILL LIGHT: Soft natural fill light on shadow side to maintain detail
   - REALISTIC BACK LIGHT: Natural light from behind creating realistic separation from background
   - The lighting should create REALISTIC 3D VOLUME (face looks naturally rounded, photorealistic)

3. REALISTIC SIZE AND SCALE WITH 3D PERSPECTIVE:
   - The person must occupy 45-55% of the thumbnail (large, realistic portrait size)
   - Face should be LARGE (like a professional portrait close-up, realistic)
   - Use REALISTIC foreshortening: Natural perspective (hands/arms closer appear naturally larger)
   - The person should appear to be NATURALLY IN FRONT OF THE CAMERA (realistic close-up, not extreme)

4. REALISTIC 3D SHADOWS AND DEPTH:
   - REALISTIC CAST SHADOW: Natural shadow BEHIND the person (realistic lighting, natural shadow)
   - Shadow should be NATURAL and REALISTIC (like person standing in real studio light)
   - Natural shadow falloff: Shadow gets softer as it extends away (realistic)
   - Shadow should look REALISTIC (not exaggerated, just natural depth)

5. PHOTOREALISTIC VOLUME AND FORM:
   - Face must have NATURAL 3D VOLUME (realistic cheekbones, nose, chin with natural depth)
   - Use REALISTIC chiaroscuro (natural light/dark contrast) to show 3D form
   - Clothing should show NATURAL folds and wrinkles (realistic texture, photorealistic)
   - Hair should have NATURAL volume and depth (realistic hair, photorealistic)
   - The person should look PHOTOREALISTIC, like a REAL PHOTOGRAPH, not a cartoon or illustration

6. NATURAL BUT EXPRESSIVE EXPRESSION AND POSE:
   - NATURAL facial expression (surprised, excited, but REALISTIC, not exaggerated cartoon)
   - Person NATURALLY positioned (not leaning unnaturally, just naturally forward)
   - Hands/arms NATURALLY positioned or gesturing (realistic gesture, not dramatic cartoon)
   - Natural eye contact and expression (realistic)
   - REALISTIC pose: Natural body position, photorealistic

7. VISUAL EFFECTS FOR 3D POP-OUT (BUT PERSON STAYS REALISTIC):
   - NATURAL DEPTH BLUR: Background heavily blurred with REALISTIC bokeh (like f/1.4 portrait), person crystal sharp
   - NATURAL COLOR SEPARATION: Person naturally vibrant, background naturally desaturated (realistic color grading)
   - PARTICLE EFFECTS: Sparks, energy, light rays AROUND the person (visual effects, but person stays photorealistic)
   - NO ARTIFICIAL GLOWING HALO on person (keep person realistic, effects are separate)
   - REFLECTIONS: Natural reflections on person's skin/clothing (realistic surface properties)

8. REALISTIC COMPOSITION WITH 3D DEPTH:
   - Person positioned naturally on left/right (rule of thirds, realistic portrait composition)
   - Text positioned behind person (creating realistic depth layers)
   - Person naturally in front of other elements (realistic depth)
   - Natural composition: Professional portrait composition
   - Person should look NATURALLY IN FRONT (realistic depth, not breaking frame unnaturally)

9. PHOTOREALISTIC TECHNICAL QUALITY WITH 3D DEPTH:
   - EXTREME DEPTH OF FIELD: Person EXTREMELY sharp (like f/1.4 portrait, photorealistic), background EXTREMELY blurred (realistic bokeh)
   - REALISTIC COLOR GRADING: Person warm tones, background cool tones (realistic color separation)
   - NATURAL CONTRAST: Person naturally contrasted (realistic highlights and shadows), background naturally softer
   - NATURAL SATURATION: Person naturally saturated, background naturally desaturated
   - The person should look like a REAL PHOTOGRAPH with realistic depth of field

STYLE: PHOTOREALISTIC, REALISTIC, LIKE A REAL PHOTOGRAPH. The person must look REAL, not cartoon, not illustration, not 3D model.
BUT with extreme depth of field and visual effects around them for 3D pop-out effect.

USE THE PERSON'S EXACT LIKENESS FROM THE PROVIDED IMAGE, and render them PHOTOREALISTICALLY (like a real photograph) with REALISTIC 3D DEPTH through natural depth of field and realistic lighting. The person should look like a REAL PERSON IN A REAL PHOTOGRAPH, not a cartoon, not an illustration, not a 3D model.
"""
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{person_prompt}\n\n{full_prompt}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{webcam_frame_base64}"
                        }
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": full_prompt
            })
        
        payload = {
            "model": "google/gemini-3-pro-image-preview",
            "messages": messages,
            "max_tokens": 4096
        }
        
        try:
            print("[OpenRouter] Génération miniature avec Gemini...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[OpenRouter] Erreur Gemini: {response.status} - {error_text[:500]}")
                        return None
                    
                    data = await response.json()
                    
                    # Debug: sauvegarder la réponse complète dans un fichier temporaire
                    debug_file = Path(output_path).parent / "gemini_response_debug.json"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"[OpenRouter] Réponse Gemini sauvegardée dans: {debug_file}")
                    
                    # Extraire le contenu de la réponse
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Vérifier d'abord la clé "images" (format Gemini)
                    message = data.get("choices", [{}])[0].get("message", {})
                    images = message.get("images", [])
                    if images:
                        for img in images:
                            img_type = img.get("type", "")
                            if img_type == "image_url":
                                image_url = img.get("image_url", {}).get("url", "")
                                if image_url.startswith("data:image"):
                                    image_data = image_url.split("base64,")[1]
                                    try:
                                        image_bytes = base64.b64decode(image_data)
                                        with open(output_path, "wb") as f:
                                            f.write(image_bytes)
                                        print(f"[OpenRouter] Miniature générée depuis images[].image_url: {output_path}")
                                        return output_path
                                    except Exception as e:
                                        print(f"[OpenRouter] Erreur décodage images[].image_url: {e}")
                            elif img_type == "image" and "b64_json" in img:
                                b64_json = img.get("b64_json", "")
                                if b64_json:
                                    try:
                                        image_bytes = base64.b64decode(b64_json)
                                        with open(output_path, "wb") as f:
                                            f.write(image_bytes)
                                        print(f"[OpenRouter] Miniature générée depuis images[].b64_json: {output_path}")
                                        return output_path
                                    except Exception as e:
                                        print(f"[OpenRouter] Erreur décodage images[].b64_json: {e}")
                    
                    # Vérifier si c'est une liste (format multimodal)
                    if isinstance(message.get("content"), list):
                        # Chercher une image dans le contenu multimodal
                        for item in message["content"]:
                            item_type = item.get("type", "")
                            
                            # Format 1: image_url avec data:image
                            if item_type == "image_url":
                                image_url = item.get("image_url", {}).get("url", "")
                                if image_url.startswith("data:image"):
                                    image_data = image_url.split("base64,")[1]
                                    try:
                                        image_bytes = base64.b64decode(image_data)
                                        with open(output_path, "wb") as f:
                                            f.write(image_bytes)
                                        print(f"[OpenRouter] Miniature générée depuis image_url: {output_path}")
                                        return output_path
                                    except Exception as e:
                                        print(f"[OpenRouter] Erreur décodage image_url: {e}")
                            
                            # Format 2: image avec b64_json
                            elif item_type == "image":
                                image_obj = item.get("image", {})
                                b64_json = image_obj.get("b64_json", "")
                                if b64_json:
                                    try:
                                        image_bytes = base64.b64decode(b64_json)
                                        with open(output_path, "wb") as f:
                                            f.write(image_bytes)
                                        print(f"[OpenRouter] Miniature générée depuis b64_json: {output_path}")
                                        return output_path
                                    except Exception as e:
                                        print(f"[OpenRouter] Erreur décodage b64_json: {e}")
                            
                            # Format 3: image avec url directe
                            elif item_type == "image" and "url" in item:
                                image_url = item.get("url", "")
                                if image_url.startswith("data:image"):
                                    image_data = image_url.split("base64,")[1]
                                    try:
                                        image_bytes = base64.b64decode(image_data)
                                        with open(output_path, "wb") as f:
                                            f.write(image_bytes)
                                        print(f"[OpenRouter] Miniature générée depuis image.url: {output_path}")
                                        return output_path
                                    except Exception as e:
                                        print(f"[OpenRouter] Erreur décodage image.url: {e}")
                    
                    # Vérifier si la réponse contient une image en base64
                    if "data:image" in content or content.startswith("/9j/") or content.startswith("iVBOR"):
                        # Extraire le base64 de l'image
                        if "base64," in content:
                            image_data = content.split("base64,")[1].split('"')[0]
                        else:
                            image_data = content
                        
                        # Décoder et sauvegarder
                        try:
                            image_bytes = base64.b64decode(image_data)
                            with open(output_path, "wb") as f:
                                f.write(image_bytes)
                            print(f"[OpenRouter] Miniature générée: {output_path}")
                            return output_path
                        except Exception as e:
                            print(f"[OpenRouter] Erreur décodage image: {e}")
                            return None
                    else:
                        # Gemini n'a pas généré d'image directement
                        # On peut utiliser le texte retourné comme nouveau prompt
                        print(f"[OpenRouter] Gemini n'a pas généré d'image directement")
                        print(f"[OpenRouter] Réponse: {content[:500]}")
                        return None
                        
        except Exception as e:
            import traceback
            print(f"[OpenRouter] Erreur génération miniature: {e}")
            traceback.print_exc()
            return None
    
    async def generate_short_metadata(
        self,
        transcript_segment: str,
        short_index: int,
        language: str = "fr"
    ) -> Optional[Dict]:
        """
        Générer titre et description pour un short avec mentions branding
        
        Args:
            transcript_segment: Transcription du segment du short
            short_index: Numéro du short
            language: Langue
            
        Returns:
            Dict avec title, description, hashtags
        """
        client = self._get_client()
        if not client:
            return None
        
        prompt = f"""Tu es un expert en création de contenu viral. Génère un titre et une description pour ce short YouTube/TikTok.

TRANSCRIPTION DU SHORT:
{transcript_segment[:1000]}

RÈGLES:
1. Titre: Maximum 60 caractères, accrocheur, avec emoji
2. Description: 2-3 lignes engageantes
3. Inclure un appel à l'action pour rejoindre la communauté
4. Mentionner: skool.com/vibeacademy ou vibeacademy.eu
5. Ajouter 5-10 hashtags pertinents

Réponds au format JSON:
{{
  "title": "🔥 Titre accrocheur ici",
  "description": "Description engageante...\\n\\n🚀 Rejoins la communauté: skool.com/vibeacademy",
  "hashtags": ["#short", "#tutorial", "#tech"]
}}"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu génères du contenu viral pour les réseaux sociaux. Réponds uniquement en JSON valide."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extraire le JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Assurer que les mentions sont présentes
            if "skool.com/vibeacademy" not in result.get("description", ""):
                result["description"] += "\n\n🚀 Rejoins-nous: skool.com/vibeacademy"
            
            print(f"[OpenRouter] Métadonnées short {short_index} générées")
            return result
            
        except Exception as e:
            print(f"[OpenRouter] Erreur génération métadonnées short: {e}")
            # Retourner des valeurs par défaut
            return {
                "title": f"🔥 Short #{short_index}",
                "description": f"Découvre ce moment incroyable!\n\n🚀 Rejoins la communauté: skool.com/vibeacademy\n🌐 Plus d'infos: vibeacademy.eu",
                "hashtags": ["#short", "#viral", "#tutorial", "#vibeacademy"]
            }

