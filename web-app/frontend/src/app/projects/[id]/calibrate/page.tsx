'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Save, 
  RotateCcw, 
  Circle, 
  Square, 
  RectangleHorizontal,
  Move,
  Maximize2,
  Palette,
  Play,
  Pause,
  SkipBack,
  SkipForward
} from 'lucide-react';

interface CalibrateConfig {
  layout: string;
  webcam_x: number;
  webcam_y: number;
  webcam_size: number;
  webcam_shape: string;
  border_color: string;
  border_width: number;
}

interface Project {
  _id: string;
  name: string;
  folder_name: string;
}

export default function CalibratePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  const [config, setConfig] = useState<CalibrateConfig>({
    layout: 'overlay',
    webcam_x: 1486,
    webcam_y: 645,
    webcam_size: 389,
    webcam_shape: 'rounded',
    border_color: '#FFB6C1',
    border_width: 4
  });
  
  // États pour le drag
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Refs et états pour les vidéos
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const webcamVideoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  
  // Dimensions de référence (1920x1080)
  const CANVAS_WIDTH = 1920;
  const CANVAS_HEIGHT = 1080;
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  // Charger le projet et la config
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        // Charger le projet
        const projectRes = await fetch(`${API_URL}/api/projects/${projectId}`);
        if (projectRes.ok) {
          const projectData = await projectRes.json();
          setProject(projectData);
        }
        
        // Charger la config existante
        const configRes = await fetch(`${API_URL}/api/projects/${projectId}/config`);
        if (configRes.ok) {
          const configData = await configRes.json();
          if (configData.exists && configData.config) {
            setConfig(configData.config);
          }
        }
      } catch (err) {
        console.error('Erreur chargement:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [projectId, API_URL]);

  // Sauvegarder la configuration
  const saveConfig = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!res.ok) throw new Error('Erreur sauvegarde');
      
      alert('Configuration sauvegardée ! Cliquez sur "Appliquer" pour régénérer les vidéos.');
    } catch (err) {
      alert('Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  // Appliquer le calibrage (sauvegarde + relance les étapes de fusion)
  const applyCalibration = async () => {
    if (!confirm('Appliquer le calibrage ?\n\nCela va:\n1. Sauvegarder la configuration\n2. Relancer les étapes 1→3 (merge, silence, cut)\n3. Relancer l\'étape 7 (intégration B-roll)\n\nLes vidéos seront régénérées avec la nouvelle position.')) return;
    
    setApplying(true);
    try {
      // 1. Sauvegarder la config
      const saveRes = await fetch(`${API_URL}/api/projects/${projectId}/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!saveRes.ok) throw new Error('Erreur sauvegarde config');
      
      // 2. Relancer les étapes 1 à 3 (merge, silence, cut)
      const step1Res = await fetch(`${API_URL}/api/projects/${projectId}/start?start_step=1&end_step=3`, {
        method: 'POST'
      });
      
      if (!step1Res.ok) throw new Error('Erreur relance étapes 1-3');
      
      alert('Calibrage appliqué ! Les étapes 1-3 sont en cours de traitement.\n\nUne fois terminé, relancez l\'étape 7 depuis la page du projet pour régénérer illustrated.mp4');
      router.push(`/projects/${projectId}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur lors de l\'application');
    } finally {
      setApplying(false);
    }
  };

  // Réinitialiser aux valeurs par défaut
  const resetConfig = () => {
    setConfig({
      layout: 'overlay',
      webcam_x: 1486,
      webcam_y: 645,
      webcam_size: 389,
      webcam_shape: 'rounded',
      border_color: '#FFB6C1',
      border_width: 4
    });
  };

  // Gestion du drag de la webcam
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const scaleX = CANVAS_WIDTH / rect.width;
    const scaleY = CANVAS_HEIGHT / rect.height;
    
    setIsDragging(true);
    setDragStart({
      x: e.clientX - (config.webcam_x / scaleX),
      y: e.clientY - (config.webcam_y / scaleY)
    });
  }, [config.webcam_x, config.webcam_y]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const scaleX = CANVAS_WIDTH / rect.width;
    const scaleY = CANVAS_HEIGHT / rect.height;
    
    let newX = (e.clientX - dragStart.x) * scaleX;
    let newY = (e.clientY - dragStart.y) * scaleY;
    
    // Limiter aux bords
    newX = Math.max(0, Math.min(newX, CANVAS_WIDTH - config.webcam_size));
    newY = Math.max(0, Math.min(newY, CANVAS_HEIGHT - config.webcam_size));
    
    setConfig(prev => ({
      ...prev,
      webcam_x: Math.round(newX),
      webcam_y: Math.round(newY)
    }));
  }, [isDragging, dragStart, config.webcam_size]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Calculer le style de la webcam
  const getWebcamStyle = () => {
    if (!containerRef.current) return {};
    
    const rect = containerRef.current.getBoundingClientRect();
    const scaleX = rect.width / CANVAS_WIDTH;
    const scaleY = rect.height / CANVAS_HEIGHT;
    
    const style: React.CSSProperties = {
      position: 'absolute',
      left: config.webcam_x * scaleX,
      top: config.webcam_y * scaleY,
      width: config.webcam_size * scaleX,
      height: config.webcam_size * scaleY,
      border: `${config.border_width}px solid ${config.border_color}`,
      cursor: isDragging ? 'grabbing' : 'grab',
      transition: isDragging ? 'none' : 'border-radius 0.2s',
      overflow: 'hidden',
      boxSizing: 'border-box'
    };
    
    // Forme
    if (config.webcam_shape === 'circle') {
      style.borderRadius = '50%';
    } else if (config.webcam_shape === 'rounded') {
      style.borderRadius = '16px';
    } else {
      style.borderRadius = '0';
    }
    
    return style;
  };

  // Contrôles vidéo
  const togglePlay = () => {
    if (screenVideoRef.current && webcamVideoRef.current) {
      if (isPlaying) {
        screenVideoRef.current.pause();
        webcamVideoRef.current.pause();
      } else {
        screenVideoRef.current.play();
        webcamVideoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (screenVideoRef.current && webcamVideoRef.current) {
      screenVideoRef.current.currentTime = time;
      webcamVideoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const skipTime = (seconds: number) => {
    if (screenVideoRef.current && webcamVideoRef.current) {
      const newTime = Math.max(0, Math.min(screenVideoRef.current.currentTime + seconds, duration));
      screenVideoRef.current.currentTime = newTime;
      webcamVideoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <div className="bg-zinc-900/80 border-b border-white/10 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <Link 
              href={`/projects/${projectId}`}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-white">Calibrage webcam</h1>
              <p className="text-sm text-zinc-400">{project?.name || 'Projet'}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={resetConfig}
              className="btn-secondary flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Réinitialiser
            </button>
            <button
              onClick={saveConfig}
              disabled={saving || applying}
              className="btn-secondary flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Sauvegarde...' : 'Sauvegarder'}
            </button>
            <button
              onClick={applyCalibration}
              disabled={saving || applying}
              className="btn-primary flex items-center gap-2 bg-green-600 hover:bg-green-500"
            >
              <Play className="w-4 h-4" />
              {applying ? 'Application...' : 'Appliquer'}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 space-y-4">
        
        {/* Zone d'aperçu - Pleine largeur */}
        <div className="bg-zinc-900 rounded-xl border border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-zinc-400 flex items-center gap-2">
              <Move className="w-4 h-4" />
              Aperçu - Glissez la webcam pour la positionner
            </h2>
            <div className="text-xs text-zinc-500 font-mono">
              X: {config.webcam_x} | Y: {config.webcam_y} | Taille: {config.webcam_size}px
            </div>
          </div>
          
          {/* Container de prévisualisation */}
          <div 
            ref={containerRef}
            className="relative bg-zinc-800 rounded-lg overflow-hidden select-none"
            style={{ aspectRatio: '16/9' }}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Vidéo de fond (screen) */}
            {project && (
              <video 
                ref={screenVideoRef}
                src={`${API_URL}/output/${project.folder_name}/screen.mp4`}
                className="w-full h-full object-cover"
                autoPlay
                loop
                muted
                playsInline
                onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              />
            )}
            
            {/* Grille de référence */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="w-full h-full grid grid-cols-3 grid-rows-3">
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="border border-white/5" />
                ))}
              </div>
            </div>
            
            {/* Webcam overlay - affiché pour overlay et side_by_side */}
            {(config.layout === 'overlay' || config.layout === 'side_by_side' || config.layout === 'side-by-side') && (
              <div
                style={getWebcamStyle()}
                onMouseDown={handleMouseDown}
                className="flex items-center justify-center overflow-hidden"
              >
                {/* Vidéo webcam */}
                {project && (
                  <video 
                    ref={webcamVideoRef}
                    src={`${API_URL}/output/${project.folder_name}/webcam.mp4`}
                    className="w-full h-full object-cover pointer-events-none"
                    style={{ 
                      borderRadius: config.webcam_shape === 'circle' ? '50%' : 
                                    config.webcam_shape === 'rounded' ? '12px' : '0'
                    }}
                    autoPlay
                    loop
                    muted
                    playsInline
                  />
                )}
              </div>
            )}
          </div>

          {/* Contrôles vidéo */}
          <div className="mt-4 bg-zinc-800 rounded-lg p-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => skipTime(-5)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
                title="Reculer 5s"
              >
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={togglePlay}
                className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
              <button
                onClick={() => skipTime(5)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
                title="Avancer 5s"
              >
                <SkipForward className="w-4 h-4" />
              </button>
              <span className="text-xs text-zinc-400 font-mono min-w-[45px]">
                {formatTime(currentTime)}
              </span>
              <input
                type="range"
                min="0"
                max={duration || 100}
                step="0.1"
                value={currentTime}
                onChange={handleSeek}
                className="flex-1 accent-indigo-500 h-1"
              />
              <span className="text-xs text-zinc-400 font-mono min-w-[45px]">
                {formatTime(duration)}
              </span>
            </div>
          </div>
        </div>

        {/* Outils - Sur une ligne */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          
          {/* Layout */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Layout</h3>
            <div className="flex gap-1">
              {[
                { value: 'overlay', icon: <Circle className="w-4 h-4" /> },
                { value: 'side-by-side', icon: <RectangleHorizontal className="w-4 h-4" /> },
                { value: 'webcam-only', icon: <Square className="w-4 h-4" /> }
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setConfig({...config, layout: opt.value})}
                  className={`flex-1 flex items-center justify-center p-2 rounded-lg transition ${
                    config.layout === opt.value
                      ? 'bg-indigo-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  }`}
                  title={opt.value}
                >
                  {opt.icon}
                </button>
              ))}
            </div>
          </div>

          {/* Forme */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Forme</h3>
            <div className="flex gap-1">
              {[
                { value: 'circle', icon: <div className="w-5 h-5 rounded-full border-2 border-current" /> },
                { value: 'rounded', icon: <div className="w-5 h-5 rounded-md border-2 border-current" /> },
                { value: 'square', icon: <div className="w-5 h-5 border-2 border-current" /> }
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setConfig({...config, webcam_shape: opt.value})}
                  className={`flex-1 flex items-center justify-center p-2 rounded-lg transition ${
                    config.webcam_shape === opt.value
                      ? 'bg-indigo-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                  }`}
                  title={opt.value}
                >
                  {opt.icon}
                </button>
              ))}
            </div>
          </div>

          {/* Position X */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Position X</h3>
            <input
              type="range"
              min="0"
              max={CANVAS_WIDTH - config.webcam_size}
              value={config.webcam_x}
              onChange={(e) => setConfig({...config, webcam_x: parseInt(e.target.value)})}
              className="w-full accent-indigo-500"
            />
            <input
              type="number"
              value={config.webcam_x}
              onChange={(e) => setConfig({...config, webcam_x: parseInt(e.target.value) || 0})}
              className="w-full mt-1 bg-zinc-800 border border-white/10 rounded px-2 py-1 text-xs text-white"
            />
          </div>

          {/* Position Y */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Position Y</h3>
            <input
              type="range"
              min="0"
              max={CANVAS_HEIGHT - config.webcam_size}
              value={config.webcam_y}
              onChange={(e) => setConfig({...config, webcam_y: parseInt(e.target.value)})}
              className="w-full accent-indigo-500"
            />
            <input
              type="number"
              value={config.webcam_y}
              onChange={(e) => setConfig({...config, webcam_y: parseInt(e.target.value) || 0})}
              className="w-full mt-1 bg-zinc-800 border border-white/10 rounded px-2 py-1 text-xs text-white"
            />
          </div>

          {/* Taille */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Taille</h3>
            <input
              type="range"
              min="100"
              max="600"
              value={config.webcam_size}
              onChange={(e) => setConfig({...config, webcam_size: parseInt(e.target.value)})}
              className="w-full accent-indigo-500"
            />
            <input
              type="number"
              value={config.webcam_size}
              onChange={(e) => setConfig({...config, webcam_size: parseInt(e.target.value) || 100})}
              className="w-full mt-1 bg-zinc-800 border border-white/10 rounded px-2 py-1 text-xs text-white"
            />
          </div>

          {/* Bordure */}
          <div className="bg-zinc-900 rounded-xl border border-white/10 p-3 col-span-2 md:col-span-1">
            <h3 className="text-xs font-medium text-zinc-400 mb-2">Bordure</h3>
            <div className="flex gap-2 items-center mb-2">
              <input
                type="color"
                value={config.border_color}
                onChange={(e) => setConfig({...config, border_color: e.target.value})}
                className="w-8 h-8 rounded cursor-pointer border-0"
              />
              <input
                type="range"
                min="0"
                max="20"
                value={config.border_width}
                onChange={(e) => setConfig({...config, border_width: parseInt(e.target.value)})}
                className="flex-1 accent-indigo-500"
              />
              <span className="text-xs text-zinc-500 w-8">{config.border_width}px</span>
            </div>
            <div className="flex gap-1 flex-wrap">
              {['#FFB6C1', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#FFFFFF', '#000000'].map(color => (
                <button
                  key={color}
                  onClick={() => setConfig({...config, border_color: color})}
                  className={`w-5 h-5 rounded-full border-2 transition ${
                    config.border_color === color ? 'border-white scale-110' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Position rapide */}
        <div className="bg-zinc-900 rounded-xl border border-white/10 p-3">
          <div className="flex items-center gap-4">
            <h3 className="text-xs font-medium text-zinc-400 whitespace-nowrap">Position rapide</h3>
            <div className="flex gap-1">
              {[
                { label: '↖', x: 50, y: 50 },
                { label: '↑', x: (CANVAS_WIDTH - config.webcam_size) / 2, y: 50 },
                { label: '↗', x: CANVAS_WIDTH - config.webcam_size - 50, y: 50 },
                { label: '←', x: 50, y: (CANVAS_HEIGHT - config.webcam_size) / 2 },
                { label: '⊙', x: (CANVAS_WIDTH - config.webcam_size) / 2, y: (CANVAS_HEIGHT - config.webcam_size) / 2 },
                { label: '→', x: CANVAS_WIDTH - config.webcam_size - 50, y: (CANVAS_HEIGHT - config.webcam_size) / 2 },
                { label: '↙', x: 50, y: CANVAS_HEIGHT - config.webcam_size - 50 },
                { label: '↓', x: (CANVAS_WIDTH - config.webcam_size) / 2, y: CANVAS_HEIGHT - config.webcam_size - 50 },
                { label: '↘', x: CANVAS_WIDTH - config.webcam_size - 50, y: CANVAS_HEIGHT - config.webcam_size - 50 }
              ].map((pos, i) => (
                <button
                  key={i}
                  onClick={() => setConfig({...config, webcam_x: Math.round(pos.x), webcam_y: Math.round(pos.y)})}
                  className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded text-zinc-400 hover:text-white transition text-lg"
                >
                  {pos.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

