'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  Video, 
  Trash2, 
  FileText,
  Loader2,
  RefreshCw,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  X,
  VolumeX,
  Scissors,
  Wand2,
  Folder,
  FolderOpen,
  FileVideo,
  FileJson,
  ChevronRight,
  ChevronDown,
  Check,
  Volume2,
  Settings2,
  Move,
  Camera,
  Film,
  Sparkles,
  Download
} from 'lucide-react';

// Interface pour les suggestions de shorts
interface ShortSuggestion {
  start: number;
  end: number;
  duration: number;
  title: string;
  description: string;
  timestamp_start: string;
  timestamp_end: string;
}

interface ShortFile {
  name: string;
  path: string;
  size: number;
}

interface VideoFile {
  name: string;
  size: number;
  url: string;
  created: string;
  folder?: string | null;
  has_original?: boolean;
  has_nosilence?: boolean;
  has_transcription?: boolean;
  has_screen?: boolean;
  has_webcam?: boolean;
  has_screen_nosilence?: boolean;
  has_webcam_nosilence?: boolean;
  has_shorts?: boolean;
  shorts?: ShortFile[];
}

interface FileListProps {
  onLog?: (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => void;
}

export function FileList({ onLog }: FileListProps) {
  const [files, setFiles] = useState<VideoFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<VideoFile | null>(null);
  const [transcription, setTranscription] = useState<{ 
    filename: string; 
    text: string; 
    segments: Array<{ start: number; end: number; text: string }>;
    seo?: {
      title: string;
      description: string;
      keywords?: string[];
      hashtags?: string[];
      chapters?: Array<{ timestamp: string; title: string }>;
    };
  } | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [audioWaveform, setAudioWaveform] = useState<number[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameRate, setFrameRate] = useState(60); // Default 60fps
  const [isRemovingSilences, setIsRemovingSilences] = useState(false);
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null); // URL de la vidéo actuellement chargée
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Paramètres de détection de silence
  const [silenceThreshold, setSilenceThreshold] = useState(-40); // dB (de -60 à -20)
  const [minSilenceDuration, setMinSilenceDuration] = useState(0.5); // secondes
  const [detectedSilences, setDetectedSilences] = useState<Array<{start: number; end: number}>>([]);
  const [showSilenceSettings, setShowSilenceSettings] = useState(false);
  
  // Paramètres de repositionnement webcam
  const [showWebcamReposition, setShowWebcamReposition] = useState(false);
  const [isRepositioning, setIsRepositioning] = useState(false);
  const [webcamX, setWebcamX] = useState(50);
  const [webcamY, setWebcamY] = useState(50);
  const [webcamSize, setWebcamSize] = useState(300);
  const [webcamShape, setWebcamShape] = useState<'circle' | 'rectangle'>('circle');
  const [borderThickness, setBorderThickness] = useState(4); // Épaisseur du bord (0-20)
  const [borderColor, setBorderColor] = useState('#ec4899'); // Couleur du bord
  const [isDraggingWebcam, setIsDraggingWebcam] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const previewContainerRef = useRef<HTMLDivElement>(null);
  const webcamVideoRef = useRef<HTMLVideoElement>(null);
  
  // Paramètres shorts
  const [showShortsPanel, setShowShortsPanel] = useState(false);
  const [shortsSuggestions, setShortsSuggestions] = useState<ShortSuggestion[]>([]);
  const [isLoadingShorts, setIsLoadingShorts] = useState(false);
  const [creatingShortIndex, setCreatingShortIndex] = useState<number | null>(null);
  const [createdShorts, setCreatedShorts] = useState<string[]>([]);
  
