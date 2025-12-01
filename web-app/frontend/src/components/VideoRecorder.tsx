'use client';

import { useState, useRef, useEffect, useCallback, createContext, useContext } from 'react';
import { 
  Video, 
  VideoOff,
  Mic, 
  MicOff,
  Monitor,
  Circle,
  Square,
  Pause,
  Play,
  Upload,
  Check,
  Loader2,
  Camera,
  Layout,
  LayoutGrid,
  User,
  Layers,
  Volume2,
  VolumeX,
  Zap,
  ZapOff
} from 'lucide-react';

type LayoutMode = 'screen_only' | 'webcam_only' | 'side_by_side' | 'overlay';
type RecordingState = 'idle' | 'countdown' | 'recording' | 'paused' | 'processing' | 'preview';

interface RecordingConfig {
  layout: LayoutMode;
  webcamEnabled: boolean;
  micEnabled: boolean;
  micVolume: number;
  webcamPosition: { x: number; y: number };
  webcamSize: number;
  webcamShape: 'circle' | 'rounded' | 'square';
  webcamBorderColor: string;
  webcamBorderWidth: number;
  autoProcess: boolean;  // Traitement automatique (silences, shorts, etc.)
  autoIllustrate: boolean;  // Ajout automatique de clips Pexels/Unsplash
}

// Helper pour détecter le meilleur format vidéo pour l'écran (VP9 pour compression)
function getBestVideoFormat(withAudio: boolean = false): { mimeType: string; extension: string } {
  // VP9 d'abord (meilleure compression pour screen recording)
  const webmTypes = withAudio
    ? ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']
    : ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
  
  for (const type of webmTypes) {
    if (MediaRecorder.isTypeSupported(type)) {
      console.log(`[Format] WebM VP9 utilisé: ${type}`);
      return { mimeType: type, extension: 'webm' };
    }
  }
  
  // Fallback MP4
  const mp4Types = withAudio 
    ? ['video/mp4;codecs=avc1,mp4a.40.2', 'video/mp4;codecs=h264,aac', 'video/mp4']
    : ['video/mp4;codecs=avc1', 'video/mp4;codecs=h264', 'video/mp4'];
  
  for (const type of mp4Types) {
    if (MediaRecorder.isTypeSupported(type)) {
      console.log(`[Format] MP4 fallback: ${type}`);
      return { mimeType: type, extension: 'mp4' };
    }
  }
  
  // Dernier recours
  return { mimeType: 'video/webm', extension: 'webm' };
}

// Helper pour la webcam : H.264 prioritaire (meilleur pour les visages)
function getWebcamFormat(): { mimeType: string; extension: string } {
  // H.264/AVC d'abord - optimisé pour les visages, meilleure qualité
  const h264Types = [
    'video/mp4;codecs=avc1.42E01E',  // Baseline profile
    'video/mp4;codecs=avc1.4D401E',  // Main profile
    'video/mp4;codecs=avc1.64001E',  // High profile
    'video/mp4;codecs=avc1',
    'video/mp4;codecs=h264',
    'video/mp4',
  ];
  
  for (const type of h264Types) {
    if (MediaRecorder.isTypeSupported(type)) {
      console.log(`[Format Webcam] H.264 utilisé: ${type}`);
      return { mimeType: type, extension: 'mp4' };
    }
  }
  
  // Fallback WebM VP9 si H.264 non supporté
  const webmTypes = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
  for (const type of webmTypes) {
    if (MediaRecorder.isTypeSupported(type)) {
      console.log(`[Format Webcam] WebM fallback: ${type}`);
      return { mimeType: type, extension: 'webm' };
    }
  }
  
  return { mimeType: 'video/webm', extension: 'webm' };
}

// Contexte pour partager la config entre les instances
export interface RecordingConfigContextType {
  config: RecordingConfig;
  setConfig: (config: RecordingConfig | ((prev: RecordingConfig) => RecordingConfig)) => void;
}

export const RecordingConfigContext = createContext<RecordingConfigContextType | null>(null);

export function useRecordingConfig() {
  const context = useContext(RecordingConfigContext);
  if (!context) {
    throw new Error('useRecordingConfig must be used within RecordingConfigProvider');
  }
  return context;
}

