'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  X, 
  Download, 
  Merge, 
  Loader2,
  Move,
  Circle,
  Square,
  RectangleHorizontal
} from 'lucide-react';

interface MergePreviewProps {
  screenBlob: Blob;
  webcamBlob: Blob | null;
  layout: string;
  webcamPosition?: { x: number; y: number };
  webcamSize?: number;
  webcamShape?: 'circle' | 'rounded' | 'square';
  webcamBorderColor?: string;
  webcamBorderWidth?: number;
  onMerge: (config: MergeConfig) => void;
  onCancel: () => void;
  onLog?: (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => void;
}

interface MergeConfig {
  layout: string;
  webcamX: number;
  webcamY: number;
  webcamSize: number;
  webcamShape: 'circle' | 'rounded' | 'square';
  webcamBorderColor?: string;
  webcamBorderWidth?: number;
}

export function MergePreview({ 
  screenBlob, 
  webcamBlob, 
  layout,
  webcamPosition = { x: 50, y: 50 },
  webcamSize: initialWebcamSize = 200,
  webcamShape: initialWebcamShape = 'circle',
  webcamBorderColor: initialWebcamBorderColor = '#FFB6C1',
  webcamBorderWidth: initialWebcamBorderWidth = 4,
  onMerge, 
  onCancel,
  onLog 
}: MergePreviewProps) {
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const webcamVideoRef = useRef<HTMLVideoElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  
  const [screenUrl, setScreenUrl] = useState<string>('');
  const [webcamUrl, setWebcamUrl] = useState<string>('');
  const [merging, setMerging] = useState(false);
  
  // Webcam config - initialisé avec les valeurs de la config
  const [webcamX, setWebcamX] = useState(0);
  const [webcamY, setWebcamY] = useState(0);
  const [webcamSize, setWebcamSize] = useState(initialWebcamSize);
  const [webcamShape, setWebcamShape] = useState<'circle' | 'rounded' | 'square'>(initialWebcamShape);
  const [webcamBorderColor, setWebcamBorderColor] = useState(initialWebcamBorderColor);
  const [webcamBorderWidth, setWebcamBorderWidth] = useState(initialWebcamBorderWidth);
  
  // Drag state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const log = (type: 'info' | 'success' | 'warning' | 'error' | 'action', message: string) => {
    onLog?.(type, message);
  };

  // Initialize position from config (convert percentage to pixels)
  useEffect(() => {
    if (previewRef.current && layout === 'overlay') {
      const updatePosition = () => {
        const rect = previewRef.current?.getBoundingClientRect();
        if (!rect) return;
        // Convertir les pourcentages en pixels (position centrée)
        const centerX = (webcamPosition.x / 100) * rect.width;
        const centerY = (webcamPosition.y / 100) * rect.height;
        const x = centerX - (webcamSize / 2);
        const y = centerY - (webcamSize / 2);
        setWebcamX(Math.max(0, Math.min(x, rect.width - webcamSize)));
        setWebcamY(Math.max(0, Math.min(y, rect.height - webcamSize)));
      };
      
      updatePosition();
      // Réinitialiser quand la taille change
      const resizeObserver = new ResizeObserver(updatePosition);
      resizeObserver.observe(previewRef.current);
      
      return () => resizeObserver.disconnect();
    }
  }, [layout, webcamPosition.x, webcamPosition.y, webcamSize]);

  // Create object URLs for videos
  useEffect(() => {
    const sUrl = URL.createObjectURL(screenBlob);
    setScreenUrl(sUrl);
    log('info', `Video ecran: ${(screenBlob.size / 1024 / 1024).toFixed(2)} MB`);
    
    if (webcamBlob) {
      const wUrl = URL.createObjectURL(webcamBlob);
      setWebcamUrl(wUrl);
      log('info', `Video webcam: ${(webcamBlob.size / 1024 / 1024).toFixed(2)} MB`);
    }
    
    return () => {
      URL.revokeObjectURL(sUrl);
      if (webcamBlob) URL.revokeObjectURL(webcamUrl);
    };
  }, [screenBlob, webcamBlob]);