  const log = (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => {
    onLog?.(type, message);
  };

  // Calcul du temps de frame
  const frameDuration = 1 / frameRate;
  const currentFrame = Math.floor(currentTime * frameRate);
  const totalFrames = Math.floor(videoDuration * frameRate);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimeWithFrames = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const frame = Math.floor((seconds % 1) * frameRate);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frame.toString().padStart(2, '0')}`;
  };

  // Navigation frame par frame
  const nextFrame = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
      const newTime = Math.min(videoRef.current.currentTime + frameDuration, videoDuration);
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const prevFrame = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
      const newTime = Math.max(videoRef.current.currentTime - frameDuration, 0);
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  // Gestion des raccourcis clavier
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ne pas intercepter si on est dans un input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      
      if (!selectedFile || !videoRef.current) return;

      switch (e.code) {
        case 'Space':
          e.preventDefault();
          togglePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          prevFrame();
          break;
        case 'ArrowRight':
          e.preventDefault();
          nextFrame();
          break;
        case 'ArrowUp':
          e.preventDefault();
          // Avancer de 1 seconde
          if (videoRef.current) {
            const newTime = Math.min(videoRef.current.currentTime + 1, videoDuration);
            videoRef.current.currentTime = newTime;
            setCurrentTime(newTime);
          }
          break;
        case 'ArrowDown':
          e.preventDefault();
          // Reculer de 1 seconde
          if (videoRef.current) {
            const newTime = Math.max(videoRef.current.currentTime - 1, 0);
            videoRef.current.currentTime = newTime;
            setCurrentTime(newTime);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedFile, isPlaying, videoDuration, frameDuration]);

  // Repositionner la webcam sur l'écran
  const repositionWebcam = async () => {
    if (!selectedFile || isRepositioning) return;
    
    // Vérifier que les fichiers nosilence existent
    if (!selectedFile.has_screen_nosilence || !selectedFile.has_webcam_nosilence) {
      log('error', 'Les fichiers screen_nosilence.mp4 et webcam_nosilence.mp4 sont requis');
      log('info', 'Lance d\'abord "Supprimer silences" pour créer ces fichiers');
      return;
    }
    
    setIsRepositioning(true);
    log('action', `Repositionnement webcam sur ${selectedFile.name}...`);
    log('info', `Position: x=${webcamX}, y=${webcamY}, taille=${webcamSize}, forme=${webcamShape}, bordure=${borderThickness}px`);
    
    try {
      const response = await fetch('/api/reposition-webcam', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder_name: selectedFile.name,
          webcam_x: webcamX,
          webcam_y: webcamY,
          webcam_size: webcamSize,
          webcam_shape: webcamShape,
          border_thickness: borderThickness,
          border_color: borderColor.replace('#', ''),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        log('success', `Webcam repositionnée ! Nouveau fichier: nosilence.mp4`);
        
        // Rafraîchir la liste des fichiers
        const filesResponse = await fetch(`/api/files?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' },
        });
        
        if (filesResponse.ok) {
          const filesData = await filesResponse.json();
          const validFiles = (filesData.files || [])
            .filter((f: VideoFile) => f.name && f.url);
          setFiles(validFiles);
          
          // Recharger la vidéo
          const uniqueId = `${Date.now()}_${Math.random().toString(36).substring(7)}`;
          const newUrl = `/output/${selectedFile.name}/nosilence.mp4?nocache=${uniqueId}`;
          setActiveVideoUrl(newUrl);
          log('info', `Vidéo rechargée`);
        }
        
        setShowWebcamReposition(false);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        log('error', `Erreur: ${errorData.detail || 'Impossible de repositionner la webcam'}`);
      }
    } catch (err: any) {
      log('error', `Erreur: ${err.message}`);
    } finally {
      setIsRepositioning(false);
    }
  };

  // Générer des suggestions de shorts
  const generateShortsSuggestions = async () => {
    if (!selectedFile || !transcription?.segments || isLoadingShorts) return;
    
    setIsLoadingShorts(true);
    setShortsSuggestions([]);
    log('action', `Analyse IA pour shorts de ${selectedFile.name}...`);
    
    try {
      const response = await fetch('/api/generate-shorts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_name: selectedFile.folder || selectedFile.name,
          segments: transcription.segments
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setShortsSuggestions(data.shorts || []);
        
        if (data.shorts?.length > 0) {
          log('success', `${data.shorts.length} short(s) suggéré(s) par l'IA`);
        } else {
          log('warning', 'Aucun moment intéressant trouvé pour un short');
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        log('error', `Erreur: ${errorData.detail || 'Impossible de générer les suggestions'}`);
      }
    } catch (err: any) {
      log('error', `Erreur: ${err.message}`);
    } finally {
      setIsLoadingShorts(false);
    }
  };

  // Créer un short à partir d'une suggestion
  const createShort = async (suggestion: ShortSuggestion, index: number) => {
    if (!selectedFile || creatingShortIndex !== null) return;
    
    setCreatingShortIndex(index);
    log('action', `Création du short "${suggestion.title}"...`);
    log('info', `Durée: ${suggestion.duration.toFixed(1)}s (${suggestion.timestamp_start} → ${suggestion.timestamp_end})`);
    
    try {
      const response = await fetch('/api/create-short', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_name: selectedFile.folder || selectedFile.name,
          start: suggestion.start,
          end: suggestion.end,
          title: suggestion.title
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        log('success', `Short créé: ${data.filename}`);
        log('info', `Format: ${data.dimensions} (9:16)`);
        
        // Ajouter à la liste des shorts créés
        setCreatedShorts(prev => [...prev, data.path]);
        
        // Rafraîchir la liste des fichiers pour mettre à jour l'arborescence
        fetchFiles();
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        log('error', `Erreur: ${errorData.detail || 'Impossible de créer le short'}`);
      }
    } catch (err: any) {
      log('error', `Erreur: ${err.message}`);
    } finally {
      setCreatingShortIndex(null);
    }
  };

  // Prévisualiser un short dans le player
  const previewShort = (suggestion: ShortSuggestion) => {
    if (videoRef.current) {
      videoRef.current.currentTime = suggestion.start;
      videoRef.current.play();
      log('info', `Prévisualisation: ${suggestion.timestamp_start} → ${suggestion.timestamp_end}`);
    }
  };

  // Supprimer les silences de la vidéo
  const removeSilences = async () => {
    if (!selectedFile || isRemovingSilences) return;
    
    setIsRemovingSilences(true);
    log('action', `Suppression des silences de ${selectedFile.name}...`);
    
    try {
      // Log les zones rouges qu'on va couper
      log('info', `${detectedSilences.length} zone(s) rouge(s) à couper`);
      detectedSilences.forEach((s, i) => {
        log('info', `  🔴 ${i}: ${s.start.toFixed(2)}s → ${s.end.toFixed(2)}s`);
      });
      
      const response = await fetch('/api/remove-silences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          // Envoyer les zones ROUGES détectées = ce qui sera coupé
          detected_silences: detectedSilences,
          video_duration: videoDuration,
          silence_threshold: silenceThreshold,
          min_silence_duration: minSilenceDuration,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        log('success', `Silences supprimés ! Nouveau fichier: ${data.output_filename}`);
        log('info', `Durée originale: ${data.original_duration?.toFixed(1)}s → Nouvelle: ${data.new_duration?.toFixed(1)}s`);
        log('info', `${data.silences_removed || 0} silence(s) supprimé(s), ${data.time_saved?.toFixed(1)}s économisé(s)`);
        
        // Rafraîchir la liste des fichiers
        const newFilename = data.output_filename;
        const filesResponse = await fetch(`/api/files?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' },
        });
        
        if (filesResponse.ok) {
          const filesData = await filesResponse.json();
          const validFiles = (filesData.files || [])
            .filter((f: VideoFile) => f.name && f.url);
          setFiles(validFiles);
          
          // Charger directement le fichier nosilence.mp4 avec cache-busting
          const newFile = validFiles.find((f: VideoFile) => f.name === newFilename);
          if (newFile) {
            // Forcer le rechargement du fichier nosilence avec timestamp UNIQUE
            const uniqueId = `${Date.now()}_${Math.random().toString(36).substring(7)}`;
            const nosilenceUrl = `/output/${newFilename}/nosilence.mp4?nocache=${uniqueId}`;
            
            log('info', `🔄 Forçage rechargement: ${nosilenceUrl}`);
            
            // Réinitialiser complètement le player
            if (videoRef.current) {
              videoRef.current.pause();
              videoRef.current.removeAttribute('src');
              videoRef.current.load(); // Vider le buffer
            }
            
            setActiveVideoUrl('');
            setSelectedFile({ ...newFile, has_nosilence: true });
            setAudioWaveform([]);
            setDetectedSilences([]);
            
            // Charger la nouvelle URL après avoir vidé
            setTimeout(() => {
              setActiveVideoUrl(nosilenceUrl);
              if (videoRef.current) {
                videoRef.current.src = nosilenceUrl;
                videoRef.current.load();
              }
            }, 200);
            
            // Recharger la transcription mise à jour
            if (data.transcription_updated) {
              log('info', 'Rechargement de la transcription...');
              try {
                const transcriptionResponse = await fetch(`/output/${newFilename}/transcription.json?t=${Date.now()}`);
                if (transcriptionResponse.ok) {
                  const transcriptionData = await transcriptionResponse.json();
                  setTranscription(transcriptionData);
                  log('success', `Transcription mise à jour (${transcriptionData.segments?.length || 0} segments)`);
                }
              } catch (err) {
                log('warning', 'Transcription non disponible');
                setTranscription(null);
              }
            } else {
              setTranscription(null);
            }
            
            log('info', `Fichier nosilence.mp4 chargé (${data.new_duration?.toFixed(1)}s)`);
          }
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        log('error', `Erreur: ${errorData.detail || 'Impossible de supprimer les silences'}`);
      }
    } catch (err: any) {
      console.error('Error removing silences:', err);
      log('error', `Erreur: ${err.message || 'Erreur inconnue'}`);
    } finally {
      setIsRemovingSilences(false);
    }
  };

  const fetchFiles = async () => {
    setLoading(true);
    log('action', 'Chargement des fichiers...');
    try {
      // Forcer le non-cache avec timestamp et headers
      const response = await fetch(`/api/files?t=${Date.now()}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('[FileList] Fichiers reçus:', data.files);
        const validFiles = (data.files || [])
          .filter((f: VideoFile) => f.name && f.url);
        console.log('[FileList] Vidéos trouvées:', validFiles.map((f: VideoFile) => f.name));
        setFiles(validFiles);
        log('success', `${validFiles.length} fichier(s) trouve(s)`);
        
        // Si le fichier sélectionné n'existe plus, le désélectionner
        if (selectedFile && !validFiles.find((f: VideoFile) => f.name === selectedFile.name)) {
          setSelectedFile(null);
          log('warning', 'Fichier selectionne n\'existe plus');
        }
      } else {
        log('error', `Erreur HTTP: ${response.status}`);
      }
    } catch (err) {
      console.error('Error fetching files:', err);
      log('error', 'Erreur chargement fichiers');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchFiles();
    // Pas de polling automatique - rafraîchissement manuel uniquement
  }, []);

  // Écouter les commandes du terminal
  useEffect(() => {
    const handleCommand = async (event: CustomEvent<{ command: string }>) => {
      if (event.detail.command === '/retranscript') {
        if (!selectedFile) {
          log('warning', 'Aucune vidéo sélectionnée pour retranscrire');
          return;
        }
        await retranscribeFile(selectedFile);
      } else if (event.detail.command === '/seo') {
        if (!selectedFile) {
          log('warning', 'Aucune vidéo sélectionnée pour optimiser le SEO');
          return;
        }
        if (!transcription || !transcription.text) {
          log('warning', 'Aucune transcription disponible. Utilisez /retranscript d\'abord.');
          return;
        }
        await optimizeSEO(selectedFile, transcription.text);
      }
    };

    const handler = handleCommand as unknown as EventListener;
    window.addEventListener('terminal-command', handler);
    return () => {
      window.removeEventListener('terminal-command', handler);
    };
  }, [selectedFile, transcription]);

  const retranscribeFile = async (file: VideoFile) => {
    log('action', `Retranscription de ${file.name}...`);
    try {
      log('info', 'Téléchargement de la vidéo...');
      const response = await fetch(file.url);
      const blob = await response.blob();
      log('info', `Vidéo téléchargée: ${(blob.size / 1024 / 1024).toFixed(2)} MB`);
      
      const formData = new FormData();
      formData.append('file', blob, file.name);
      formData.append('language', 'fr');

      log('info', 'Envoi au serveur pour transcription avec Groq Whisper...');
      
      const result = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (result.ok) {
        const data = await result.json();
        log('success', 'Transcription terminée avec Groq');
        
        if (data.text) {
          log('info', `Texte: ${data.text.substring(0, 200)}...`);
          log('info', `${data.segments?.length || 0} segment(s) trouvé(s)`);
          
          // Afficher la transcription avec segments
          setTranscription({
            filename: file.name,
            text: data.text,
            segments: data.segments || [],
            seo: data.seo || undefined
          });
          
          log('success', `Transcription sauvegardée pour ${file.name}`);
          
          if (data.seo) {
            log('info', 'Métadonnées SEO générées');
          }
        } else {
          log('warning', 'Transcription vide');
        }
      } else {
        const errorData = await result.json().catch(() => ({ detail: 'Erreur serveur' }));
        log('error', `Erreur transcription: ${errorData.detail || 'Erreur inconnue'}`);
      }
    } catch (err: any) {
      console.error('Error retranscribing:', err);
      log('error', `Erreur retranscription: ${err.message || 'Erreur inconnue'}`);
    }
  };

  const optimizeSEO = async (file: VideoFile, transcriptText: string) => {
    log('action', `Optimisation SEO pour ${file.name}...`);
    try {
      log('info', 'Génération métadonnées SEO optimisées avec OpenRouter...');
      
      // Inclure les segments si disponibles pour générer les chapitres avec timestamps réels
      const segments = transcription?.segments || [];
      if (segments.length > 0) {
        log('info', `${segments.length} segments disponibles pour chapitrage avec timestamps réels`);
      }
      
      const response = await fetch('/api/optimize-seo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          transcript: transcriptText,
          language: 'fr',
          segments: segments
        }),
      });

      if (response.ok) {
        const data = await response.json();
        log('success', 'Métadonnées SEO optimisées générées');
        
        if (data.seo) {
          // Mettre à jour la transcription avec les nouvelles métadonnées SEO
          setTranscription(prev => prev ? {
            ...prev,
            seo: data.seo
          } : null);
          
          log('info', `Titre: ${data.seo.title}`);
          log('info', `Description: ${data.seo.description.length} caractères`);
          log('info', `${data.seo.keywords?.length || 0} mots-clés générés`);
          log('info', `${data.seo.hashtags?.length || 0} hashtags générés`);
          if (data.seo.chapters && data.seo.chapters.length > 0) {
            log('info', `${data.seo.chapters.length} chapitres générés avec timestamps réels`);
          }
          log('success', 'Métadonnées SEO mises à jour');
        } else {
          log('warning', 'Aucune métadonnée SEO générée');
        }
      } else {
        const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
        const errorMessage = errorData.detail || 'Erreur inconnue';
        log('error', `Erreur optimisation SEO: ${errorMessage}`);
        
        // Messages d'aide selon le type d'erreur
        if (errorMessage.includes('Clé API')) {
          log('info', 'Vérifiez que OPENROUTER_API_KEY est configurée dans le fichier .env');
        } else if (errorMessage.includes('SDK')) {
          log('info', 'Installez le SDK OpenAI: pip install openai');
        }
      }
    } catch (err: any) {
      console.error('Error optimizing SEO:', err);
      log('error', `Erreur optimisation SEO: ${err.message || 'Erreur inconnue'}`);
    }
  };

  // Charger automatiquement la transcription existante quand une vidéo est sélectionnée
  useEffect(() => {
    const loadExistingTranscription = async () => {
      if (!selectedFile) {
        setTranscription(null);
        return;
      }

      const backendUrl = '';
      
      // Déterminer le chemin du fichier de transcription
      let transcriptionUrl: string;
      if (selectedFile.folder) {
        // Nouveau format: dossier vidéo
        transcriptionUrl = `${backendUrl}/output/${selectedFile.folder}/transcription.json`;
      } else {
        // Ancien format: fichier standalone
        const baseName = selectedFile.name.replace(/\.(mp4|webm)$/i, '');
        transcriptionUrl = `${backendUrl}/output/${baseName}.json`;
      }
      
      try {
        // Charger la transcription depuis le fichier JSON (texte + segments)
        const jsonResponse = await fetch(transcriptionUrl);
        
        if (jsonResponse.ok) {
          const jsonData = await jsonResponse.json();
          log('info', `Transcription chargée depuis ${selectedFile.folder || selectedFile.name}`);
          log('success', `${jsonData.segments?.length || 0} segment(s) chargé(s)`);
          
          // Afficher la transcription avec segments et métadonnées SEO
          setTranscription({
            filename: selectedFile.name,
            text: jsonData.text || '',
            segments: jsonData.segments || [],
            seo: jsonData.seo || undefined
          });
          
          if (jsonData.seo) {
            log('info', 'Métadonnées SEO disponibles');
          }
        } else {
          // Pas de transcription existante, réinitialiser
          console.log(`[FileList] Transcription non trouvee: ${jsonResponse.status}`);
          setTranscription(null);
        }
      } catch (err: any) {
        // Si erreur, pas de transcription existante
        console.log('[FileList] Pas de transcription existante:', err.message);
        setTranscription(null);
      }
    };

    loadExistingTranscription();
  }, [selectedFile]);

  // Suivre le temps de la vidéo avec requestAnimationFrame pour un mouvement fluide
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let animationFrameId: number;
    let lastTime = 0;

    // Mise à jour fluide frame par frame avec requestAnimationFrame
    const updateTimeSmooth = () => {
      if (video && !video.paused && !video.ended) {
        // Mettre à jour seulement si le temps a changé (évite les re-renders inutiles)
        if (Math.abs(video.currentTime - lastTime) > 0.001) {
          lastTime = video.currentTime;
          setCurrentTime(video.currentTime);
        }
        animationFrameId = requestAnimationFrame(updateTimeSmooth);
      }
    };

    const handlePlay = () => {
      lastTime = video.currentTime;
      animationFrameId = requestAnimationFrame(updateTimeSmooth);
    };

    const handlePause = () => {
      cancelAnimationFrame(animationFrameId);
      setCurrentTime(video.currentTime);
    };

    const handleSeeked = () => {
      setCurrentTime(video.currentTime);
    };

    const updateDuration = () => setVideoDuration(video.duration);

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handlePause);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('loadedmetadata', updateDuration);
    video.addEventListener('durationchange', updateDuration);

    // Si la vidéo est déjà en lecture au montage
    if (!video.paused) {
      handlePlay();
    }

    return () => {
      cancelAnimationFrame(animationFrameId);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handlePause);
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('loadedmetadata', updateDuration);
      video.removeEventListener('durationchange', updateDuration);
    };
  }, [selectedFile]);

  // Analyser l'audio complet pour créer la waveform statique
  // Se déclenche quand selectedFile ou activeVideoUrl change
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !selectedFile) {
      setAudioWaveform([]);
      return;
    }

    // Analyser la vidéo actuellement affichée pour la waveform
    const folderName = selectedFile.folder || selectedFile.name;
    
    // Si on a une URL active (nosilence), analyser celle-ci
    // Sinon analyser original.mp4
    let urlToAnalyze: string;
    if (activeVideoUrl && activeVideoUrl.includes('nosilence')) {
      urlToAnalyze = `/output/${folderName}/nosilence.mp4`;
    } else {
      urlToAnalyze = `/output/${folderName}/original.mp4`;
    }
    const cleanUrl = urlToAnalyze;

    let cancelled = false;

    const analyzeAudioFile = async () => {
      try {
        log('action', `Analyse audio pour waveform (${cleanUrl.split('/').pop()})...`);
        
        // Charger le fichier vidéo
        const response = await fetch(cleanUrl);
        if (!response.ok) throw new Error('Impossible de charger la vidéo');
        
        const arrayBuffer = await response.arrayBuffer();
        
        // Créer un contexte audio pour décoder
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        
        // Décoder le fichier audio
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));
        
        if (cancelled) {
          audioContext.close();
          return;
        }

        // Attendre que la vidéo soit chargée pour obtenir sa durée réelle
        await new Promise<void>((resolve) => {
          if (video.readyState >= 1 && video.duration > 0) {
            resolve();
          } else {
            const handler = () => {
              if (video.duration > 0) {
                video.removeEventListener('loadedmetadata', handler);
                resolve();
              }
            };
            video.addEventListener('loadedmetadata', handler);
          }
        });

        if (cancelled) {
          audioContext.close();
          return;
        }

        // Utiliser la durée réelle de la vidéo, pas celle du buffer audio
        const videoDurationReal = video.duration || audioBuffer.duration;
        
        // Analyser chaque canal audio
        const channelData = audioBuffer.getChannelData(0); // Prendre le premier canal
        const sampleRate = audioBuffer.sampleRate;
        const audioDuration = audioBuffer.duration;
        
        // Nombre de barres à afficher (correspondant à la largeur de la timeline)
        const numBars = 400;
        
        const waveform: number[] = [];
        
        // Analyser chaque segment basé sur le temps réel de la vidéo
        for (let i = 0; i < numBars; i++) {
          // Calculer le temps correspondant à cette barre dans la vidéo
          const barStartTime = (i / numBars) * videoDurationReal;
          const barEndTime = ((i + 1) / numBars) * videoDurationReal;
          
          // Convertir le temps en indices de samples dans le buffer audio
          const audioStartSample = Math.floor((barStartTime / audioDuration) * channelData.length);
          const audioEndSample = Math.floor((barEndTime / audioDuration) * channelData.length);
          
          // Calculer l'amplitude RMS (Root Mean Square) pour ce segment
          let sumSquares = 0;
          let count = 0;
          
          for (let j = audioStartSample; j < audioEndSample && j < channelData.length; j++) {
            const sample = channelData[j];
            sumSquares += sample * sample;
            count++;
          }
          
          // RMS pour obtenir le niveau audio moyen
          const rms = count > 0 ? Math.sqrt(sumSquares / count) : 0;
          
          // Normaliser entre 0 et 1, avec amplification pour meilleure visibilité
          const normalized = Math.min(rms * 3, 1);
          waveform.push(normalized);
        }
        
        if (!cancelled) {
          setAudioWaveform(waveform);
          log('success', `Waveform generee: ${waveform.length} barres`);
        }
        
        audioContext.close();
      } catch (err) {
        console.error('[FileList] Erreur analyse audio:', err);
        if (!cancelled) {
          setAudioWaveform([]);
          log('warning', 'Impossible d\'analyser l\'audio (peut-etre pas d\'audio)');
        }
      }
    };

    // Attendre que la vidéo soit chargée avec métadonnées
    const handleLoadedMetadata = () => {
      if (video.duration && video.duration > 0) {
        analyzeAudioFile();
      }
    };

    if (video.readyState >= 1 && video.duration > 0) {
      analyzeAudioFile();
    } else {
      video.addEventListener('loadedmetadata', handleLoadedMetadata);
    }

    return () => {
      cancelled = true;
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, [selectedFile, activeVideoUrl]); // Regénérer si la vidéo change (original -> nosilence)

  // Détecter les silences à partir de la waveform
  useEffect(() => {
    if (audioWaveform.length === 0 || videoDuration === 0) {
      setDetectedSilences([]);
      return;
    }

    // Convertir le seuil dB en amplitude linéaire (approximation)
    // -40dB ≈ 0.01, -30dB ≈ 0.03, -20dB ≈ 0.1
    const thresholdLinear = Math.pow(10, silenceThreshold / 20);
    
    const silences: Array<{start: number; end: number}> = [];
    let silenceStart: number | null = null;
    
    const barDuration = videoDuration / audioWaveform.length;
    
    for (let i = 0; i < audioWaveform.length; i++) {
      const amplitude = audioWaveform[i];
      const time = (i / audioWaveform.length) * videoDuration;
      
      if (amplitude < thresholdLinear) {
        // Début d'un silence potentiel
        if (silenceStart === null) {
          silenceStart = time;
        }
      } else {
        // Fin d'un silence
        if (silenceStart !== null) {
          const silenceDuration = time - silenceStart;
          if (silenceDuration >= minSilenceDuration) {
            silences.push({ start: silenceStart, end: time });
          }
          silenceStart = null;
        }
      }
    }
    
    // Si la vidéo se termine par un silence
    if (silenceStart !== null) {
      const silenceDuration = videoDuration - silenceStart;
      if (silenceDuration >= minSilenceDuration) {
        silences.push({ start: silenceStart, end: videoDuration });
      }
    }
    
    setDetectedSilences(silences);
  }, [audioWaveform, videoDuration, silenceThreshold, minSilenceDuration]);

  const deleteFile = async (filename: string) => {
    log('action', `Suppression de ${filename}...`);
    try {
      const response = await fetch(`/api/files/${filename}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setFiles(files.filter(f => f.name !== filename));
        if (selectedFile?.name === filename) {
          setSelectedFile(null);
        }
        log('success', `${filename} supprime`);
      }
    } catch (err) {
      console.error('Error deleting file:', err);
      log('error', 'Erreur suppression');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex flex-col h-full overflow-hidden bg-dark-950">
      {/* Layout style CapCut - 3 colonnes avec timeline en bas */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Left Panel - Liste des fichiers */}
        <div className="w-64 xl:w-80 shrink-0 bg-dark-900 border-r border-dark-800 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-dark-800 shrink-0">
            <h2 className="text-lg font-semibold text-white mb-4">Fichiers</h2>
            <div className="flex gap-2">
              <button className="flex-1 px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium">
                Importer
              </button>
              <button className="flex-1 px-3 py-2 bg-dark-800 text-dark-400 rounded-lg text-sm font-medium hover:bg-dark-700">
                Enregistrer
            </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 flex-1">
              <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-12 flex-1 flex flex-col items-center justify-center px-4">
              <Video className="w-16 h-16 text-dark-600 mx-auto mb-4" />
              <p className="text-dark-400">Aucune video pour le moment</p>
              <p className="text-dark-500 text-sm mt-2">Enregistrez votre premiere video!</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-dark-400 uppercase">Projets vidéo</span>
                <button
                  onClick={fetchFiles}
                  className="p-1 rounded hover:bg-dark-800 text-dark-400 hover:text-white transition-all"
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
              </div>
              <div className="space-y-1">
              {files.map((file) => (
                  <div key={file.name} className="select-none">
                    {/* Dossier principal */}
                    <div
                      onClick={() => {
                        setSelectedFile(file);
                        // Définir l'URL par défaut (nosilence si disponible, sinon original)
                        setActiveVideoUrl(file.url);
                      }}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-all ${
                    selectedFile?.name === file.name
                          ? 'bg-primary-600/20 text-primary-400'
                          : 'hover:bg-dark-800/50 text-dark-300'
                      }`}
                    >
                      {selectedFile?.name === file.name ? (
                        <FolderOpen className="w-4 h-4 text-primary-400 shrink-0" />
                      ) : (
                        <Folder className="w-4 h-4 text-yellow-500 shrink-0" />
                      )}
                      <span className="text-xs font-medium truncate flex-1">
                        {file.folder || file.name}
                      </span>
                      <ChevronRight className={`w-3 h-3 transition-transform ${selectedFile?.name === file.name ? 'rotate-90' : ''}`} />
                  </div>
                  
                    {/* Contenu du dossier (affiché si sélectionné) */}
                    {selectedFile?.name === file.name && (
                      <div className="ml-4 mt-1 space-y-0.5 border-l border-dark-700 pl-2">
                        {/* original.mp4 */}
                        {file.has_original && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = file.folder 
                                ? `/output/${file.folder}/original.mp4`
                                : file.url;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de original.mp4');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('original.mp4')
                                ? 'bg-blue-500/20 text-blue-400'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-blue-400" />
                            <span>original.mp4</span>
                            {activeVideoUrl?.includes('original.mp4') && (
                              <span className="text-blue-400 text-[10px]">● actif</span>
                            )}
                  </div>
                        )}
                        
                        {/* nosilence.mp4 */}
                        {file.has_nosilence && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = file.folder 
                                ? `/output/${file.folder}/nosilence.mp4`
                                : file.url;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de nosilence.mp4');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('nosilence.mp4')
                                ? 'bg-green-500/20 text-green-400'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-green-400" />
                            <span>nosilence.mp4</span>
                            {activeVideoUrl?.includes('nosilence.mp4') && (
                              <span className="text-green-400 text-[10px]">● actif</span>
                            )}
                          </div>
                        )}
                        
                        {/* screen.mp4 */}
                        {file.has_screen && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = `/output/${file.folder || file.name}/screen.mp4`;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de screen.mp4 (écran)');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('screen.mp4') && !activeVideoUrl?.includes('screen_nosilence')
                                ? 'bg-purple-500/20 text-purple-400'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-purple-400" />
                            <span>screen.mp4</span>
                            {activeVideoUrl?.includes('screen.mp4') && !activeVideoUrl?.includes('screen_nosilence') && (
                              <span className="text-purple-400 text-[10px]">● actif</span>
                            )}
                          </div>
                        )}
                        
                        {/* screen_nosilence.mp4 */}
                        {file.has_screen_nosilence && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = `/output/${file.folder || file.name}/screen_nosilence.mp4`;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de screen_nosilence.mp4 (écran sans silences)');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('screen_nosilence.mp4')
                                ? 'bg-purple-500/20 text-purple-300'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-purple-300" />
                            <span>screen_nosilence.mp4</span>
                            {activeVideoUrl?.includes('screen_nosilence.mp4') && (
                              <span className="text-purple-300 text-[10px]">● actif</span>
                            )}
                          </div>
                        )}
                        
                        {/* webcam.mp4 */}
                        {file.has_webcam && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = `/output/${file.folder || file.name}/webcam.mp4`;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de webcam.mp4 (caméra)');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('webcam.mp4') && !activeVideoUrl?.includes('webcam_nosilence')
                                ? 'bg-pink-500/20 text-pink-400'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-pink-400" />
                            <span>webcam.mp4</span>
                            {activeVideoUrl?.includes('webcam.mp4') && !activeVideoUrl?.includes('webcam_nosilence') && (
                              <span className="text-pink-400 text-[10px]">● actif</span>
                            )}
                          </div>
                        )}
                        
                        {/* webcam_nosilence.mp4 */}
                        {file.has_webcam_nosilence && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              const url = `/output/${file.folder || file.name}/webcam_nosilence.mp4`;
                              setActiveVideoUrl(url);
                              log('info', 'Chargement de webcam_nosilence.mp4 (caméra sans silences)');
                            }}
                            className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                              activeVideoUrl?.includes('webcam_nosilence.mp4')
                                ? 'bg-pink-500/20 text-pink-300'
                                : 'text-dark-400 hover:bg-dark-800/50 hover:text-white'
                            }`}
                          >
                            <FileVideo className="w-3 h-3 text-pink-300" />
                            <span>webcam_nosilence.mp4</span>
                            {activeVideoUrl?.includes('webcam_nosilence.mp4') && (
                              <span className="text-pink-300 text-[10px]">● actif</span>
                            )}
                          </div>
                        )}
                        
                        {/* transcription.json */}
                        {file.has_transcription && (
                          <div className="flex items-center gap-2 px-2 py-1 text-dark-400 text-xs">
                            <FileJson className="w-3 h-3 text-orange-400" />
                            <span>transcription.json</span>
                            <Check className="w-3 h-3 text-green-500" />
                          </div>
                        )}
                        
                        {/* Dossier shorts */}
                        {file.has_shorts && file.shorts && file.shorts.length > 0 && (
                          <div className="mt-1 border-t border-dark-800/50 pt-1">
                            <div className="flex items-center gap-2 px-2 py-1 text-purple-400 text-xs">
                              <Film className="w-3 h-3" />
                              <span>shorts/</span>
                              <span className="text-purple-300 bg-purple-500/20 px-1.5 py-0.5 rounded text-[10px]">
                                {file.shorts.length}
                              </span>
                            </div>
                            {/* Liste des shorts */}
                            <div className="ml-4 space-y-0.5">
                              {file.shorts.map((short, idx) => (
                                <div
                                  key={idx}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveVideoUrl(short.path);
                                    log('info', `Lecture du short: ${short.name}`);
                                  }}
                                  className={`flex items-center gap-2 px-2 py-1 text-xs cursor-pointer rounded transition-all ${
                                    activeVideoUrl?.includes(short.name)
                                      ? 'bg-purple-500/20 text-purple-300'
                                      : 'text-dark-400 hover:bg-purple-500/10 hover:text-purple-300'
                                  }`}
                                >
                                  <FileVideo className="w-3 h-3 text-purple-400" />
                                  <span className="truncate flex-1">{short.name}</span>
                                  <span className="text-[10px] text-dark-500">
                                    {(short.size / 1024 / 1024).toFixed(1)}MB
                                  </span>
                                  {activeVideoUrl?.includes(short.name) && (
                                    <span className="text-purple-400 text-[10px]">● actif</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Info fichier */}
                        <div className="flex items-center gap-2 px-2 py-1 text-dark-500 text-[10px] mt-1">
                          <span>{formatSize(file.size)}</span>
                          <span>•</span>
                          <span>{formatDate(file.created)}</span>
                        </div>
                        
                        {/* Bouton supprimer */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                            if (confirm(`Supprimer ${file.name} et tout son contenu ?`)) {
                        deleteFile(file.name);
                            }
                      }}
                          className="flex items-center gap-2 px-2 py-1 text-red-400 hover:text-red-300 text-xs mt-1 hover:bg-red-500/10 rounded w-full"
                    >
                          <Trash2 className="w-3 h-3" />
                          <span>Supprimer le projet</span>
                    </button>
                  </div>
                    )}
                </div>
              ))}
              </div>
            </div>
          )}
          </div>

        {/* Center Panel - Preview vidéo */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden bg-dark-950">
          {selectedFile ? (
            <>
              {/* Toolbar au-dessus du player */}
              <div className="shrink-0 bg-dark-900 border-b border-dark-800 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white font-medium truncate max-w-xs">
                    {selectedFile.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {/* Bouton générer shorts */}
                  {selectedFile?.has_screen_nosilence && selectedFile?.has_webcam_nosilence && transcription?.segments && (
                    <button
                      onClick={() => {
                        setShowShortsPanel(!showShortsPanel);
                        if (!showShortsPanel && shortsSuggestions.length === 0) {
                          generateShortsSuggestions();
                        }
                      }}
                      disabled={isLoadingShorts}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        showShortsPanel
                          ? 'bg-purple-600 text-white'
                          : 'bg-dark-800 hover:bg-purple-600 text-white hover:text-white'
                      }`}
                      title="Générer des shorts 9:16"
                    >
                      {isLoadingShorts ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Film className="w-4 h-4" />
                      )}
                      <span>Short</span>
                    </button>
                  )}
                  
                  {/* Bouton repositionner webcam */}
                  {selectedFile?.has_screen_nosilence && selectedFile?.has_webcam_nosilence && (
            <button
                      onClick={() => setShowWebcamReposition(!showWebcamReposition)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                        showWebcamReposition
                          ? 'bg-pink-600 text-white'
                          : 'bg-dark-800 hover:bg-pink-600 text-white hover:text-white'
                      }`}
                      title="Repositionner la webcam"
                    >
                      <Camera className="w-4 h-4" />
                      <span>Webcam</span>
                    </button>
                  )}
                  
                  {/* Bouton supprimer les silences */}
                  <button
                    onClick={removeSilences}
                    disabled={isRemovingSilences}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      isRemovingSilences
                        ? 'bg-dark-700 text-dark-400 cursor-not-allowed'
                        : 'bg-dark-800 hover:bg-primary-600 text-white hover:text-white'
                    }`}
                    title="Supprimer les silences de la vidéo"
                  >
                    {isRemovingSilences ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <VolumeX className="w-4 h-4" />
                    )}
                    <span>{isRemovingSilences ? 'Traitement...' : 'Supprimer silences'}</span>
                  </button>
                  
                  {/* Bouton paramètres silence */}
                  <button
                    onClick={() => setShowSilenceSettings(!showSilenceSettings)}
                    className={`p-2 rounded-lg transition-all ${
                      showSilenceSettings 
                        ? 'bg-primary-600 text-white' 
                        : 'bg-dark-800 text-dark-300 hover:text-white'
                    }`}
                    title="Paramètres de détection"
                  >
                    <Settings2 className="w-4 h-4" />
                  </button>
                  
                  {/* Indicateur silences détectés */}
                  {detectedSilences.length > 0 && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-red-500/20 rounded-lg">
                      <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      <span className="text-xs text-red-400 font-medium">
                        {detectedSilences.length} silence{detectedSilences.length > 1 ? 's' : ''} ({detectedSilences.reduce((acc, s) => acc + (s.end - s.start), 0).toFixed(1)}s)
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Panneau paramètres de silence */}
              {showSilenceSettings && (
                <div className="shrink-0 bg-dark-850 border-b border-dark-800 px-4 py-3">
                  <div className="flex items-center gap-6">
                    {/* Slider seuil de silence */}
                    <div className="flex-1 max-w-xs">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs text-dark-400 flex items-center gap-1">
                          <Volume2 className="w-3 h-3" />
                          Seuil de silence
                        </label>
                        <span className="text-xs text-primary-400 font-mono">{silenceThreshold} dB</span>
                      </div>
                      <input
                        type="range"
                        min="-60"
                        max="-20"
                        step="5"
                        value={silenceThreshold}
                        onChange={(e) => setSilenceThreshold(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                      />
                      <div className="flex justify-between text-[10px] text-dark-500 mt-0.5">
                        <span>-60dB (sensible)</span>
                        <span>-20dB (strict)</span>
                      </div>
                    </div>
                    
                    {/* Slider durée minimum */}
                    <div className="flex-1 max-w-xs">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs text-dark-400">Durée minimum</label>
                        <span className="text-xs text-primary-400 font-mono">{minSilenceDuration.toFixed(1)}s</span>
                      </div>
                      <input
                        type="range"
                        min="0.1"
                        max="2"
                        step="0.1"
                        value={minSilenceDuration}
                        onChange={(e) => setMinSilenceDuration(parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                      />
                      <div className="flex justify-between text-[10px] text-dark-500 mt-0.5">
                        <span>0.1s</span>
                        <span>2.0s</span>
                      </div>
                    </div>
                    
                    {/* Preview */}
                    <div className="text-center">
                      <div className="text-xs text-dark-400 mb-1">Aperçu</div>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-6 bg-dark-800 rounded overflow-hidden relative">
                          {/* Mini waveform preview */}
                          <div className="absolute inset-0 flex items-end">
                            {audioWaveform.slice(0, 32).map((amp, i) => {
                              const thresholdLinear = Math.pow(10, silenceThreshold / 20);
                              const isSilent = amp < thresholdLinear;
                              return (
                                <div
                                  key={i}
                                  className={`flex-1 ${isSilent ? 'bg-red-500/50' : 'bg-primary-400/70'}`}
                                  style={{ height: `${Math.max(amp * 100, 5)}%` }}
                                />
                              );
                            })}
                          </div>
                        </div>
                        <div className="text-[10px] text-dark-500">
                          <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-red-500/50 rounded-sm" />
                            <span>Silence</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-primary-400/70 rounded-sm" />
                            <span>Audio</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Panneau repositionnement webcam */}
              {showWebcamReposition && selectedFile?.has_screen_nosilence && selectedFile?.has_webcam_nosilence && (
                <div className="shrink-0 bg-gradient-to-r from-pink-900/30 to-dark-900 border-b border-pink-500/30 px-4 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Taille */}
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-pink-300">Taille:</label>
                        <input
                          type="range"
                          min="100"
                          max="600"
                          step="10"
                          value={webcamSize}
                          onChange={(e) => setWebcamSize(parseInt(e.target.value))}
                          className="w-20 h-1.5 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-pink-500"
                        />
                        <span className="text-xs text-pink-400 font-mono w-10">{webcamSize}</span>
                      </div>
                      
                      {/* Épaisseur du bord */}
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-pink-300">Bord:</label>
                        <input
                          type="range"
                          min="0"
                          max="20"
                          step="1"
                          value={borderThickness}
                          onChange={(e) => setBorderThickness(parseInt(e.target.value))}
                          className="w-14 h-1.5 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-pink-500"
                        />
                        <span className="text-xs text-pink-400 font-mono w-6">{borderThickness}</span>
                      </div>
                      
                      {/* Couleur du bord */}
                      <div className="flex items-center gap-1">
                        <input
                          type="color"
                          value={borderColor}
                          onChange={(e) => setBorderColor(e.target.value)}
                          className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                        />
                      </div>
                      
                      {/* Forme */}
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setWebcamShape('circle')}
                          className={`px-2 py-1 rounded text-xs transition-all ${
                            webcamShape === 'circle'
                              ? 'bg-pink-600 text-white'
                              : 'bg-dark-700 text-dark-400 hover:text-white'
                          }`}
                        >
                          ●
                        </button>
                        <button
                          onClick={() => setWebcamShape('rectangle')}
                          className={`px-2 py-1 rounded text-xs transition-all ${
                            webcamShape === 'rectangle'
                              ? 'bg-pink-600 text-white'
                              : 'bg-dark-700 text-dark-400 hover:text-white'
                          }`}
                        >
                          ▢
                        </button>
                      </div>
                      
                      {/* Position affichée */}
                      <div className="text-xs text-dark-400">
                        <span className="text-pink-400 font-mono">{webcamX}, {webcamY}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {/* Bouton annuler */}
                      <button
                        onClick={() => setShowWebcamReposition(false)}
                        className="px-3 py-1.5 rounded-lg text-xs bg-dark-700 text-dark-300 hover:text-white transition-all"
                      >
                        Annuler
                      </button>
                      
                      {/* Bouton appliquer */}
                      <button
                        onClick={repositionWebcam}
                        disabled={isRepositioning}
                        className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                          isRepositioning
                            ? 'bg-dark-700 text-dark-400 cursor-not-allowed'
                            : 'bg-pink-600 hover:bg-pink-500 text-white'
                        }`}
                      >
                        {isRepositioning ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Check className="w-4 h-4" />
                        )}
                        <span>{isRepositioning ? 'Fusion...' : 'Appliquer'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Panneau shorts */}
              {showShortsPanel && (
                <div className="shrink-0 bg-gradient-to-r from-purple-900/30 to-dark-900 border-b border-purple-500/30 px-4 py-3 max-h-64 overflow-y-auto">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Film className="w-4 h-4 text-purple-400" />
                      <span className="text-sm font-medium text-white">Shorts suggérés</span>
                      {shortsSuggestions.length > 0 && (
                        <span className="text-xs text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded-full">
                          {shortsSuggestions.length} suggestion{shortsSuggestions.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={generateShortsSuggestions}
                        disabled={isLoadingShorts}
                        className="flex items-center gap-1.5 px-2 py-1 text-xs rounded bg-purple-600/20 text-purple-300 hover:bg-purple-600/40 transition-all"
                      >
                        {isLoadingShorts ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Sparkles className="w-3 h-3" />
                        )}
                        Régénérer
                      </button>
                      <button
                        onClick={() => setShowShortsPanel(false)}
                        className="p-1 rounded hover:bg-dark-700 text-dark-400 hover:text-white transition-all"
            >
              <X className="w-4 h-4" />
            </button>
                    </div>
                  </div>
                  
                  {isLoadingShorts ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="flex items-center gap-3 text-purple-400">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span className="text-sm">Analyse IA en cours...</span>
                      </div>
                    </div>
                  ) : shortsSuggestions.length === 0 ? (
                    <div className="text-center py-6 text-dark-400 text-sm">
                      Cliquez sur "Régénérer" pour analyser la vidéo.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {shortsSuggestions.map((suggestion, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 p-2 bg-dark-800/50 rounded-lg border border-purple-500/20 hover:border-purple-500/40 transition-all"
                        >
                          {/* Aperçu format 9:16 */}
                          <div className="shrink-0 w-12 h-20 bg-gradient-to-b from-purple-600/30 to-pink-600/30 rounded flex flex-col items-center justify-center border border-purple-500/30">
                            <div className="w-8 h-4 bg-dark-700 rounded-sm mb-0.5 flex items-center justify-center">
                              <span className="text-[6px] text-purple-300">ÉCRAN</span>
                            </div>
                            <div className="w-8 h-4 bg-pink-600/50 rounded-sm flex items-center justify-center">
                              <span className="text-[6px] text-pink-200">CAM</span>
                            </div>
                          </div>
                          
                          {/* Infos */}
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium text-white truncate">{suggestion.title}</h4>
                            <p className="text-xs text-dark-400 truncate mt-0.5">{suggestion.description}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-purple-400 font-mono">
                                {suggestion.timestamp_start} → {suggestion.timestamp_end}
                              </span>
                              <span className="text-xs text-dark-500">•</span>
                              <span className="text-xs text-purple-300">{suggestion.duration.toFixed(1)}s</span>
                            </div>
                          </div>
                          
                          {/* Actions */}
                          <div className="shrink-0 flex items-center gap-1.5">
                            {/* Prévisualiser */}
                            <button
                              onClick={() => previewShort(suggestion)}
                              className="p-1.5 rounded bg-dark-700 text-dark-300 hover:text-white hover:bg-dark-600 transition-all"
                              title="Prévisualiser"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                            
                            {/* Créer le short */}
                            <button
                              onClick={() => createShort(suggestion, index)}
                              disabled={creatingShortIndex !== null}
                              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-all ${
                                creatingShortIndex === index
                                  ? 'bg-purple-600/50 text-purple-200 cursor-not-allowed'
                                  : 'bg-purple-600 text-white hover:bg-purple-500'
                              }`}
                            >
                              {creatingShortIndex === index ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Download className="w-3.5 h-3.5" />
                              )}
                              {creatingShortIndex === index ? 'Création...' : 'Créer'}
                            </button>
        </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Liste des shorts créés */}
                  {createdShorts.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-purple-500/20">
                      <div className="flex items-center gap-2 mb-2">
                        <Check className="w-3.5 h-3.5 text-green-400" />
                        <span className="text-xs font-medium text-green-400">
                          {createdShorts.length} short{createdShorts.length > 1 ? 's' : ''} créé{createdShorts.length > 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {createdShorts.map((path, index) => (
                          <a
                            key={index}
                            href={path}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1.5 px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-all"
                          >
                            <FileVideo className="w-3 h-3" />
                            <span>Short {index + 1}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Video Preview - Grande zone centrale */}
              <div className="flex-1 min-h-0 bg-dark-900 flex items-center justify-center p-4">
                {showWebcamReposition && selectedFile?.has_screen_nosilence && selectedFile?.has_webcam_nosilence ? (
                  /* Mode prévisualisation webcam avec drag & drop */
                  <div 
                    ref={previewContainerRef}
                    className="relative w-full max-w-full max-h-full select-none"
                    style={{ aspectRatio: '16/9' }}
                    onMouseMove={(e) => {
                      if (!isDraggingWebcam || !previewContainerRef.current) return;
                      const rect = previewContainerRef.current.getBoundingClientRect();
                      const scaleX = 1920 / rect.width;
                      const scaleY = 1080 / rect.height;
                      const newX = Math.max(0, Math.min(1920 - webcamSize, (e.clientX - rect.left - dragOffset.x) * scaleX));
                      const newY = Math.max(0, Math.min(1080 - webcamSize, (e.clientY - rect.top - dragOffset.y) * scaleY));
                      setWebcamX(Math.round(newX));
                      setWebcamY(Math.round(newY));
                    }}
                    onMouseUp={() => setIsDraggingWebcam(false)}
                    onMouseLeave={() => setIsDraggingWebcam(false)}
                  >
                    {/* Vidéo écran en fond */}
              <video
                ref={videoRef}
                      src={`/output/${selectedFile.folder || selectedFile.name}/screen_nosilence.mp4`}
                      className="absolute inset-0 w-full h-full object-contain bg-black"
                      muted
                      loop
                      autoPlay
                      playsInline
                    />
                    
                    {/* Overlay webcam draggable */}
                    <div
                      className={`absolute cursor-move transition-shadow ${isDraggingWebcam ? 'ring-2 ring-white' : ''}`}
                      style={{
                        left: `${(webcamX / 1920) * 100}%`,
                        top: `${(webcamY / 1080) * 100}%`,
                        width: `${(webcamSize / 1920) * 100}%`,
                        height: `${(webcamSize / 1080) * 100}%`,
                        borderRadius: webcamShape === 'circle' ? '50%' : '8px',
                        overflow: 'hidden',
                        border: borderThickness > 0 ? `${borderThickness}px solid ${borderColor}` : 'none',
                      }}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        if (!previewContainerRef.current) return;
                        const rect = previewContainerRef.current.getBoundingClientRect();
                        const scaleX = 1920 / rect.width;
                        const scaleY = 1080 / rect.height;
                        const webcamScreenX = (webcamX / 1920) * rect.width;
                        const webcamScreenY = (webcamY / 1080) * rect.height;
                        setDragOffset({
                          x: (e.clientX - rect.left - webcamScreenX),
                          y: (e.clientY - rect.top - webcamScreenY)
                        });
                        setIsDraggingWebcam(true);
                      }}
                    >
                      <video
                        ref={webcamVideoRef}
                        src={`/output/${selectedFile.folder || selectedFile.name}/webcam_nosilence.mp4`}
                        className="w-full h-full object-cover"
                        muted
                        loop
                        autoPlay
                        playsInline
                      />
                    </div>
                    
                    {/* Indicateur de position */}
                    <div className="absolute bottom-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                      📍 X: {webcamX}px, Y: {webcamY}px | Taille: {webcamSize}px
                    </div>
                    
                    {/* Instructions */}
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-pink-600/90 text-white text-xs px-3 py-1.5 rounded-full">
                      🖱️ Glisse la webcam pour la repositionner
                    </div>
                  </div>
                ) : activeVideoUrl?.includes('/shorts/') ? (
                  /* Mode Short - Simulation téléphone */
                  <div className="h-full flex items-center justify-center py-4">
                    <div 
                      className="relative bg-gray-900 rounded-[3rem] p-2 shadow-2xl"
                      style={{ 
                        height: '100%',
                        maxHeight: '85vh',
                        aspectRatio: '9/19.5',
                      }}
                    >
                      {/* Encoche du téléphone */}
                      <div className="absolute top-4 left-1/2 -translate-x-1/2 w-24 h-6 bg-black rounded-full z-10" />
                      
                      {/* Écran du téléphone */}
                      <div 
                        className="relative w-full h-full bg-black rounded-[2.5rem] overflow-hidden"
                      >
                        <video
                          ref={videoRef}
                          src={activeVideoUrl}
                controls
                          controlsList="nodownload"
                          preload="metadata"
                          className="w-full h-full object-cover"
                          style={{ 
                            backgroundColor: '#000',
                          }}
                          playsInline
                onError={(e) => {
                            console.error('[FileList] Erreur chargement video:', activeVideoUrl, e);
                            log('error', `Erreur chargement short`);
                          }}
                          onLoadStart={() => {
                            log('action', `⏳ Chargement short...`);
                          }}
                          onLoadedMetadata={() => {
                            const video = videoRef.current;
                            if (video) {
                              const fileName = activeVideoUrl.split('/').pop()?.split('?')[0] || 'short';
                              log('success', `📱 Short chargé: ${fileName} (${video.duration.toFixed(1)}s)`);
                              setVideoDuration(video.duration);
                            }
                          }}
                          onPlay={() => setIsPlaying(true)}
                          onPause={() => setIsPlaying(false)}
                          onEnded={() => setIsPlaying(false)}
                        />
                        
                        {/* Barre d'état simulée */}
                        <div className="absolute top-2 left-0 right-0 flex items-center justify-between px-8 text-white text-xs z-10 pointer-events-none">
                          <span className="font-medium">9:41</span>
                          <div className="flex items-center gap-1">
                            <div className="w-4 h-2 border border-white rounded-sm">
                              <div className="w-3/4 h-full bg-white rounded-sm" />
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      {/* Bouton home */}
                      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-28 h-1 bg-gray-600 rounded-full" />
                    </div>
                  </div>
                ) : (
                  /* Mode normal 16:9 */
                  <div className="w-full max-w-full max-h-full" style={{ aspectRatio: '16/9' }}>
                    <video
                      ref={videoRef}
                      src={activeVideoUrl || selectedFile.url}
                      controls
                      controlsList="nodownload"
                      preload="metadata"
                      className="w-full h-full"
                      style={{ 
                        aspectRatio: '16/9',
                        backgroundColor: '#000',
                        display: 'block'
                      }}
                      playsInline
                      onError={(e) => {
                        console.error('[FileList] Erreur chargement video:', activeVideoUrl || selectedFile.url, e);
                  log('error', `Erreur chargement: ${selectedFile.name}`);
                }}
                onLoadStart={() => {
                        const url = activeVideoUrl || selectedFile.url;
                        log('action', `⏳ Chargement: ${url.split('/').slice(-2).join('/')}`);
                      }}
                      onLoadedMetadata={() => {
                        const video = videoRef.current;
                        if (video) {
                          const currentSrc = video.currentSrc || video.src;
                          const fileName = currentSrc.split('/').pop()?.split('?')[0] || 'unknown';
                          log('success', `📹 Chargé: ${fileName} (${video.duration.toFixed(1)}s)`);
                          setVideoDuration(video.duration);
                          video.playbackRate = 1.0;
                        }
                      }}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => setIsPlaying(false)}
                    />
                  </div>
                )}
            </div>

              {/* Timeline en bas - masquée pour les shorts */}
              {videoRef.current && !activeVideoUrl?.includes('/shorts/') && (
                <div className="h-40 shrink-0 bg-dark-900 border-t border-dark-800 p-4">
                  {/* Contrôles de lecture */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {/* Bouton frame précédente */}
                      <button
                        onClick={prevFrame}
                        className="p-2 rounded-lg bg-dark-800 hover:bg-dark-700 text-white transition-all"
                        title="Frame précédente (←)"
                      >
                        <SkipBack className="w-4 h-4" />
                      </button>
                      
                      {/* Bouton Play/Pause */}
                      <button
                        onClick={togglePlayPause}
                        className="p-3 rounded-lg bg-primary-600 hover:bg-primary-500 text-white transition-all"
                        title="Lecture/Pause (Espace)"
                      >
                        {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                      </button>
                      
                      {/* Bouton frame suivante */}
                      <button
                        onClick={nextFrame}
                        className="p-2 rounded-lg bg-dark-800 hover:bg-dark-700 text-white transition-all"
                        title="Frame suivante (→)"
                      >
                        <SkipForward className="w-4 h-4" />
                      </button>
                    </div>
                    
                    {/* Affichage du temps et des frames */}
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="text-sm text-white font-mono">
                          {formatTimeWithFrames(currentTime)}
                    </span>
                        <span className="text-dark-400 font-mono text-sm"> / </span>
                        <span className="text-sm text-dark-400 font-mono">
                          {formatTimeWithFrames(videoDuration)}
                        </span>
                </div>
                      <div className="px-3 py-1 bg-dark-800 rounded-lg">
                        <span className="text-xs text-primary-400 font-mono">
                          Frame {currentFrame} / {totalFrames}
                        </span>
                      </div>
                      {/* Sélecteur de framerate */}
                      <select
                        value={frameRate}
                        onChange={(e) => setFrameRate(Number(e.target.value))}
                        className="px-2 py-1 bg-dark-800 hover:bg-dark-700 border border-dark-700 rounded text-xs text-white font-mono cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary-500"
                        title="Sélectionner le framerate"
                      >
                        <option value={24}>24 fps</option>
                        <option value={25}>25 fps</option>
                        <option value={30}>30 fps</option>
                        <option value={50}>50 fps</option>
                        <option value={60}>60 fps</option>
                        <option value={120}>120 fps</option>
                      </select>
                    </div>
                  </div>
                  
                  {/* Aide clavier */}
                  <div className="flex items-center gap-4 mb-2 text-xs text-dark-500">
                    <span><kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-dark-400">Espace</kbd> Play/Pause</span>
                    <span><kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-dark-400">←</kbd><kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-dark-400 ml-0.5">→</kbd> ±1 frame</span>
                    <span><kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-dark-400">↑</kbd><kbd className="px-1.5 py-0.5 bg-dark-800 rounded text-dark-400 ml-0.5">↓</kbd> ±1 sec</span>
                  </div>
                  
                  <div className="relative bg-dark-950 rounded-lg overflow-hidden h-12">
                    {/* Barre de progression - sans transition pour un mouvement fluide frame par frame */}
                  {videoDuration > 0 && (
                    <div
                        className="absolute top-0 left-0 w-0.5 bg-primary-500 z-20 pointer-events-none"
                      style={{
                        left: `${(currentTime / videoDuration) * 100}%`,
                          height: '100%',
                          willChange: 'left' // Optimisation GPU pour mouvement fluide
                      }}
                    >
                      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3 h-3 bg-primary-500 rounded-full -translate-y-1/2 border-2 border-dark-950" />
                    </div>
                  )}
                    
                    {/* Zones de silence détectées (en rouge) */}
                    {detectedSilences.length > 0 && videoDuration > 0 && (
                      <div className="absolute inset-0 z-5">
                        {detectedSilences.map((silence, index) => {
                          const silenceWidth = `${((silence.end - silence.start) / videoDuration) * 100}%`;
                          const silenceLeft = `${(silence.start / videoDuration) * 100}%`;
                          
                          return (
                            <div
                              key={`silence-${index}`}
                              className="absolute h-full bg-red-500/30 border-l border-r border-red-500/50"
                              style={{
                                left: silenceLeft,
                                width: silenceWidth,
                                minWidth: '1px'
                              }}
                              title={`Silence: ${silence.start.toFixed(2)}s → ${silence.end.toFixed(2)}s (${(silence.end - silence.start).toFixed(2)}s)`}
                            />
                          );
                        })}
                      </div>
                    )}
                  
                  {/* Segments de transcription */}
                  {transcription && transcription.segments.length > 0 && videoDuration > 0 && (
                      <div className="absolute inset-0">
                        {transcription.segments.map((segment, index) => {
                          const segmentWidth = `${((segment.end - segment.start) / videoDuration) * 100}%`;
                          const segmentLeft = `${(segment.start / videoDuration) * 100}%`;
                          
                          return (
                            <div
                              key={index}
                              onClick={() => {
                                if (videoRef.current) {
                                  videoRef.current.currentTime = segment.start;
                                  videoRef.current.play();
                                }
                              }}
                              className="absolute h-full cursor-pointer hover:bg-primary-500/20 transition-all border-r border-dark-700"
                              style={{
                                left: segmentLeft,
                                width: segmentWidth,
                                minWidth: '2px'
                              }}
                            />
                          );
                        })}
                    </div>
                  )}

                    {/* Waveform */}
                  {audioWaveform.length > 0 && videoDuration > 0 && (
                      <div className="absolute inset-0 flex items-end gap-0.5 px-0.5">
                        {audioWaveform.map((amplitude, index) => {
                          const barStartTime = (index / audioWaveform.length) * videoDuration;
                          const barEndTime = ((index + 1) / audioWaveform.length) * videoDuration;
                          const barLeft = `${(barStartTime / videoDuration) * 100}%`;
                          const barWidth = `${(1 / audioWaveform.length) * 100}%`;
                          const isActive = currentTime >= barStartTime && currentTime < barEndTime;
                          const barHeight = Math.max(amplitude * 100, 3);
                          
                          // Vérifier si cette barre est dans une zone de silence
                          const isInSilence = detectedSilences.some(
                            silence => barStartTime >= silence.start && barEndTime <= silence.end
                          );
                          
                          return (
                            <div
                              key={index}
                              className={`absolute rounded-t transition-colors ${
                                isActive 
                                  ? 'bg-white' 
                                  : isInSilence
                                    ? 'bg-red-500/70'
                                  : amplitude > 0.05 
                                    ? 'bg-primary-400/70' 
                                    : 'bg-dark-700/50'
                              }`}
                              style={{
                                left: barLeft,
                                width: barWidth,
                                height: `${barHeight}%`,
                                minHeight: '2px',
                                bottom: 0
                              }}
                            />
                          );
                        })}
                    </div>
                  )}
                </div>
              </div>
            )}
                  </>
                ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Video className="w-24 h-24 text-dark-600 mx-auto mb-4" />
                <p className="text-dark-400 text-lg">Sélectionnez une vidéo</p>
                <p className="text-dark-500 text-sm mt-2">Choisissez une vidéo dans le panneau de gauche</p>
            </div>
          </div>
        )}
      </div>

        {/* Right Panel - Transcription + Métadonnées SEO */}
        <div className="w-80 xl:w-96 shrink-0 bg-dark-900 border-l border-dark-800 flex flex-col overflow-hidden">
          {selectedFile && transcription ? (
            <div className="flex-1 overflow-y-auto">
              {/* Section Transcription */}
              <div className="border-b border-dark-800">
                <div className="p-4 border-b border-dark-800 shrink-0">
            <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary-400" />
                    <h2 className="text-lg font-semibold text-white">Transcription</h2>
              {transcription.segments.length > 0 && (
                <span className="text-xs text-dark-400">
                        ({transcription.segments.length} segments)
                </span>
              )}
            </div>
            </div>
                <div className="p-4 max-h-64 overflow-y-auto">
          {transcription.segments.length > 0 ? (
              <div className="space-y-2">
                {transcription.segments.map((segment, index) => (
                  <div
                    key={index}
                    onClick={() => {
                      if (videoRef.current) {
                        videoRef.current.currentTime = segment.start;
                        videoRef.current.play();
                        log('info', `Navigation vers ${formatTime(segment.start)}`);
                      }
                    }}
                          className="p-2 rounded-lg bg-dark-800/30 hover:bg-dark-800/50 cursor-pointer transition-all border border-transparent hover:border-primary-500/30"
                  >
                          <span className="text-xs text-primary-400 font-mono">
                            {formatTime(segment.start)}
                      </span>
                          <p className="text-white text-xs leading-relaxed mt-1">
                        {segment.text}
                      </p>
                  </div>
                ))}
            </div>
          ) : (
                    <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">
                {transcription.text}
              </p>
                  )}
                </div>
              </div>

              {/* Section Métadonnées YouTube */}
              {transcription.seo && (
                <div>
                  <div className="p-4 border-b border-dark-800 shrink-0">
                    <h2 className="text-lg font-semibold text-white">Métadonnées YouTube</h2>
                  </div>
                  <div className="p-4 space-y-4">
                    {/* Titre */}
                    {transcription.seo.title && (
                      <div>
                        <h3 className="text-sm font-semibold text-primary-400 mb-2">Titre</h3>
                        <div className="bg-dark-800/50 rounded-lg p-3">
                          <p className="text-white font-medium text-sm">{transcription.seo.title}</p>
                          <p className="text-xs text-dark-500 mt-1">{transcription.seo.title.length} caractères</p>
                        </div>
            </div>
          )}

                    {/* Description */}
                    {transcription.seo.description && (
                      <div>
                        <h3 className="text-sm font-semibold text-primary-400 mb-2">Description</h3>
                        <div className="bg-dark-800/50 rounded-lg p-3">
                          <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">
                            {transcription.seo.description}
                          </p>
                          <p className="text-xs text-dark-500 mt-2">{transcription.seo.description.length} caractères</p>
                        </div>
        </div>
      )}

                    {/* Hashtags */}
                    {transcription.seo.hashtags && transcription.seo.hashtags.length > 0 && (
                      <div>
                        <h3 className="text-sm font-semibold text-primary-400 mb-2">Hashtags</h3>
                        <div className="bg-dark-800/50 rounded-lg p-3">
                          <div className="flex flex-wrap gap-2">
                            {transcription.seo.hashtags.map((tag, index) => (
                              <span
                                key={index}
                                className="px-2 py-1 bg-primary-600/20 text-primary-400 rounded text-xs border border-primary-500/30"
                              >
                                {tag.startsWith('#') ? tag : `#${tag}`}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : selectedFile ? (
            <div className="flex-1 flex items-center justify-center p-4">
              <div className="text-center">
                <FileText className="w-12 h-12 text-dark-600 mx-auto mb-4" />
                <p className="text-dark-400 text-sm">Aucune transcription disponible</p>
                <p className="text-dark-500 text-xs mt-2">Utilisez /retranscript pour générer</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-4">
              <div className="text-center">
                <FileText className="w-12 h-12 text-dark-600 mx-auto mb-4" />
                <p className="text-dark-400 text-sm">Sélectionnez une vidéo</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