interface VideoRecorderProps {
  onLog?: (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => void;
  showControlsInline?: boolean;  // Show controls below preview (default true)
  showControlsOnly?: boolean;    // Show only controls, no preview
  sharedConfig?: RecordingConfigContextType;  // Config partagée optionnelle
  onProcessingComplete?: (folderName: string, autoProcess: boolean, autoIllustrate: boolean, layout: string) => void;  // Callback quand le traitement est terminé
}

export function VideoRecorder({ onLog, showControlsInline = true, showControlsOnly = false, sharedConfig, onProcessingComplete }: VideoRecorderProps) {
  // Helper to log
  const log = (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => {
    console.log(`[${type}] ${message}`);
    onLog?.(type, message);
  };
  // Refs
  const webcamRef = useRef<HTMLVideoElement>(null);
  const screenRef = useRef<HTMLVideoElement>(null);
  const webcamStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const screenRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const screenChunksRef = useRef<Blob[]>([]);
  
  // Canvas pour forcer le fps à 30 (comme dans FFmpeg)
  const webcamCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const webcamCanvasStreamRef = useRef<MediaStream | null>(null);
  const webcamCanvasIntervalRef = useRef<number | null>(null);
  
  // Canvas compositing temps réel (switch auto layout)
  const compositeCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const compositeStreamRef = useRef<MediaStream | null>(null);
  const compositeRecorderRef = useRef<MediaRecorder | null>(null);
  const compositeChunksRef = useRef<Blob[]>([]);
  const compositeAnimationRef = useRef<number>(0);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const recordingStartTimeRef = useRef<number>(0);
  const screenVideoRef = useRef<HTMLVideoElement | null>(null);
  const webcamVideoRef = useRef<HTMLVideoElement | null>(null);
  const currentDisplayLayoutRef = useRef<'overlay' | 'webcam_only'>('overlay');
  
  // Format vidéo utilisé (MP4 ou WebM)
  const webcamFormatRef = useRef<{ mimeType: string; extension: string }>({ mimeType: 'video/webm', extension: 'webm' });
  const screenFormatRef = useRef<{ mimeType: string; extension: string }>({ mimeType: 'video/webm', extension: 'webm' });
  
  // Audio refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Utiliser la config partagée si fournie, sinon créer un état local
  // Paramètres par défaut : webcam en bas à droite (93%, 88%), taille 232px, carré arrondi
  const [localConfig, setLocalConfig] = useState<RecordingConfig>({
    layout: 'overlay',
    webcamEnabled: true,
    micEnabled: true,
    micVolume: 100,
    webcamPosition: { x: 93, y: 88 },
    webcamSize: 232,
    webcamShape: 'rounded',
    webcamBorderColor: '#8B5CF6',  // Violet pour meilleure visibilité
    webcamBorderWidth: 3,
    autoProcess: true,
    autoIllustrate: false,  // Désactivé par défaut (nécessite clés API)
  });
  
  const config = sharedConfig?.config || localConfig;
  const setConfig = sharedConfig?.setConfig || setLocalConfig;
  
  // Audio level state
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>('');
  
  // Drag state for webcam position
  const [isDraggingWebcam, setIsDraggingWebcam] = useState(false);
  const dragStartRef = useRef<{ 
    x: number; 
    y: number; 
    startX: number; 
    startY: number;
    currentX?: number;
    currentY?: number;
  } | null>(null);
  const previewContainerRef = useRef<HTMLDivElement>(null);

  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [countdown, setCountdown] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [webcamReady, setWebcamReady] = useState(false);
  const [screenReady, setScreenReady] = useState(false);
  
  // Recorded blobs for preview
  const [screenBlob, setScreenBlob] = useState<Blob | null>(null);
  const [webcamBlob, setWebcamBlob] = useState<Blob | null>(null);
  
  // Auto switch layout (Canvas compositing)
  const [autoSwitchEnabled, setAutoSwitchEnabled] = useState(true);
  const [currentDisplayLayout, setCurrentDisplayLayout] = useState<'overlay' | 'webcam_only'>('overlay');
  const [compositeBlob, setCompositeBlob] = useState<Blob | null>(null);
  
  // Enregistrement des timestamps de switch pour le merge backend
  const layoutSwitchesRef = useRef<Array<{ timestamp: number; layout: 'overlay' | 'webcam_only' }>>([]);
  const lastWebcamOnlySwitchRef = useRef<number>(0); // Timestamp du dernier switch vers webcam_only
  



  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (recordingState === 'recording') {
      interval = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [recordingState]);

  // Get audio devices on mount
  useEffect(() => {
    const getDevices = async () => {
      try {
        // Request permission first
        await navigator.mediaDevices.getUserMedia({ audio: true });
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter(d => d.kind === 'audioinput');
        setAudioDevices(audioInputs);
        if (audioInputs.length > 0 && !selectedAudioDevice) {
          setSelectedAudioDevice(audioInputs[0].deviceId);
        }
      } catch (err) {
        console.error('Error getting audio devices:', err);
      }
    };
    getDevices();
  }, []);

  // Initialize audio with level detection
  const initAudio = useCallback(async () => {
    log('action', 'Initialisation du microphone...');
    try {
      // Contraintes audio haute qualité
      const audioConstraints: MediaTrackConstraints = {
        echoCancellation: true,      // Suppression d'écho
        noiseSuppression: true,      // Suppression de bruit de fond
        autoGainControl: true,       // Contrôle automatique du gain
        sampleRate: 48000,           // Échantillonnage 48kHz (qualité CD)
        channelCount: 1,             // Mono (meilleur pour la voix)
      };
      
      // Ajouter le device sélectionné si disponible
      if (selectedAudioDevice) {
        audioConstraints.deviceId = { exact: selectedAudioDevice };
      }
      
      const constraints: MediaStreamConstraints = {
        audio: audioConstraints
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      audioStreamRef.current = stream;
      
      // AudioContext avec sample rate haute qualité
      const audioContext = new AudioContext({ sampleRate: 48000 });
      audioContextRef.current = audioContext;
      
      log('info', `Micro: ${audioContext.sampleRate}Hz`);
      
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      const gainNode = audioContext.createGain();
      
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      gainNode.gain.value = config.micVolume / 100;
      
      source.connect(gainNode);
      gainNode.connect(analyser);
      
      analyserRef.current = analyser;
      gainNodeRef.current = gainNode;
      
      const detectLevel = () => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const normalizedLevel = Math.min(100, (average / 128) * 100);
        setAudioLevel(normalizedLevel);
        animationFrameRef.current = requestAnimationFrame(detectLevel);
      };
      
      detectLevel();
      setError(null);
      log('success', 'Microphone connecte');
    } catch (err) {
      console.error('Audio error:', err);
      setError('Impossible d\'acceder au microphone');
      log('error', 'Echec connexion microphone');
    }
  }, [selectedAudioDevice, config.micVolume]);

  // Update volume when changed
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = config.micVolume / 100;
    }
  }, [config.micVolume]);

  // Initialize/stop audio based on mic toggle
  useEffect(() => {
    if (config.micEnabled && !audioStreamRef.current) {
      initAudio();
    } else if (!config.micEnabled) {
      stopAudio();
    }
    
    return () => {
      stopAudio();
    };
  }, [config.micEnabled, initAudio]);

  // Stop audio
  const stopAudio = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
    analyserRef.current = null;
    gainNodeRef.current = null;
    setAudioLevel(0);
  }, []);

  // Initialize webcam function - Utilise le stream direct pour l'aperçu
  // Capture en Full HD 1080p à 30fps avec qualité maximale
  const initWebcam = useCallback(async () => {
    log('action', 'Initialisation de la webcam...');
    try {
      const TARGET_WIDTH = 1920;  // 1080p pour qualité maximale
      const TARGET_HEIGHT = 1080;
      const TARGET_FPS = 30;  // 30fps suffisant pour webcam
      
      // Obtenir le stream de la webcam avec contraintes HD + qualité maximale
      let stream: MediaStream;
      try {
        // D'abord essayer 1080p avec contraintes de qualité maximale
        stream = await navigator.mediaDevices.getUserMedia({
          video: { 
            width: { ideal: TARGET_WIDTH, min: 1280 },
            height: { ideal: TARGET_HEIGHT, min: 720 },
            facingMode: 'user',
            frameRate: { ideal: TARGET_FPS, max: 30 },
            // Désactiver les traitements automatiques qui dégradent la qualité
            // @ts-ignore - Ces contraintes sont supportées par Chrome/Edge
            resizeMode: 'none',  // Pas de redimensionnement logiciel
          } as MediaTrackConstraints,
          audio: false,
        });
      } catch (err) {
        // Fallback 720p si 1080p échoue
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { 
              width: { ideal: 1920 },
              height: { ideal: 1080 },
              facingMode: 'user',
              frameRate: { ideal: TARGET_FPS }
            },
            audio: false,
          });
        } catch (err2) {
          // Fallback minimal
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user' },
            audio: false,
          });
        }
      }
      
      // Vérifier la résolution et le fps réels
      const videoTrack = stream.getVideoTracks()[0];
      const settings = videoTrack.getSettings();
      const actualWidth = settings.width || TARGET_WIDTH;
      const actualHeight = settings.height || TARGET_HEIGHT;
      const actualFps = settings.frameRate || TARGET_FPS;
      
      // Stocker le stream original
      webcamStreamRef.current = stream;
      
      // Afficher dans l'aperçu
      if (webcamRef.current) {
        webcamRef.current.srcObject = stream;
        await webcamRef.current.play();
      }
      
      setWebcamReady(true);
      setError(null);
      log('success', `Webcam connectee (${actualWidth}x${actualHeight}@${Math.round(actualFps)}fps)`);
    } catch (err) {
      console.error('Webcam error:', err);
      setError('Impossible d\'acceder a la webcam. Verifiez les permissions.');
      setWebcamReady(false);
      log('error', 'Echec connexion webcam');
    }
  }, []);

  // Auto-initialize webcam on mount and when webcamEnabled changes
  useEffect(() => {
    const shouldShowWebcam = config.webcamEnabled && config.layout !== 'screen_only';
    
    if (shouldShowWebcam && !webcamReady && !webcamStreamRef.current) {
      initWebcam();
    } else if (!config.webcamEnabled && webcamStreamRef.current) {
      // Seulement arrêter si webcam désactivée explicitement (pas sur changement de layout)
      webcamStreamRef.current.getTracks().forEach(track => track.stop());
      webcamStreamRef.current = null;
      if (webcamRef.current) {
        webcamRef.current.srcObject = null;
      }
      setWebcamReady(false);
    }
  }, [config.webcamEnabled, config.layout, webcamReady, initWebcam]);
  
  // Cleanup webcam uniquement au démontage du composant
  useEffect(() => {
    return () => {
      if (webcamStreamRef.current) {
        webcamStreamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  // Handle webcam drag - Optimisé pour la fluidité
  useEffect(() => {
    let animationFrameId: number | null = null;
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingWebcam || !dragStartRef.current || !previewContainerRef.current || !webcamRef.current) return;
      
      // Annuler l'animation frame précédente si elle existe
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }
      
      // Utiliser requestAnimationFrame pour une mise à jour fluide
      animationFrameId = requestAnimationFrame(() => {
        if (!dragStartRef.current || !previewContainerRef.current || !webcamRef.current) return;
        
        const rect = previewContainerRef.current.getBoundingClientRect();
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;
        
        // Convertir le déplacement en pourcentage
        const percentX = (dx / rect.width) * 100;
        const percentY = (dy / rect.height) * 100;
        
        // Calculer la nouvelle position
        let newX = dragStartRef.current.startX + percentX;
        let newY = dragStartRef.current.startY + percentY;
        
        // Limiter aux bords (en tenant compte de la taille de la webcam)
        const webcamSizePercent = (config.webcamSize / rect.width) * 100;
        const webcamSizePercentH = (config.webcamSize / rect.height) * 100;
        
        newX = Math.max(webcamSizePercent / 2, Math.min(100 - webcamSizePercent / 2, newX));
        newY = Math.max(webcamSizePercentH / 2, Math.min(100 - webcamSizePercentH / 2, newY));
        
        // Mettre à jour directement le DOM pour la fluidité (sans re-render React)
        const video = webcamRef.current;
        video.style.setProperty('left', `${newX}%`, 'important');
        video.style.setProperty('top', `${newY}%`, 'important');
        
        // Stocker la position temporaire pour la synchroniser à la fin
        dragStartRef.current.currentX = newX;
        dragStartRef.current.currentY = newY;
      });
    };
    
    const handleMouseUp = () => {
      if (isDraggingWebcam && dragStartRef.current) {
        // Synchroniser la position finale avec le state React
        if (dragStartRef.current.currentX !== undefined && dragStartRef.current.currentY !== undefined) {
          setConfig({ 
            ...config, 
            webcamPosition: { 
              x: dragStartRef.current.currentX, 
              y: dragStartRef.current.currentY 
            } 
          });
        }
        
        setIsDraggingWebcam(false);
        if (webcamRef.current) {
          webcamRef.current.style.cursor = 'grab';
        }
        dragStartRef.current = null;
      }
    };
    
    if (isDraggingWebcam) {
      document.addEventListener('mousemove', handleMouseMove, { passive: true });
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        if (animationFrameId !== null) {
          cancelAnimationFrame(animationFrameId);
        }
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDraggingWebcam, config, setConfig]);

  // Force update webcam styles when config changes
  useEffect(() => {
    if (!webcamRef.current || !config.webcamEnabled) return;
    
    const updateStyles = () => {
      const video = webcamRef.current;
      if (!video) return;
      
      // Utiliser requestAnimationFrame pour s'assurer que le DOM est prêt
      requestAnimationFrame(() => {
        if (!video) return;
        
        // Construire le style CSS complet avec !important
        let newStyles = '';
        
        if (config.layout === 'overlay') {
          newStyles += `width: ${config.webcamSize}px !important; height: ${config.webcamSize}px !important;`;
          newStyles += `left: ${config.webcamPosition.x}% !important; top: ${config.webcamPosition.y}% !important;`;
          newStyles += `transform: translate(-50%, -50%) !important;`;
          newStyles += `z-index: 10 !important;`;
        } else if (config.layout !== 'side_by_side' && config.layout !== 'webcam_only') {
          newStyles += `width: ${config.webcamSize}px !important; height: ${config.webcamSize}px !important;`;
          newStyles += `z-index: 10 !important;`;
        }
        
        newStyles += `border-width: ${config.webcamBorderWidth}px !important; border-style: solid !important; border-color: ${config.webcamBorderColor} !important; box-sizing: border-box !important;`;
        
        // Remplacer complètement les styles de taille et bordure
        const currentStyle = video.getAttribute('style') || '';
        const preservedStyles = currentStyle.split(';').filter(s => {
          const trimmed = s.trim();
          return trimmed && 
                 !trimmed.includes('width') && 
                 !trimmed.includes('height') && 
                 !trimmed.includes('border') && 
                 !trimmed.includes('box-sizing') &&
                 !trimmed.includes('left') &&
                 !trimmed.includes('top') &&
                 !trimmed.includes('transform') &&
                 !trimmed.includes('z-index');
        }).join(';');
        
        // Appliquer les nouveaux styles
        const finalStyle = preservedStyles ? `${preservedStyles}; ${newStyles}` : newStyles;
        video.setAttribute('style', finalStyle);
        
        // Forcer aussi via style direct pour être sûr
        if (config.layout === 'overlay') {
          video.style.setProperty('width', `${config.webcamSize}px`, 'important');
          video.style.setProperty('height', `${config.webcamSize}px`, 'important');
          video.style.setProperty('left', `${config.webcamPosition.x}%`, 'important');
          video.style.setProperty('top', `${config.webcamPosition.y}%`, 'important');
          video.style.setProperty('transform', 'translate(-50%, -50%)', 'important');
          video.style.setProperty('z-index', '10', 'important'); // Au-dessus du placeholder
        }
        video.style.setProperty('border-width', `${config.webcamBorderWidth}px`, 'important');
        video.style.setProperty('border-style', 'solid', 'important');
        video.style.setProperty('border-color', config.webcamBorderColor, 'important');
        video.style.setProperty('box-sizing', 'border-box', 'important');
        
        console.log('Styles appliqués:', {
          size: config.webcamSize,
          borderWidth: config.webcamBorderWidth,
          borderColor: config.webcamBorderColor,
          layout: config.layout,
          computedBorder: window.getComputedStyle(video).borderWidth,
          computedWidth: window.getComputedStyle(video).width,
          computedHeight: window.getComputedStyle(video).height,
          actualStyle: video.getAttribute('style')
        });
      });
    };
    
    updateStyles();
  }, [config.webcamSize, config.webcamBorderWidth, config.webcamBorderColor, config.webcamShape, config.layout, config.webcamEnabled, config.webcamPosition]);

  // Initialize screen capture
  const initScreen = useCallback(async () => {
    log('action', 'Selection de l\'ecran a capturer...');
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { width: 1920, height: 1080, frameRate: 30 },
        audio: true,
      });
      
      screenStreamRef.current = stream;
      if (screenRef.current) {
        screenRef.current.srcObject = stream;
      }
      setScreenReady(true);
      setError(null);
      
      const track = stream.getVideoTracks()[0];
      const settings = track.getSettings();
      log('success', `Ecran capture (${settings.width}x${settings.height})`);

      track.onended = () => {
        setScreenReady(false);
        log('warning', 'Capture ecran arretee');
        if (recordingState === 'recording') {
          stopRecording();
        }
      };
    } catch (err) {
      console.error('Screen error:', err);
      setError('Capture d\'ecran annulee');
      setScreenReady(false);
      log('warning', 'Capture ecran annulee');
    }
  }, [recordingState]);

  // ===== CANVAS COMPOSITING TEMPS RÉEL =====
  
  // Dessiner la webcam avec la forme configurée (circle, rounded, square) et bordure sur le Canvas
  const drawWebcamBubble = useCallback((
    ctx: CanvasRenderingContext2D,
    webcamVideo: HTMLVideoElement,
    canvasWidth: number,
    canvasHeight: number
  ) => {
    const size = config.webcamSize;
    const borderWidth = config.webcamBorderWidth;
    const innerSize = size - borderWidth * 2;
    const shape = config.webcamShape || 'rounded';
    
    // Position en pixels (config.webcamPosition est en %)
    const x = (config.webcamPosition.x / 100) * canvasWidth;
    const y = (config.webcamPosition.y / 100) * canvasHeight;
    
    // Coin supérieur gauche pour les formes carrées/arrondies
    const topLeftX = x - size / 2;
    const topLeftY = y - size / 2;
    const innerTopLeftX = x - innerSize / 2;
    const innerTopLeftY = y - innerSize / 2;
    
    // Rayon pour coins arrondis (environ 15% de la taille)
    const cornerRadius = Math.round(size * 0.15);
    const innerCornerRadius = Math.round(innerSize * 0.15);
    
    ctx.save();
    
    // Dessiner la bordure selon la forme
    ctx.beginPath();
    if (shape === 'circle') {
      ctx.arc(x, y, size / 2, 0, Math.PI * 2);
    } else if (shape === 'rounded') {
      ctx.roundRect(topLeftX, topLeftY, size, size, cornerRadius);
    } else {
      // square
      ctx.rect(topLeftX, topLeftY, size, size);
    }
    ctx.fillStyle = config.webcamBorderColor;
    ctx.fill();
    
    // Clip pour la webcam selon la forme
    ctx.beginPath();
    if (shape === 'circle') {
      ctx.arc(x, y, innerSize / 2, 0, Math.PI * 2);
    } else if (shape === 'rounded') {
      ctx.roundRect(innerTopLeftX, innerTopLeftY, innerSize, innerSize, innerCornerRadius);
    } else {
      // square
      ctx.rect(innerTopLeftX, innerTopLeftY, innerSize, innerSize);
    }
    ctx.clip();
    
    // Calculer les dimensions pour garder le ratio et centrer
    const videoRatio = webcamVideo.videoWidth / webcamVideo.videoHeight;
    let drawWidth = innerSize;
    let drawHeight = innerSize;
    
    if (videoRatio > 1) {
      drawHeight = innerSize;
      drawWidth = innerSize * videoRatio;
    } else {
      drawWidth = innerSize;
      drawHeight = innerSize / videoRatio;
    }
    
    const drawX = x - drawWidth / 2;
    const drawY = y - drawHeight / 2;
    
    ctx.drawImage(webcamVideo, drawX, drawY, drawWidth, drawHeight);
    ctx.restore();
  }, [config.webcamSize, config.webcamBorderWidth, config.webcamBorderColor, config.webcamPosition, config.webcamShape]);

  // Fonction principale de compositing
  const startCompositing = useCallback(() => {
    if (!compositeCanvasRef.current) {
      // Créer le canvas hors-écran
      compositeCanvasRef.current = document.createElement('canvas');
      compositeCanvasRef.current.width = 1920;
      compositeCanvasRef.current.height = 1080;
    }
    
    const canvas = compositeCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Créer des éléments vidéo pour lire les streams
    if (!screenVideoRef.current && screenStreamRef.current) {
      screenVideoRef.current = document.createElement('video');
      screenVideoRef.current.srcObject = screenStreamRef.current;
      screenVideoRef.current.muted = true;
      screenVideoRef.current.play();
    }
    
    if (!webcamVideoRef.current && webcamStreamRef.current) {
      webcamVideoRef.current = document.createElement('video');
      webcamVideoRef.current.srcObject = webcamStreamRef.current;
      webcamVideoRef.current.muted = true;
      webcamVideoRef.current.play();
    }
    
    const draw = () => {
      if (!ctx) return;
      
      // Lire le layout depuis la ref (mise à jour dynamiquement)
      const displayLayout = currentDisplayLayoutRef.current;
      
      // Effacer le canvas
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, 1920, 1080);
      
      if (displayLayout === 'overlay' && screenVideoRef.current && webcamVideoRef.current) {
        // Mode overlay : écran + webcam bubble
        ctx.drawImage(screenVideoRef.current, 0, 0, 1920, 1080);
        drawWebcamBubble(ctx, webcamVideoRef.current, 1920, 1080);
      } else if (displayLayout === 'webcam_only' && webcamVideoRef.current) {
        // Mode webcam plein écran
        const video = webcamVideoRef.current;
        const videoRatio = video.videoWidth / video.videoHeight;
        const canvasRatio = 1920 / 1080;
        
        let drawWidth, drawHeight, drawX, drawY;
        
        if (videoRatio > canvasRatio) {
          drawHeight = 1080;
          drawWidth = 1080 * videoRatio;
          drawX = (1920 - drawWidth) / 2;
          drawY = 0;
        } else {
          drawWidth = 1920;
          drawHeight = 1920 / videoRatio;
          drawX = 0;
          drawY = (1080 - drawHeight) / 2;
        }
        
        ctx.drawImage(video, drawX, drawY, drawWidth, drawHeight);
      } else if (screenVideoRef.current) {
        // Fallback : juste l'écran
        ctx.drawImage(screenVideoRef.current, 0, 0, 1920, 1080);
      }
      
      compositeAnimationRef.current = requestAnimationFrame(draw);
    };
    
    draw();
    
    // Capturer le stream du Canvas à 30 fps
    compositeStreamRef.current = canvas.captureStream(30);
    
    log('info', 'Canvas compositing démarré (30 fps)');
  }, [drawWebcamBubble]);

  // Mettre à jour la ref quand le layout change (pour que le draw loop le voie)
  useEffect(() => {
    currentDisplayLayoutRef.current = currentDisplayLayout;
  }, [currentDisplayLayout]);

  // Détection d'inactivité pour le switch auto
  const handleActivity = useCallback(() => {
    if (recordingState !== 'recording' || !autoSwitchEnabled || config.layout !== 'overlay') return;
    
    // Si on était en webcam_only, revenir en overlay SEULEMENT après 2 secondes minimum
    if (currentDisplayLayout === 'webcam_only') {
      const now = Date.now();
      const timeSinceSwitch = now - lastWebcamOnlySwitchRef.current;
      const MIN_WEBCAM_ONLY_DURATION = 2000; // 2 secondes minimum en webcam_only
      
      if (timeSinceSwitch >= MIN_WEBCAM_ONLY_DURATION) {
        const timestamp = (now - recordingStartTimeRef.current) / 1000;
        layoutSwitchesRef.current.push({ timestamp, layout: 'overlay' });
        setCurrentDisplayLayout('overlay');
        log('info', `↩️ Retour overlay @ ${timestamp.toFixed(1)}s (activité détectée)`);
      }
      // Si moins de 2s, on ignore l'activité (évite les retours instantanés)
      return;
    }
    
    // Reset le timer d'inactivité
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    
    inactivityTimerRef.current = setTimeout(() => {
      if (recordingState === 'recording' && autoSwitchEnabled) {
        const now = Date.now();
        const timestamp = (now - recordingStartTimeRef.current) / 1000;
        layoutSwitchesRef.current.push({ timestamp, layout: 'webcam_only' });
        lastWebcamOnlySwitchRef.current = now; // Enregistrer le moment du switch
        setCurrentDisplayLayout('webcam_only');
        log('info', `📷 Switch webcam plein écran @ ${timestamp.toFixed(1)}s (5s inactivité)`);
      }
    }, 5000);
  }, [recordingState, autoSwitchEnabled, currentDisplayLayout, config.layout]);

  // Écouter les événements d'activité
  useEffect(() => {
    if (recordingState === 'recording' && autoSwitchEnabled && config.layout === 'overlay') {
      window.addEventListener('mousemove', handleActivity);
      window.addEventListener('keydown', handleActivity);
      window.addEventListener('click', handleActivity);
      window.addEventListener('scroll', handleActivity);
      
      // Démarrer le timer initial
      handleActivity();
      
      return () => {
        window.removeEventListener('mousemove', handleActivity);
        window.removeEventListener('keydown', handleActivity);
        window.removeEventListener('click', handleActivity);
        window.removeEventListener('scroll', handleActivity);
        if (inactivityTimerRef.current) {
          clearTimeout(inactivityTimerRef.current);
        }
      };
    }
  }, [recordingState, autoSwitchEnabled, config.layout, handleActivity]);

  // Arrêter le compositing
  const stopCompositing = useCallback(() => {
    if (compositeAnimationRef.current) {
      cancelAnimationFrame(compositeAnimationRef.current);
      compositeAnimationRef.current = 0;
    }
    
    if (compositeStreamRef.current) {
      compositeStreamRef.current.getTracks().forEach(track => track.stop());
      compositeStreamRef.current = null;
    }
    
    if (screenVideoRef.current) {
      screenVideoRef.current.srcObject = null;
      screenVideoRef.current = null;
    }
    
    if (webcamVideoRef.current) {
      webcamVideoRef.current.srcObject = null;
      webcamVideoRef.current = null;
    }
    
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
    
    compositeCanvasRef.current = null;
    setCurrentDisplayLayout('overlay');
  }, []);

  // ===== FIN CANVAS COMPOSITING =====

  // Check if ready to record
  const canRecord = config.layout === 'webcam_only' 
    ? (webcamReady || config.webcamEnabled) 
    : screenReady;

  // Start recording
  // Actually start recording (called after countdown)
  const actuallyStartRecording = useCallback(async () => {
    log('action', 'Demarrage de l\'enregistrement...');
    log('info', `Layout: ${config.layout}${autoSwitchEnabled && config.layout === 'overlay' ? ' (Switch auto ON)' : ''}`);
    setError(null);
    setDuration(0);
    chunksRef.current = [];
    screenChunksRef.current = [];
    compositeChunksRef.current = [];
    layoutSwitchesRef.current = []; // Reset les switches
    lastWebcamOnlySwitchRef.current = 0; // Reset le timestamp du dernier switch webcam
    recordingStartTimeRef.current = Date.now();

    try {
      // Initialize webcam if needed and not ready
      if (config.layout !== 'screen_only' && config.webcamEnabled && !webcamReady) {
        await initWebcam();
      }

      // Wait a bit for streams to be ready
      await new Promise(resolve => setTimeout(resolve, 300));

      // ===== SWITCH AUTO: Aperçu + timestamps pour merge backend =====
      // Le Canvas est utilisé pour l'aperçu (switch overlay ↔ webcam)
      // Les timestamps des switches sont enregistrés et envoyés au backend pour le merge final
      if (autoSwitchEnabled && config.layout === 'overlay' && screenStreamRef.current && webcamStreamRef.current) {
        log('info', '🎬 Switch Auto activé (timestamps enregistrés pour merge)');
        startCompositing();  // Pour l'aperçu visuel uniquement
      }
      // ===== FIN SWITCH AUTO =====

      // Record webcam if enabled (mode classique)
      if (webcamStreamRef.current && config.layout !== 'screen_only') {
        // Vérifier la résolution ET le fps du stream avant enregistrement
        const videoTrack = webcamStreamRef.current.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        const width = settings.width || 1280;
        const height = settings.height || 720;
        const fps = settings.frameRate || 60;
        
        // Avertir si le fps est trop élevé (cause de lag)
        if (fps > 30) {
          log('warning', `ATTENTION: Webcam enregistre a ${fps} fps au lieu de 30, cela peut causer du lag!`);
          log('warning', `Essayez de reduire le fps de votre webcam dans les parametres systeme`);
        }
        
        // Forcer H.264 pour la webcam (meilleur pour les visages)
        const webcamFormat = getWebcamFormat();
        webcamFormatRef.current = webcamFormat;
        log('info', `Format webcam: ${webcamFormat.mimeType} (.${webcamFormat.extension})`);
        
        const options: MediaRecorderOptions = {
          mimeType: webcamFormat.mimeType,
          videoBitsPerSecond: 12_000_000, // 12 Mbps pour webcam 1080p (qualité maximale visage)
        };
        
        const recorder = new MediaRecorder(webcamStreamRef.current, options);
        
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };
        
        mediaRecorderRef.current = recorder;
        recorder.start(1000);
        log('info', `Webcam enregistrement demarre (${width}x${height}@${fps}fps)`);
      }

      // Record screen if enabled (avec audio si disponible)
      if (screenStreamRef.current && config.layout !== 'webcam_only') {
        // Combiner vidéo écran + audio micro
        const combinedStream = new MediaStream();
        
        // Ajouter toutes les pistes vidéo de l'écran
        screenStreamRef.current.getVideoTracks().forEach(track => {
          combinedStream.addTrack(track);
        });
        
        // Ajouter l'audio du micro si activé
        if (audioStreamRef.current && config.micEnabled) {
          audioStreamRef.current.getAudioTracks().forEach(track => {
            combinedStream.addTrack(track);
          });
        }
        
        // Détecter le meilleur format (MP4 prioritaire pour meilleure sync)
        const screenFormat = getBestVideoFormat(true);
        screenFormatRef.current = screenFormat;
        log('info', `Format screen: ${screenFormat.mimeType} (.${screenFormat.extension})`);
        
        const screenRecorder = new MediaRecorder(combinedStream, {
          mimeType: screenFormat.mimeType,
          videoBitsPerSecond: 6_000_000,  // 6 Mbps vidéo (qualité nette pour texte, FFmpeg compresse après)
          audioBitsPerSecond: 128000,     // 128 kbps audio
        });
        
        screenRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            screenChunksRef.current.push(e.data);
          }
        };
        
        screenRecorderRef.current = screenRecorder;
        screenRecorder.start(1000);
      }

      setRecordingState('recording');
      log('success', '● ENREGISTREMENT EN COURS');
    } catch (err) {
      console.error('Recording error:', err);
      setError('Erreur lors du demarrage de l\'enregistrement');
      log('error', 'Echec demarrage enregistrement');
      setRecordingState('idle');
    }
  }, [config, webcamReady, initWebcam]);

  // Start recording with countdown
  const startRecording = useCallback(async () => {
    // Verify screen is ready for layouts that need it
    if (config.layout !== 'webcam_only' && !screenReady) {
      log('warning', 'Selectionnez d\'abord un ecran');
      setError('Cliquez sur l\'apercu pour selectionner un ecran');
      return;
    }

    // Start countdown
    setRecordingState('countdown');
    setCountdown(5);
    log('info', 'Decompte: 5...');

    // Countdown from 5 to 1
    for (let i = 4; i >= 0; i--) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      if (i > 0) {
        setCountdown(i);
        log('info', `Decompte: ${i}...`);
      }
    }

    // Start recording
    setCountdown(0);
    await actuallyStartRecording();
  }, [config.layout, screenReady, actuallyStartRecording]);

  // Stop all streams
  const stopStreams = useCallback(() => {
    // Nettoyer le canvas si utilisé pour l'enregistrement
    if (webcamCanvasIntervalRef.current !== null) {
      clearInterval(webcamCanvasIntervalRef.current);
      webcamCanvasIntervalRef.current = null;
    }
    
    if (webcamCanvasStreamRef.current) {
      webcamCanvasStreamRef.current.getTracks().forEach(track => track.stop());
      webcamCanvasStreamRef.current = null;
    }
    
    webcamCanvasRef.current = null;
    
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach(track => track.stop());
      webcamStreamRef.current = null;
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
      screenStreamRef.current = null;
    }
    setWebcamReady(false);
    setScreenReady(false);
  }, []);

  // Handle composite (Canvas) file directly - Skip merge step
  const handleCompositeDirect = useCallback(async (compositeBlob: Blob) => {
    log('action', 'Création du projet (mode composite)...');
    log('info', `Composite: ${(compositeBlob.size / 1024 / 1024).toFixed(2)} MB`);
    
    try {
      const formData = new FormData();
      formData.append('combined_file', compositeBlob, 'combined.webm');
      formData.append('layout', 'composite');
      formData.append('auto_process', String(config.autoProcess));
      
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';
      const response = await fetch(`${API_URL}/api/projects/create-composite`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Erreur serveur: ${response.status}`);
      }
      
      const result = await response.json();
      log('success', `✅ Projet créé: ${result.folder_name}`);
      
      // Callback pour informer de la fin du traitement
      if (onProcessingComplete) {
        onProcessingComplete(result.folder_name, config.autoProcess, config.autoIllustrate, 'composite');
      }
      
      setRecordingState('idle');
      
    } catch (err) {
      console.error('Upload composite error:', err);
      log('error', `Erreur upload: ${err}`);
      setRecordingState('idle');
    }
  }, [config.autoProcess, config.autoIllustrate, onProcessingComplete]);

  // Handle merge directly with blobs - Simplified: create project and start pipeline in background
  const handleMergeDirect = useCallback(async (
    screenBlobToMerge: Blob,
    webcamBlobToMerge: Blob | null,
    mergeConfig: {
      layout: string;
      webcamX: number;
      webcamY: number;
      webcamSize: number;
      webcamShape: 'circle' | 'rounded' | 'square';
      webcamBorderColor?: string;
      webcamBorderWidth?: number;
    }
  ) => {
    log('action', 'Création du projet...');
    log('info', `Écran: ${(screenBlobToMerge.size / 1024 / 1024).toFixed(2)} MB`);
    if (webcamBlobToMerge) {
      log('info', `Webcam: ${(webcamBlobToMerge.size / 1024 / 1024).toFixed(2)} MB`);
    }
    
    try {
      const formData = new FormData();
      const screenExt = screenFormatRef.current.extension;
      formData.append('screen_file', screenBlobToMerge, `screen.${screenExt}`);
      
      if (webcamBlobToMerge) {
        const webcamExt = webcamFormatRef.current.extension;
        formData.append('webcam_file', webcamBlobToMerge, `webcam.${webcamExt}`);
      }
      
      formData.append('layout', mergeConfig.layout);
      formData.append('webcam_x', String(mergeConfig.webcamX));
      formData.append('webcam_y', String(mergeConfig.webcamY));
      formData.append('webcam_size', String(mergeConfig.webcamSize));
      formData.append('webcam_shape', mergeConfig.webcamShape);
      if (mergeConfig.webcamBorderColor) {
        formData.append('webcam_border_color', mergeConfig.webcamBorderColor);
      }
      if (mergeConfig.webcamBorderWidth !== undefined) {
        formData.append('webcam_border_width', String(mergeConfig.webcamBorderWidth));
      }
      formData.append('auto_process', String(config.autoProcess));
      
      // Envoyer les timestamps de switch auto si présents
      if (layoutSwitchesRef.current.length > 0) {
        formData.append('layout_switches', JSON.stringify(layoutSwitchesRef.current));
        log('info', `📍 ${layoutSwitchesRef.current.length} switch(es) de layout enregistré(s)`);
      }

      log('info', 'Envoi des fichiers...');
      
      // Envoyer au backend qui crée le projet et démarre le pipeline
      const response = await fetch('/api/create-project', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        const projectId = result.project_id;
        const folderName = result.folder_name;
        
        log('success', `✓ Projet créé: ${folderName}`);
        log('info', `Pipeline démarré en arrière-plan (12 étapes)`);
        log('info', `Suivez la progression dans "Projets"`);
        
        // Clean up
        setScreenBlob(null);
        setWebcamBlob(null);
        setRecordingState('idle');
        
        // Notification
        onProcessingComplete?.(folderName, config.autoProcess, config.autoIllustrate, config.layout);
        
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        throw new Error(errorData.detail || 'Erreur serveur');
      }
    } catch (err: any) {
      console.error('Create project error:', err);
      log('error', `Échec création projet: ${err.message || 'Erreur inconnue'}`);
      setRecordingState('idle');
    }
  }, [log, onProcessingComplete, config.autoProcess, config.autoIllustrate, config.layout]);

  // Stop recording
  const stopRecording = useCallback(async () => {
    log('action', 'Arret de l\'enregistrement...');
    setRecordingState('processing');
    setProcessing(true);

    // Stop recorders
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (screenRecorderRef.current && screenRecorderRef.current.state !== 'inactive') {
      screenRecorderRef.current.stop();
    }
    if (compositeRecorderRef.current && compositeRecorderRef.current.state !== 'inactive') {
      compositeRecorderRef.current.stop();
    }

    // Arrêter le compositing Canvas (utilisé uniquement pour l'aperçu Switch Auto)
    stopCompositing();

    // Wait for data
    await new Promise(resolve => setTimeout(resolve, 500));

    // Create blobs from recorded chunks (toujours mode standard)
    let newScreenBlob: Blob | null = null;
    let newWebcamBlob: Blob | null = null;
    
    if (screenChunksRef.current.length > 0) {
      const screenType = screenFormatRef.current.mimeType.split(';')[0]; // video/mp4 ou video/webm
      newScreenBlob = new Blob(screenChunksRef.current, { type: screenType });
      log('success', `Video ecran: ${(newScreenBlob.size / 1024 / 1024).toFixed(2)} MB (.${screenFormatRef.current.extension})`);
    }
    
    if (chunksRef.current.length > 0 && config.layout !== 'screen_only') {
      const webcamType = webcamFormatRef.current.mimeType.split(';')[0];
      newWebcamBlob = new Blob(chunksRef.current, { type: webcamType });
      log('success', `Video webcam: ${(newWebcamBlob.size / 1024 / 1024).toFixed(2)} MB (.${webcamFormatRef.current.extension})`);
    }

    // Store blobs
    setScreenBlob(newScreenBlob);
    setWebcamBlob(newWebcamBlob);
    
    // Stop streams
    stopStreams();
    setProcessing(false);
    
    // MODE TEST: Télécharger les fichiers séparément sans fusion
    const TEST_MODE = false; // Mettre à true pour télécharger les fichiers localement (debug)
    
    if (TEST_MODE && (newScreenBlob || newWebcamBlob)) {
      log('action', '[TEST] Téléchargement des fichiers séparés...');
      
      // Télécharger screen
      if (newScreenBlob) {
        const screenExt = screenFormatRef.current.extension;
        const screenUrl = URL.createObjectURL(newScreenBlob);
        const screenLink = document.createElement('a');
        screenLink.href = screenUrl;
        screenLink.download = `screen.${screenExt}`;
        screenLink.click();
        URL.revokeObjectURL(screenUrl);
        log('success', `[TEST] screen.${screenExt} téléchargé (${(newScreenBlob.size / 1024 / 1024).toFixed(2)} MB)`);
      }
      
      // Télécharger webcam
      if (newWebcamBlob) {
        const webcamExt = webcamFormatRef.current.extension;
        const webcamUrl = URL.createObjectURL(newWebcamBlob);
        const webcamLink = document.createElement('a');
        webcamLink.href = webcamUrl;
        webcamLink.download = `webcam.${webcamExt}`;
        webcamLink.click();
        URL.revokeObjectURL(webcamUrl);
        log('success', `[TEST] webcam.${webcamExt} téléchargé (${(newWebcamBlob.size / 1024 / 1024).toFixed(2)} MB)`);
      }
      
      setRecordingState('idle');
      log('success', '[TEST] Fichiers téléchargés - Vérifie les durées avec ffprobe !');
      return;
    }
    
    // Fusion directe avec la config actuelle (désactivé en mode test)
    if (newScreenBlob || newWebcamBlob) {
      log('action', 'Fusion directe avec la configuration actuelle...');
      
      // Utiliser les nouveaux blobs directement
      const mergeBlobs = async () => {
        if (config.layout === 'overlay' && newWebcamBlob && newScreenBlob) {
          // Convertir la position en pixels pour 1920x1080
          const finalX = Math.round((config.webcamPosition.x / 100) * 1920 - (config.webcamSize / 2));
          const finalY = Math.round((config.webcamPosition.y / 100) * 1080 - (config.webcamSize / 2));
          
          await handleMergeDirect(newScreenBlob, newWebcamBlob, {
            layout: config.layout,
            webcamX: finalX,
            webcamY: finalY,
            webcamSize: config.webcamSize,
            webcamShape: config.webcamShape,
            webcamBorderColor: config.webcamBorderColor,
            webcamBorderWidth: config.webcamBorderWidth
          });
        } else if (config.layout === 'side_by_side' && newWebcamBlob && newScreenBlob) {
          await handleMergeDirect(newScreenBlob, newWebcamBlob, {
            layout: config.layout,
            webcamX: 0,
            webcamY: 0,
            webcamSize: config.webcamSize,
            webcamShape: config.webcamShape,
            webcamBorderColor: config.webcamBorderColor,
            webcamBorderWidth: config.webcamBorderWidth
          });
        } else if (newScreenBlob) {
          await handleMergeDirect(newScreenBlob, null, {
            layout: config.layout,
            webcamX: 0,
            webcamY: 0,
            webcamSize: config.webcamSize,
            webcamShape: config.webcamShape,
            webcamBorderColor: config.webcamBorderColor,
            webcamBorderWidth: config.webcamBorderWidth
          });
        }
      };
      
      mergeBlobs();
      setRecordingState('processing');
    } else {
      setRecordingState('idle');
      log('error', 'Aucune video capturee');
    }
  }, [config, handleMergeDirect, log, stopStreams]);

  // Handle merge from preview
  const handleMerge = useCallback(async (mergeConfig: {
    layout: string;
    webcamX: number;
    webcamY: number;
    webcamSize: number;
    webcamShape: 'circle' | 'rounded' | 'square';
    webcamBorderColor?: string;
    webcamBorderWidth?: number;
  }) => {
    if (!screenBlob) {
      log('error', 'Pas de video ecran');
      return;
    }

    log('action', 'Envoi au serveur pour fusion...');
    log('info', `Ecran: ${(screenBlob.size / 1024 / 1024).toFixed(2)} MB`);
    if (webcamBlob) {
      log('info', `Webcam: ${(webcamBlob.size / 1024 / 1024).toFixed(2)} MB`);
    }
    
    try {
      const formData = new FormData();
      const screenExt = screenFormatRef.current.extension;
      formData.append('screen_file', screenBlob, `screen.${screenExt}`);
      
      if (webcamBlob) {
        const webcamExt = webcamFormatRef.current.extension;
        formData.append('webcam_file', webcamBlob, `webcam.${webcamExt}`);
      }
      
      formData.append('layout', mergeConfig.layout);
      formData.append('webcam_x', String(mergeConfig.webcamX));
      formData.append('webcam_y', String(mergeConfig.webcamY));
      formData.append('webcam_size', String(mergeConfig.webcamSize));
      formData.append('webcam_shape', mergeConfig.webcamShape);
      if (mergeConfig.webcamBorderColor) {
        formData.append('webcam_border_color', mergeConfig.webcamBorderColor);
      }
      if (mergeConfig.webcamBorderWidth !== undefined) {
        formData.append('webcam_border_width', String(mergeConfig.webcamBorderWidth));
      }

      log('info', 'Envoi en cours...');
      
      // Utilise le proxy Next.js qui redirige vers le backend
      const response = await fetch('/api/merge', {
        method: 'POST',
        body: formData,
      });
      
      log('info', `Reponse: ${response.status}`);

      if (response.ok) {
        const result = await response.json();
        log('success', `Video fusionnee: ${result.filename}`);
        log('info', `Disponible dans Fichiers`);
        log('action', 'Transcription en cours en arriere-plan...');
        log('info', 'La transcription sera disponible automatiquement');
        
        // Clean up
        setScreenBlob(null);
        setWebcamBlob(null);
        setRecordingState('idle');
        
        // Notifier que le traitement est terminé avec le nom du dossier et les options
        onProcessingComplete?.(result.folder || result.filename, config.autoProcess, config.autoIllustrate, config.layout);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
        throw new Error(errorData.detail || 'Erreur serveur');
      }
    } catch (err: any) {
      console.error('Merge error:', err);
      log('error', `Echec fusion: ${err.message || 'Erreur inconnue'}`);
      setRecordingState('idle');
    }
  }, [log, onProcessingComplete, screenBlob, webcamBlob, config.autoProcess, config.autoIllustrate, config.layout]);


  // Format duration
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Layout options
  const layouts: { id: LayoutMode; icon: React.ReactNode; label: string }[] = [
    { id: 'screen_only', icon: <Monitor className="w-5 h-5" />, label: 'Ecran seul' },
    { id: 'webcam_only', icon: <User className="w-5 h-5" />, label: 'Webcam seule' },
    { id: 'side_by_side', icon: <LayoutGrid className="w-5 h-5" />, label: 'Cote a cote' },
    { id: 'overlay', icon: <Layers className="w-5 h-5" />, label: 'Overlay' },
  ];

  // Controls only mode (for side panel)
  if (showControlsOnly) {
    return (
      <div className="space-y-3">
        {/* Layout Selection */}
        <div className="glass rounded-xl p-3">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-2">
            Layout
          </h3>
          <div className="grid grid-cols-4 gap-1.5">
            {layouts.map(({ id, icon, label }) => (
              <button
                key={id}
                onClick={() => setConfig({ ...config, layout: id })}
                disabled={recordingState !== 'idle'}
                className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-all ${
                  config.layout === id
                    ? 'bg-primary-600 text-white'
                    : 'bg-dark-800/50 text-dark-400 hover:bg-dark-700/50 hover:text-white'
                } disabled:opacity-50`}
              >
                {icon}
                <span className="text-[10px] font-medium leading-tight text-center">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Recording Controls */}
        <div className="glass rounded-xl p-3">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-2">
            Enregistrement
          </h3>
          
          {/* Toggle Buttons */}
          <div className="flex gap-2 mb-2">
            <button
              onClick={() => setConfig({ ...config, webcamEnabled: !config.webcamEnabled })}
              disabled={recordingState !== 'idle'}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs transition-all ${
                config.webcamEnabled
                  ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                  : 'bg-dark-800/50 text-dark-500 border border-dark-700'
              }`}
            >
              {config.webcamEnabled ? <Video className="w-3.5 h-3.5" /> : <VideoOff className="w-3.5 h-3.5" />}
              Webcam
            </button>
            
            <button
              onClick={() => setConfig({ ...config, micEnabled: !config.micEnabled })}
              disabled={recordingState !== 'idle'}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs transition-all ${
                config.micEnabled
                  ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                  : 'bg-dark-800/50 text-dark-500 border border-dark-700'
              }`}
            >
              {config.micEnabled ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
              Micro
            </button>
          </div>
          
          {/* Toggle Traitement Auto */}
          <div className="mb-2">
            <button
              onClick={() => setConfig({ ...config, autoProcess: !config.autoProcess })}
              className={`w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs transition-all ${
                config.autoProcess
                  ? 'bg-amber-600/20 text-amber-400 border border-amber-500/30'
                  : 'bg-dark-800/50 text-dark-500 border border-dark-700'
              }`}
            >
              {config.autoProcess ? <Zap className="w-3.5 h-3.5" /> : <ZapOff className="w-3.5 h-3.5" />}
              Traitement Auto {config.autoProcess ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Toggle Switch Auto (Canvas compositing) - seulement en mode overlay */}
          {config.layout === 'overlay' && (
            <div className="mb-2">
              <button
                onClick={() => setAutoSwitchEnabled(!autoSwitchEnabled)}
                className={`w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs transition-all ${
                  autoSwitchEnabled
                    ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                    : 'bg-dark-800/50 text-dark-500 border border-dark-700'
                }`}
                title="Switch automatiquement en webcam plein écran après 5s sans activité clavier/souris"
              >
                {autoSwitchEnabled ? <Camera className="w-3.5 h-3.5" /> : <Monitor className="w-3.5 h-3.5" />}
                Switch Auto {autoSwitchEnabled ? 'ON' : 'OFF'}
              </button>
              {autoSwitchEnabled && (
                <p className="text-[10px] text-dark-500 text-center mt-1">
                  Webcam plein écran après 5s sans activité
                </p>
              )}
            </div>
          )}

          {/* Audio Level */}
          {config.micEnabled && (
            <div className="mb-2 p-2 bg-dark-800/30 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Mic className="w-3 h-3 text-dark-400" />
                <div className="flex-1 h-2 bg-dark-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-75 rounded-full ${
                      audioLevel > 80 ? 'bg-red-500' : audioLevel > 50 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${audioLevel}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Volume2 className="w-3 h-3 text-dark-400" />
                <input
                  type="range"
                  min="0"
                  max="150"
                  value={config.micVolume}
                  onChange={(e) => setConfig({ ...config, micVolume: Number(e.target.value) })}
                  className="flex-1 accent-primary-500 h-1"
                />
                <span className="text-[10px] text-dark-500 w-8">{config.micVolume}%</span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {recordingState === 'idle' ? (
            <button
              onClick={startRecording}
              disabled={config.layout !== 'webcam_only' && !screenReady}
              className={`w-full py-2 text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition-all ${
                config.layout !== 'webcam_only' && !screenReady
                  ? 'bg-dark-700 text-dark-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white btn-glow'
              }`}
              title={config.layout !== 'webcam_only' && !screenReady ? 'Sélectionnez d\'abord un écran dans l\'aperçu' : ''}
            >
              <Circle className="w-4 h-4 fill-current" />
              {config.layout !== 'webcam_only' && !screenReady ? 'Selectionnez un ecran' : 'Demarrer'}
            </button>
          ) : recordingState === 'recording' ? (
            <button
              onClick={stopRecording}
              className="w-full py-2 bg-dark-700 hover:bg-dark-600 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition-all"
            >
              <Square className="w-4 h-4 fill-current" />
              Arreter ({formatDuration(duration)})
            </button>
          ) : (
            <button
              disabled
              className="w-full py-2 bg-dark-800 text-dark-400 text-sm font-semibold rounded-lg flex items-center justify-center gap-2"
            >
              <Loader2 className="w-4 h-4 animate-spin" />
              Traitement...
            </button>
          )}

        </div>

        {/* Webcam Options - Barre horizontale */}
        <div className="glass rounded-xl p-3">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-2">
            Options webcam
          </h3>
          
          {/* Barre horizontale avec tous les contrôles */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Taille */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-dark-400 whitespace-nowrap">Taille:</span>
              <input
                type="range"
                min="100"
                max="400"
                value={config.webcamSize}
                onChange={(e) => setConfig({ ...config, webcamSize: Number(e.target.value) })}
                disabled={recordingState !== 'idle'}
                className="w-24 accent-primary-500 h-1"
              />
              <span className="text-[10px] text-primary-500 font-bold w-8">{config.webcamSize}</span>
            </div>

            {/* Bord */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-dark-400 whitespace-nowrap">Bord:</span>
              <input
                type="range"
                min="0"
                max="15"
                value={config.webcamBorderWidth}
                onChange={(e) => setConfig({ ...config, webcamBorderWidth: Number(e.target.value) })}
                disabled={recordingState !== 'idle'}
                className="w-20 accent-primary-500 h-1"
              />
              <span className="text-[10px] text-primary-500 font-bold w-6">{config.webcamBorderWidth}</span>
            </div>

            {/* Couleur du bord */}
            <button
              onClick={() => {
                const colors = ['#FFB6C1', '#FF69B4', '#00D4FF', '#FFD700', '#FFFFFF', '#000000'];
                const currentIndex = colors.indexOf(config.webcamBorderColor);
                const nextColor = colors[(currentIndex + 1) % colors.length];
                setConfig({ ...config, webcamBorderColor: nextColor });
              }}
              disabled={recordingState !== 'idle'}
              className="w-8 h-8 rounded border-2 border-white/20"
              style={{ backgroundColor: config.webcamBorderColor }}
              title="Changer la couleur du bord"
            />

            {/* Forme */}
            <div className="flex gap-1">
              {(['circle', 'rounded', 'square'] as const).map((shape) => (
                <button
                  key={shape}
                  onClick={() => setConfig({ ...config, webcamShape: shape })}
                  disabled={recordingState !== 'idle'}
                  className={`w-9 h-9 rounded text-sm font-medium transition-all ${
                    config.webcamShape === shape
                      ? 'bg-primary-600 text-white'
                      : 'bg-dark-800/50 text-dark-400 hover:text-white'
                  } disabled:opacity-50`}
                >
                  {shape === 'circle' ? '●' : shape === 'rounded' ? '▢' : '■'}
                </button>
              ))}
            </div>

            {/* Coordonnées */}
            <div className="text-[10px] text-primary-500 font-bold ml-auto">
              {Math.round(config.webcamPosition.x)}%, {Math.round(config.webcamPosition.y)}%
            </div>

            {/* Boutons d'action */}
            <div className="flex gap-2 ml-auto">
              <button
                onClick={() => {
                  setConfig({
                    ...config,
                    webcamPosition: { x: 93, y: 88 },
                    webcamSize: 232,
                    webcamShape: 'rounded',
                    webcamBorderColor: '#8B5CF6',
                    webcamBorderWidth: 3,
                  });
                }}
                disabled={recordingState !== 'idle'}
                className="px-3 py-1.5 text-xs bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-all disabled:opacity-50"
              >
                Reset
              </button>
              <button
                onClick={() => {
                  // Les modifications sont déjà appliquées en temps réel
                }}
                disabled={recordingState !== 'idle'}
                className="px-3 py-1.5 text-xs bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-all disabled:opacity-50 flex items-center gap-1"
              >
                <Check className="w-3 h-3" />
                Appliquer
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-2 text-red-400 text-xs">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">

      {/* Preview Area */}
      <div className="glass rounded-xl p-3 md:p-4 flex-1">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm md:text-base font-semibold text-white">Apercu</h2>
            <span className="text-xs text-dark-500 bg-dark-700 px-2 py-0.5 rounded">16:9</span>
          </div>
          {recordingState === 'recording' && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full recording-indicator" />
              <span className="text-red-400 font-mono text-sm">{formatDuration(duration)}</span>
            </div>
          )}
        </div>

        {/* Preview Container - Format 16:9 YouTube */}
        <div 
          ref={previewContainerRef}
          className={`relative w-full aspect-video rounded-xl overflow-hidden video-preview ${
            config.layout === 'webcam_only' 
              ? 'bg-gradient-to-br from-purple-900 via-purple-950 to-black' 
              : 'bg-dark-900'
          }`}
        >
          {/* Screen Preview */}
          {config.layout !== 'webcam_only' && (
            <video
              ref={screenRef}
              autoPlay
              muted
              playsInline
              className={`absolute inset-0 w-full h-full object-contain ${
                config.layout === 'side_by_side' ? 'w-2/3' : ''
              }`}
            />
          )}

          {/* Webcam Preview */}
          {config.layout !== 'screen_only' && config.webcamEnabled && (
            <video
              ref={webcamRef}
              autoPlay
              muted
              playsInline
              onMouseDown={(e) => {
                // Activer le drag uniquement en mode overlay et si on est en idle
                if (config.layout === 'overlay' && recordingState === 'idle' && previewContainerRef.current) {
                  e.preventDefault();
                  e.stopPropagation();
                  setIsDraggingWebcam(true);
                  const rect = previewContainerRef.current.getBoundingClientRect();
                  dragStartRef.current = {
                    x: e.clientX,
                    y: e.clientY,
                    startX: config.webcamPosition.x,
                    startY: config.webcamPosition.y,
                  };
                  // Changer le curseur
                  if (webcamRef.current) {
                    webcamRef.current.style.cursor = 'grabbing';
                  }
                }
              }}
              className={`
                ${config.layout === 'webcam_only' 
                  ? 'absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[85%] h-[85%] object-cover rounded-3xl shadow-2xl shadow-purple-500/20' 
                  : config.layout === 'side_by_side'
                    ? 'absolute right-0 top-0 w-1/3 h-full object-cover'
                    : 'absolute'
                }
                ${config.layout !== 'webcam_only' && (config.webcamShape === 'circle' ? 'rounded-full' : config.webcamShape === 'rounded' ? 'rounded-2xl' : 'rounded-none')}
                ${config.layout === 'overlay' && recordingState === 'idle' ? 'cursor-grab active:cursor-grabbing' : ''}
              `}
              style={{
                ...(config.layout === 'webcam_only' ? {
                  // Webcam seule : rectangle avec coins arrondis, centré sur le fond dégradé
                  borderRadius: '24px',
                  boxShadow: '0 25px 50px -12px rgba(139, 92, 246, 0.3), 0 0 0 1px rgba(139, 92, 246, 0.1)',
                } : config.layout === 'overlay' ? {
                  width: `${config.webcamSize}px`,
                  height: `${config.webcamSize}px`,
                  objectFit: 'cover',
                  left: `${config.webcamPosition.x}%`,
                  top: `${config.webcamPosition.y}%`,
                  transform: 'translate(-50%, -50%)',
                  zIndex: 10, // Au-dessus du placeholder pour permettre le drag
                } : config.layout === 'side_by_side' ? {} : {
                  width: `${config.webcamSize}px`,
                  height: `${config.webcamSize}px`,
                  objectFit: 'cover',
                  bottom: '16px',
                  right: '16px',
                  zIndex: 10,
                }),
                ...(config.layout !== 'webcam_only' && {
                  borderWidth: `${config.webcamBorderWidth}px`,
                  borderStyle: 'solid',
                  borderColor: config.webcamBorderColor,
                }),
                boxSizing: 'border-box',
              }}
            />
          )}

          {/* Placeholder when no stream - Clickable */}
          {!screenReady && config.layout !== 'webcam_only' && recordingState === 'idle' && (
            <div 
              className="absolute inset-0 flex items-center justify-center cursor-pointer hover:bg-white/5 transition-all group z-0"
              onClick={(e) => {
                // Ne pas sélectionner l'écran si on est en train de drag la webcam ou si on clique sur la webcam
                if (!isDraggingWebcam && webcamRef.current) {
                  const webcamRect = webcamRef.current.getBoundingClientRect();
                  const clickX = e.clientX;
                  const clickY = e.clientY;
                  
                  // Vérifier si le clic est sur la webcam
                  if (config.layout === 'overlay' && 
                      clickX >= webcamRect.left && 
                      clickX <= webcamRect.right &&
                      clickY >= webcamRect.top && 
                      clickY <= webcamRect.bottom) {
                    return; // Ne pas sélectionner l'écran si on clique sur la webcam
                  }
                  
                  initScreen();
                }
              }}
            >
              <div className="text-center">
                <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-dark-700/50 flex items-center justify-center group-hover:bg-primary-600/20 group-hover:scale-110 transition-all">
                  <Monitor className="w-10 h-10 text-dark-400 group-hover:text-primary-400 transition-colors" />
                </div>
                <p className="text-dark-300 font-medium group-hover:text-white transition-colors">
                  Cliquez ici pour selectionner l'ecran
                </p>
                <p className="text-dark-500 text-sm mt-1">ou une fenetre a enregistrer</p>
              </div>
            </div>
          )}

          {/* Start Recording Button - Centered Overlay */}
          {recordingState === 'idle' && (screenReady || config.layout === 'webcam_only') && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-[2px]">
              <button
                onClick={startRecording}
                className="group flex flex-col items-center gap-4 p-8 rounded-3xl bg-red-600/90 hover:bg-red-500 hover:scale-105 transition-all duration-300 shadow-2xl"
              >
                <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center group-hover:bg-white/30 transition-colors">
                  <Circle className="w-10 h-10 text-white fill-current" />
                </div>
                <span className="text-white font-bold text-xl uppercase tracking-wide">
                  Demarrer
                </span>
              </button>
            </div>
          )}

          {/* Countdown Overlay */}
          {recordingState === 'countdown' && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
              <div className="text-center">
                <div className="w-40 h-40 mx-auto rounded-full bg-red-600/90 flex items-center justify-center animate-pulse shadow-2xl shadow-red-600/50">
                  <span className="text-8xl font-bold text-white">{countdown}</span>
                </div>
                <p className="text-white/80 text-xl mt-6 font-medium">
                  Preparation...
                </p>
              </div>
            </div>
          )}

          {/* Recording Indicator Overlay */}
          {recordingState === 'recording' && (
            <div className="absolute top-4 left-4 flex items-center gap-3 bg-black/60 backdrop-blur-sm px-4 py-2 rounded-full">
              <div className="w-4 h-4 bg-red-500 rounded-full recording-indicator" />
              <span className="text-white font-mono font-bold">{formatDuration(duration)}</span>
              <button
                onClick={stopRecording}
                className="ml-2 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
                title="Arreter"
              >
                <Square className="w-5 h-5 text-white fill-current" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Controls - Only shown when inline mode */}
      {showControlsInline && (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 md:gap-4 shrink-0">
        {/* Layout Selection */}
        <div className="glass rounded-xl p-3 md:p-4">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-3">
            Layout
          </h3>
          <div className="grid grid-cols-4 md:grid-cols-2 gap-1.5">
            {layouts.map(({ id, icon, label }) => (
              <button
                key={id}
                onClick={() => setConfig({ ...config, layout: id })}
                disabled={recordingState !== 'idle'}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all ${
                  config.layout === id
                    ? 'bg-primary-600 text-white'
                    : 'bg-dark-800/50 text-dark-400 hover:bg-dark-700/50 hover:text-white'
                } disabled:opacity-50`}
              >
                {icon}
                <span className="text-xs font-medium">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Recording Controls */}
        <div className="glass rounded-xl p-3 md:p-4">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-3">
            Enregistrement
          </h3>
          
          {/* Toggle Buttons */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setConfig({ ...config, webcamEnabled: !config.webcamEnabled })}
              disabled={recordingState !== 'idle'}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl transition-all ${
                config.webcamEnabled
                  ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                  : 'bg-dark-800/50 text-dark-500 border border-dark-700'
              }`}
            >
              {config.webcamEnabled ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
              <span className="text-sm">Webcam</span>
            </button>
            
            <button
              onClick={() => setConfig({ ...config, micEnabled: !config.micEnabled })}
              disabled={recordingState !== 'idle'}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl transition-all ${
                config.micEnabled
                  ? 'bg-green-600/20 text-green-400 border border-green-500/30'
                  : 'bg-dark-800/50 text-dark-500 border border-dark-700'
              }`}
            >
              {config.micEnabled ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
              <span className="text-sm">Micro</span>
            </button>
          </div>

          {/* Audio Level Meter & Volume Control */}
          {config.micEnabled && (
            <div className="mb-4 p-3 bg-dark-800/30 rounded-xl border border-dark-700">
              {/* Device selector */}
              {audioDevices.length > 1 && (
                <div className="mb-3">
                  <select
                    value={selectedAudioDevice}
                    onChange={(e) => {
                      setSelectedAudioDevice(e.target.value);
                      stopAudio();
                      setTimeout(() => initAudio(), 100);
                    }}
                    className="w-full bg-dark-700 text-white text-sm rounded-lg px-3 py-2 border border-dark-600 focus:border-primary-500 focus:outline-none"
                  >
                    {audioDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              {/* VU Meter */}
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-1">
                  <Mic className="w-3 h-3 text-dark-400" />
                  <span className="text-xs text-dark-400">Niveau audio</span>
                </div>
                <div className="h-3 bg-dark-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-75 rounded-full ${
                      audioLevel > 80 ? 'bg-red-500' : 
                      audioLevel > 50 ? 'bg-yellow-500' : 
                      'bg-green-500'
                    }`}
                    style={{ width: `${audioLevel}%` }}
                  />
                </div>
              </div>
              
              {/* Volume Control */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {config.micVolume === 0 ? (
                      <VolumeX className="w-3 h-3 text-dark-400" />
                    ) : (
                      <Volume2 className="w-3 h-3 text-dark-400" />
                    )}
                    <span className="text-xs text-dark-400">Volume</span>
                  </div>
                  <span className="text-xs text-dark-500">{config.micVolume}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="150"
                  value={config.micVolume}
                  onChange={(e) => setConfig({ ...config, micVolume: Number(e.target.value) })}
                  className="w-full accent-primary-500 h-2"
                />
              </div>
            </div>
          )}

          {/* Main Action Button */}
          {recordingState === 'idle' ? (
            <button
              onClick={startRecording}
              disabled={config.layout !== 'webcam_only' && !screenReady}
              className={`w-full py-2.5 text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition-all ${
                config.layout !== 'webcam_only' && !screenReady
                  ? 'bg-dark-700 text-dark-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white btn-glow'
              }`}
            >
              <Circle className="w-4 h-4 fill-current" />
              {config.layout !== 'webcam_only' && !screenReady ? 'Selectionnez un ecran' : 'Demarrer'}
            </button>
          ) : recordingState === 'recording' ? (
            <button
              onClick={stopRecording}
              className="w-full py-2.5 bg-dark-700 hover:bg-dark-600 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition-all"
            >
              <Square className="w-4 h-4 fill-current" />
              Arreter ({formatDuration(duration)})
            </button>
          ) : (
            <button
              disabled
              className="w-full py-2.5 bg-dark-800 text-dark-400 text-sm font-semibold rounded-lg flex items-center justify-center gap-2"
            >
              <Loader2 className="w-4 h-4 animate-spin" />
              Traitement...
            </button>
          )}

        </div>

        {/* Webcam Settings - Barre horizontale */}
        <div className="glass rounded-xl p-3 md:p-4 md:col-span-2 xl:col-span-1">
          <h3 className="text-xs font-semibold text-dark-300 uppercase tracking-wider mb-3">
            Options webcam
          </h3>
          
          {/* Barre horizontale avec tous les contrôles */}
          <div className="flex items-center gap-4 flex-wrap">
            {/* Taille */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-white whitespace-nowrap">Taille:</span>
              <input
                type="range"
                min="100"
                max="400"
                value={config.webcamSize}
                onChange={(e) => setConfig({ ...config, webcamSize: Number(e.target.value) })}
                disabled={recordingState !== 'idle'}
                className="w-32 accent-primary-500 h-1"
              />
              <span className="text-xs text-primary-500 font-bold w-10">{config.webcamSize}</span>
            </div>

            {/* Bord */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-white whitespace-nowrap">Bord:</span>
              <input
                type="range"
                min="0"
                max="15"
                value={config.webcamBorderWidth}
                onChange={(e) => setConfig({ ...config, webcamBorderWidth: Number(e.target.value) })}
                disabled={recordingState !== 'idle'}
                className="w-24 accent-primary-500 h-1"
              />
              <span className="text-xs text-primary-500 font-bold w-6">{config.webcamBorderWidth}</span>
            </div>

            {/* Couleur du bord */}
            <button
              onClick={() => {
                const colors = ['#FFB6C1', '#FF69B4', '#00D4FF', '#FFD700', '#FFFFFF', '#000000'];
                const currentIndex = colors.indexOf(config.webcamBorderColor);
                const nextColor = colors[(currentIndex + 1) % colors.length];
                setConfig({ ...config, webcamBorderColor: nextColor });
              }}
              disabled={recordingState !== 'idle'}
              className="w-10 h-10 rounded border-2 border-white/20 hover:border-white/40 transition-all disabled:opacity-50"
              style={{ backgroundColor: config.webcamBorderColor }}
              title="Changer la couleur du bord"
            />

            {/* Forme */}
            <div className="flex gap-1.5">
              {(['circle', 'rounded', 'square'] as const).map((shape) => (
                <button
                  key={shape}
                  onClick={() => setConfig({ ...config, webcamShape: shape })}
                  disabled={recordingState !== 'idle'}
                  className={`w-11 h-11 rounded text-base font-medium transition-all ${
                    config.webcamShape === shape
                      ? 'bg-primary-600 text-white'
                      : 'bg-dark-800/50 text-dark-400 hover:text-white'
                  } disabled:opacity-50`}
                >
                  {shape === 'circle' ? '●' : shape === 'rounded' ? '▢' : '■'}
                </button>
              ))}
            </div>

            {/* Coordonnées */}
            <div className="text-xs text-primary-500 font-bold ml-auto">
              {Math.round(config.webcamPosition.x)}%, {Math.round(config.webcamPosition.y)}%
            </div>

            {/* Boutons d'action */}
            <div className="flex gap-2 ml-auto">
              <button
                onClick={() => {
                  setConfig({
                    ...config,
                    webcamPosition: { x: 93, y: 88 },
                    webcamSize: 232,
                    webcamShape: 'rounded',
                    webcamBorderColor: '#8B5CF6',
                    webcamBorderWidth: 3,
                  });
                }}
                disabled={recordingState !== 'idle'}
                className="px-4 py-2 text-xs bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-all disabled:opacity-50"
              >
                Reset
              </button>
              <button
                disabled={recordingState !== 'idle'}
                className="px-4 py-2 text-xs bg-primary-600 hover:bg-primary-500 text-white rounded-lg transition-all disabled:opacity-50 flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                Appliquer
              </button>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Error Display */}
      {error && showControlsInline && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}

    </div>
  );
}

