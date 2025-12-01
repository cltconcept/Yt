'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { X, Scissors, Play, Pause, SkipBack, SkipForward, Trash2, Plus, Check, Loader2 } from 'lucide-react';

interface CutSegment {
  id: string;
  start: number;
  end: number;
}

interface VideoCutterModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoUrl: string;
  projectId: string;
  folderName: string;
  onCutComplete: () => void;
}

export default function VideoCutterModal({
  isOpen,
  onClose,
  videoUrl,
  projectId,
  folderName,
  onCutComplete
}: VideoCutterModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [cutSegments, setCutSegments] = useState<CutSegment[]>([]);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<number | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setCutSegments([]);
      setCurrentTime(0);
      setIsPlaying(false);
      setError(null);
    }
  }, [isOpen]);

  // Handle video metadata loaded
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  // Handle time update
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  // Toggle play/pause
  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Seek to time
  const seekTo = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(time, duration));
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  // Skip forward/backward
  const skip = (seconds: number) => {
    seekTo(currentTime + seconds);
  };

  // Format time as MM:SS.ms
  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    const ms = Math.floor((time % 1) * 10);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`;
  };

  // Handle timeline click
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    const time = percentage * duration;
    
    if (isSelecting && selectionStart !== null) {
      // End selection
      const start = Math.min(selectionStart, time);
      const end = Math.max(selectionStart, time);
      
      if (end - start > 0.1) { // Minimum 0.1s segment
        setCutSegments(prev => [...prev, {
          id: Date.now().toString(),
          start,
          end
        }]);
      }
      
      setIsSelecting(false);
      setSelectionStart(null);
    } else {
      // Start selection or just seek
      seekTo(time);
    }
  };

  // Start cut selection
  const startSelection = () => {
    setIsSelecting(true);
    setSelectionStart(currentTime);
  };

  // Cancel selection
  const cancelSelection = () => {
    setIsSelecting(false);
    setSelectionStart(null);
  };

  // Remove a cut segment
  const removeSegment = (id: string) => {
    setCutSegments(prev => prev.filter(s => s.id !== id));
  };

  // Mark current position as cut point
  const markCutAtCurrentTime = () => {
    if (selectionStart === null) {
      setSelectionStart(currentTime);
      setIsSelecting(true);
    } else {
      const start = Math.min(selectionStart, currentTime);
      const end = Math.max(selectionStart, currentTime);
      
      if (end - start > 0.1) {
        setCutSegments(prev => [...prev, {
          id: Date.now().toString(),
          start,
          end
        }]);
      }
      
      setIsSelecting(false);
      setSelectionStart(null);
    }
  };

  // Apply cuts
  const applyCuts = async () => {
    if (cutSegments.length === 0) {
      setError('Aucune zone à couper sélectionnée');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/projects/${projectId}/cut`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cuts: cutSegments.map(s => ({ start: s.start, end: s.end }))
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Erreur lors de la découpe');
      }

      onCutComplete();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-zinc-900 rounded-2xl w-[95vw] max-w-6xl max-h-[95vh] overflow-hidden flex flex-col border border-white/10">
        {/* Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Scissors className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-white">Découper la vidéo</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video Player */}
        <div className="flex-1 overflow-hidden p-4">
          <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
            <video
              ref={videoRef}
              src={videoUrl}
              className="w-full h-full"
              onLoadedMetadata={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={() => skip(-5)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
              title="-5s"
            >
              <SkipBack className="w-5 h-5" />
            </button>
            <button
              onClick={() => skip(-1)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
              title="-1s"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              onClick={togglePlay}
              className="p-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            <button
              onClick={() => skip(1)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
              title="+1s"
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <button
              onClick={() => skip(5)}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
              title="+5s"
            >
              <SkipForward className="w-5 h-5" />
            </button>
            
            <span className="text-white font-mono text-sm min-w-[80px]">
              {formatTime(currentTime)}
            </span>
            <span className="text-zinc-500">/</span>
            <span className="text-zinc-400 font-mono text-sm min-w-[80px]">
              {formatTime(duration)}
            </span>

            <div className="flex-1" />

            <button
              onClick={markCutAtCurrentTime}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
                isSelecting
                  ? 'bg-red-600 hover:bg-red-500 text-white'
                  : 'bg-amber-600 hover:bg-amber-500 text-white'
              }`}
            >
              <Scissors className="w-4 h-4" />
              {isSelecting ? 'Fin de coupe' : 'Marquer début'}
            </button>
            
            {isSelecting && (
              <button
                onClick={cancelSelection}
                className="px-3 py-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
              >
                Annuler
              </button>
            )}
          </div>

          {/* Timeline */}
          <div className="mb-4">
            <div
              ref={timelineRef}
              className="relative h-16 bg-zinc-800 rounded-lg cursor-crosshair overflow-hidden"
              onClick={handleTimelineClick}
            >
              {/* Cut segments (zones à supprimer) */}
              {cutSegments.map(segment => (
                <div
                  key={segment.id}
                  className="absolute top-0 bottom-0 bg-red-500/50 border-l-2 border-r-2 border-red-500"
                  style={{
                    left: `${(segment.start / duration) * 100}%`,
                    width: `${((segment.end - segment.start) / duration) * 100}%`
                  }}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeSegment(segment.id);
                    }}
                    className="absolute top-1 right-1 p-1 bg-red-600 hover:bg-red-500 rounded text-white"
                    title="Supprimer cette coupe"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {/* Selection in progress */}
              {isSelecting && selectionStart !== null && (
                <div
                  className="absolute top-0 bottom-0 bg-amber-500/30 border-l-2 border-amber-500"
                  style={{
                    left: `${(Math.min(selectionStart, currentTime) / duration) * 100}%`,
                    width: `${(Math.abs(currentTime - selectionStart) / duration) * 100}%`
                  }}
                />
              )}

              {/* Playhead */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
                style={{ left: `${(currentTime / duration) * 100}%` }}
              >
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-white rounded-full" />
              </div>

              {/* Time markers */}
              <div className="absolute bottom-0 left-0 right-0 h-4 flex items-end px-2">
                {Array.from({ length: Math.min(10, Math.ceil(duration / 10)) + 1 }).map((_, i) => {
                  const time = (i / 10) * duration;
                  return (
                    <div
                      key={i}
                      className="absolute text-[10px] text-zinc-500"
                      style={{ left: `${(time / duration) * 100}%` }}
                    >
                      {formatTime(time).split('.')[0]}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Cut segments list */}
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <h3 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
              <Scissors className="w-4 h-4" />
              Zones à couper ({cutSegments.length})
            </h3>
            
            {cutSegments.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Cliquez sur "Marquer début" puis naviguez jusqu'à la fin de la zone à supprimer et cliquez sur "Fin de coupe"
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {cutSegments.sort((a, b) => a.start - b.start).map(segment => (
                  <div
                    key={segment.id}
                    className="flex items-center gap-2 bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-sm"
                  >
                    <span className="font-mono">
                      {formatTime(segment.start)} → {formatTime(segment.end)}
                    </span>
                    <span className="text-red-500/70">
                      ({(segment.end - segment.start).toFixed(1)}s)
                    </span>
                    <button
                      onClick={() => removeSegment(segment.id)}
                      className="p-0.5 hover:bg-red-500/30 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-3 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10 flex items-center justify-between">
          <p className="text-sm text-zinc-500">
            Les zones rouges seront supprimées de screen.mp4 et webcam.mp4, puis le pipeline redémarrera.
          </p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={processing}
              className="px-4 py-2 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition"
            >
              Annuler
            </button>
            <button
              onClick={applyCuts}
              disabled={processing || cutSegments.length === 0}
              className="px-6 py-2 bg-green-600 hover:bg-green-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition flex items-center gap-2"
            >
              {processing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Découpe en cours...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Appliquer et relancer
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