  // Handle drag
  const handleMouseDown = (e: React.MouseEvent) => {
    if (layout !== 'overlay') return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - webcamX, y: e.clientY - webcamY });
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !previewRef.current) return;
    
    const rect = previewRef.current.getBoundingClientRect();
    const maxX = rect.width - webcamSize;
    const maxY = rect.height - webcamSize;
    
    let newX = e.clientX - dragStart.x;
    let newY = e.clientY - dragStart.y;
    
    // Constrain to preview bounds
    newX = Math.max(0, Math.min(newX, maxX));
    newY = Math.max(0, Math.min(newY, maxY));
    
    setWebcamX(newX);
    setWebcamY(newY);
  }, [isDragging, dragStart, webcamSize]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Position presets
  const positionPresets = [
    { x: 20, y: 20, label: '↖' },
    { x: -1, y: 20, label: '↗' },  // -1 means calculate from right
    { x: 20, y: -1, label: '↙' },  // -1 means calculate from bottom
    { x: -1, y: -1, label: '↘' },
  ];

  const applyPreset = (preset: { x: number; y: number }) => {
    if (!previewRef.current) return;
    const rect = previewRef.current.getBoundingClientRect();
    
    const x = preset.x === -1 ? rect.width - webcamSize - 20 : preset.x;
    const y = preset.y === -1 ? rect.height - webcamSize - 20 : preset.y;
    
    setWebcamX(x);
    setWebcamY(y);
  };

  const handleMerge = () => {
    setMerging(true);
    log('action', 'Lancement de la fusion...');
    log('info', `Position: x=${webcamX}, y=${webcamY}, taille=${webcamSize}, forme=${webcamShape}, bordure=${webcamBorderWidth}px`);
    
    // Convert preview coordinates to 1920x1080
    let finalX = webcamX;
    let finalY = webcamY;
    
    if (previewRef.current && layout === 'overlay') {
      const rect = previewRef.current.getBoundingClientRect();
      const scaleX = 1920 / rect.width;
      const scaleY = 1080 / rect.height;
      // Convertir la position centrée en position absolue
      const centerX = webcamX + (webcamSize / 2);
      const centerY = webcamY + (webcamSize / 2);
      finalX = Math.round(centerX * scaleX - (webcamSize / 2));
      finalY = Math.round(centerY * scaleY - (webcamSize / 2));
    }
    
    onMerge({
      layout,
      webcamX: finalX,
      webcamY: finalY,
      webcamSize: webcamSize,
      webcamShape,
      webcamBorderColor,
      webcamBorderWidth
    });
  };

  const downloadVideo = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
    log('success', `${name} telecharge`);
  };

  return (
    <div className="fixed inset-y-0 left-0 right-0 lg:right-[420px] xl:right-[480px] 2xl:right-[520px] bg-black/90 backdrop-blur-sm z-40 flex items-center justify-center p-4">
      <div className="bg-dark-900 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
          <div>
            <h2 className="text-lg font-semibold text-white">Prévisualisation</h2>
            <p className="text-sm text-dark-400">Positionnez la webcam puis fusionnez</p>
          </div>
          <button
            onClick={onCancel}
            className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Preview */}
          <div className="flex-1 p-4">
            <div 
              ref={previewRef}
              className="relative w-full aspect-video bg-dark-800 rounded-xl overflow-hidden"
            >
              {/* Screen video */}
              <video
                ref={screenVideoRef}
                src={screenUrl}
                className="absolute inset-0 w-full h-full object-contain"
                autoPlay
                loop
                muted
              />
              
              {/* Webcam overlay */}
              {webcamUrl && layout === 'overlay' && (
                <div
                  className={`absolute cursor-move transition-shadow ${
                    isDragging ? 'shadow-2xl ring-2 ring-primary-500' : ''
                  }`}
                  style={{
                    left: webcamX,
                    top: webcamY,
                    width: webcamSize,
                    height: webcamSize,
                  }}
                  onMouseDown={handleMouseDown}
                >
                  <video
                    ref={webcamVideoRef}
                    src={webcamUrl}
                    className={`w-full h-full object-cover border-4 border-pink-400 ${
                      webcamShape === 'circle' ? 'rounded-full' : 
                      webcamShape === 'rounded' ? 'rounded-2xl' : ''
                    }`}
                    autoPlay
                    loop
                    muted
                  />
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                    <Move className="w-8 h-8 text-white drop-shadow-lg" />
                  </div>
                </div>
              )}

              {/* Side by side preview */}
              {webcamUrl && layout === 'side_by_side' && (
                <div className="absolute right-0 top-0 w-1/3 h-full bg-dark-900 flex items-center justify-center">
                  <video
                    src={webcamUrl}
                    className={`w-4/5 aspect-square object-cover border-4 border-pink-400 ${
                      webcamShape === 'circle' ? 'rounded-full' : 
                      webcamShape === 'rounded' ? 'rounded-2xl' : ''
                    }`}
                    autoPlay
                    loop
                    muted
                  />
                </div>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="w-72 p-4 border-l border-dark-700 overflow-y-auto space-y-4">
            {/* Position presets */}
            {layout === 'overlay' && (
              <div>
                <label className="text-xs text-dark-400 mb-2 block">Position rapide</label>
                <div className="grid grid-cols-4 gap-2">
                  {positionPresets.map((preset, i) => (
                    <button
                      key={i}
                      onClick={() => applyPreset(preset)}
                      className="py-2 rounded-lg bg-dark-800 text-dark-400 hover:text-white hover:bg-dark-700 transition-all text-lg"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Size */}
            <div>
              <label className="text-xs text-dark-400 mb-2 block">
                Taille: {webcamSize}px
              </label>
              <input
                type="range"
                min="100"
                max="400"
                value={webcamSize}
                onChange={(e) => setWebcamSize(Number(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            {/* Border Width */}
            <div>
              <label className="text-xs text-dark-400 mb-2 block">
                Bordure: {webcamBorderWidth}px
              </label>
              <input
                type="range"
                min="0"
                max="15"
                value={webcamBorderWidth}
                onChange={(e) => setWebcamBorderWidth(Number(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            {/* Border Color */}
            <div>
              <label className="text-xs text-dark-400 mb-2 block">Couleur bordure</label>
              <div className="flex gap-2 flex-wrap">
                {['#FFB6C1', '#FF69B4', '#00D4FF', '#FFD700', '#FFFFFF', '#000000'].map((color) => (
                  <button
                    key={color}
                    onClick={() => setWebcamBorderColor(color)}
                    className={`w-10 h-10 rounded border-2 transition-all ${
                      webcamBorderColor === color
                        ? 'border-white scale-110'
                        : 'border-dark-600 hover:border-dark-500'
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>

            {/* Shape */}
            <div>
              <label className="text-xs text-dark-400 mb-2 block">Forme</label>
              <div className="flex gap-2">
                {(['circle', 'rounded', 'square'] as const).map((shape) => (
                  <button
                    key={shape}
                    onClick={() => setWebcamShape(shape)}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1 ${
                      webcamShape === shape
                        ? 'bg-primary-600 text-white'
                        : 'bg-dark-800 text-dark-400 hover:text-white'
                    }`}
                  >
                    {shape === 'circle' ? <Circle className="w-4 h-4" /> : 
                     shape === 'rounded' ? <RectangleHorizontal className="w-4 h-4" /> : 
                     <Square className="w-4 h-4" />}
                  </button>
                ))}
              </div>
            </div>

            {/* Download individual videos */}
            <div className="pt-4 border-t border-dark-700">
              <label className="text-xs text-dark-400 mb-2 block">Telecharger separement</label>
              <div className="space-y-2">
                <button
                  onClick={() => downloadVideo(screenBlob, 'screen.webm')}
                  className="w-full py-2 bg-dark-800 hover:bg-dark-700 text-dark-300 text-sm rounded-lg flex items-center justify-center gap-2 transition-all"
                >
                  <Download className="w-4 h-4" />
                  Ecran ({(screenBlob.size / 1024 / 1024).toFixed(1)} MB)
                </button>
                {webcamBlob && (
                  <button
                    onClick={() => downloadVideo(webcamBlob, 'webcam.webm')}
                    className="w-full py-2 bg-dark-800 hover:bg-dark-700 text-dark-300 text-sm rounded-lg flex items-center justify-center gap-2 transition-all"
                  >
                    <Download className="w-4 h-4" />
                    Webcam ({(webcamBlob.size / 1024 / 1024).toFixed(1)} MB)
                  </button>
                )}
              </div>
            </div>

            {/* Merge button */}
            <div className="pt-4">
              <button
                onClick={handleMerge}
                disabled={merging}
                className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:bg-dark-700 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all"
              >
                {merging ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Fusion en cours...
                  </>
                ) : (
                  <>
                    <Merge className="w-5 h-5" />
                    Fusionner les videos
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

