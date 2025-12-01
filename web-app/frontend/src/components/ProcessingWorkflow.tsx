'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Check, 
  X, 
  Loader2, 
  Clock,
  FileVideo,
  Upload,
  Scissors,
  Sparkles,
  Image,
  Film,
  VolumeX,
  Mic,
  Search,
  Zap,
  Layers,
  ImagePlus,
  Type,
  ImageIcon
} from 'lucide-react';

export type WorkflowStepStatus = 'pending' | 'running' | 'success' | 'error' | 'skipped';

export interface WorkflowStep {
  id: string;
  label: string;
  status: WorkflowStepStatus;
  message?: string;
  duration?: number;
  icon: React.ReactNode;
}

export interface WorkflowLog {
  id: string;
  timestamp: Date;
  type: 'info' | 'success' | 'error' | 'warning' | 'action';
  message: string;
  stepId?: string;
}

interface ProcessingWorkflowProps {
  steps: WorkflowStep[];
  logs: WorkflowLog[];
  isComplete: boolean;
  hasError: boolean;
  onClose?: () => void;
  folderName?: string;  // Pour polling de progression
}

const statusColors: Record<WorkflowStepStatus, string> = {
  pending: 'bg-dark-600 border-dark-500',
  running: 'bg-primary-500/20 border-primary-500 animate-pulse',
  success: 'bg-green-500/20 border-green-500',
  error: 'bg-red-500/20 border-red-500',
  skipped: 'bg-dark-600/50 border-dark-500/50'
};

const statusIcons: Record<WorkflowStepStatus, React.ReactNode> = {
  pending: <Clock className="w-4 h-4 text-dark-400" />,
  running: <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />,
  success: <Check className="w-4 h-4 text-green-500" />,
  error: <X className="w-4 h-4 text-red-500" />,
  skipped: <span className="text-xs text-dark-500">—</span>
};

const logTypeColors: Record<string, string> = {
  info: 'text-blue-400',
  success: 'text-green-400',
  error: 'text-red-400',
  warning: 'text-amber-400',
  action: 'text-purple-400'
};

export function ProcessingWorkflow({ steps, logs, isComplete, hasError, onClose, folderName }: ProcessingWorkflowProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const startTimeRef = useRef<Date>(new Date());

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Timer
  useEffect(() => {
    if (isComplete) return;
    
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((new Date().getTime() - startTimeRef.current.getTime()) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isComplete]);

  // Bloquer la fermeture avec Escape tant que pas terminé
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isComplete) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isComplete]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const completedSteps = steps.filter(s => s.status === 'success').length;
  const totalSteps = steps.filter(s => s.status !== 'skipped').length;
  const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  // Message d'avertissement si pas terminé
  const showWarning = !isComplete && !hasError;

  return (
    <div 
      className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        // Empêcher la fermeture en cliquant en dehors tant que pas terminé
        if (!isComplete && e.target === e.currentTarget) {
          e.preventDefault();
          e.stopPropagation();
        }
      }}
    >
      <div 
        className="glass rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden border border-dark-600"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-dark-600">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-3">
                {isComplete ? (
                  hasError ? (
                    <>
                      <X className="w-6 h-6 text-red-500" />
                      Traitement terminé avec erreurs
                    </>
                  ) : (
                    <>
                      <Check className="w-6 h-6 text-green-500" />
                      Traitement terminé
                    </>
                  )
                ) : (
                  <>
                    <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                    Pipeline en cours...
                  </>
                )}
              </h2>
              <p className="text-dark-400 text-sm mt-1">
                {completedSteps}/{totalSteps} étapes • {formatTime(elapsedTime)}
                {folderName && <span className="ml-2 text-dark-500">({folderName})</span>}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Avertissement de ne pas fermer */}
              {showWarning && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/30 rounded-lg">
                  <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                  <span className="text-amber-400 text-sm font-medium">Ne pas fermer</span>
                </div>
              )}
              {/* Bouton fermer uniquement si terminé */}
              {isComplete && onClose && (
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors font-medium"
                >
                  Fermer
                </button>
              )}
            </div>
          </div>
          
          {/* Progress bar */}
          <div className="h-2 bg-dark-600 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${hasError ? 'bg-red-500' : 'bg-gradient-to-r from-primary-500 to-green-500'}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Workflow Steps */}
          <div className="w-1/2 p-6 border-r border-dark-600 overflow-y-auto">
            <h3 className="text-sm font-semibold text-dark-300 uppercase tracking-wider mb-4">
              Pipeline ({totalSteps} étapes)
            </h3>
            <div className="space-y-2">
              {steps.map((step, index) => (
                <div 
                  key={step.id}
                  className={`relative flex items-start gap-3 p-3 rounded-xl border-2 transition-all ${statusColors[step.status]}`}
                >
                  {/* Connector line */}
                  {index < steps.length - 1 && (
                    <div className="absolute left-[26px] top-[52px] w-0.5 h-4 bg-dark-600" />
                  )}
                  
                  {/* Step icon */}
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    step.status === 'running' ? 'bg-primary-500/30' :
                    step.status === 'success' ? 'bg-green-500/30' :
                    step.status === 'error' ? 'bg-red-500/30' :
                    'bg-dark-500/30'
                  }`}>
                    {step.icon}
                  </div>
                  
                  {/* Step content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`font-medium text-sm ${
                        step.status === 'pending' || step.status === 'skipped' ? 'text-dark-400' : 'text-white'
                      }`}>
                        {step.label}
                      </span>
                      {statusIcons[step.status]}
                    </div>
                    {step.message && (
                      <p className={`text-xs mt-1 truncate ${
                        step.status === 'error' ? 'text-red-400' : 'text-dark-400'
                      }`}>
                        {step.message}
                      </p>
                    )}
                    {step.duration !== undefined && step.status === 'success' && (
                      <p className="text-xs text-dark-500 mt-0.5">
                        {step.duration < 1000 ? `${step.duration}ms` : `${(step.duration / 1000).toFixed(1)}s`}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Console Logs */}
          <div className="w-1/2 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-dark-600">
              <h3 className="text-sm font-semibold text-dark-300 uppercase tracking-wider">
                Console
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs bg-dark-900/50">
              {logs.length === 0 ? (
                <div className="text-dark-500 text-center py-8">
                  En attente des logs...
                </div>
              ) : (
                <div className="space-y-1">
                  {logs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                      <span className="text-dark-500 shrink-0">
                        {log.timestamp.toLocaleTimeString('fr-FR', { 
                          hour: '2-digit', 
                          minute: '2-digit', 
                          second: '2-digit' 
                        })}
                      </span>
                      <span className={`${logTypeColors[log.type]} break-all`}>
                        {log.type === 'success' && '✓ '}
                        {log.type === 'error' && '✗ '}
                        {log.type === 'warning' && '⚠ '}
                        {log.type === 'action' && '→ '}
                        {log.message}
                      </span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Hook pour gérer le workflow complet (11 étapes pour overlay)
export function useWorkflowState(layout: string, autoProcess: boolean, autoIllustrate: boolean) {
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [logs, setLogs] = useState<WorkflowLog[]>([]);
  const logIdRef = useRef(0);

  // Initialiser les étapes en fonction du layout et des options
  const initializeSteps = useCallback(() => {
    const isFullWorkflow = layout === 'overlay' || layout === 'side_by_side';
    
    // Pipeline complet pour overlay/side_by_side avec Auto ON
    if (autoProcess && isFullWorkflow) {
      const fullSteps: WorkflowStep[] = [
        {
          id: 'prepare',
          label: 'Organisation des fichiers',
          status: 'pending',
          icon: <FileVideo className="w-4 h-4 text-blue-400" />
        },
        {
          id: 'upload',
          label: 'Envoi au serveur',
          status: 'pending',
          icon: <Upload className="w-4 h-4 text-cyan-400" />
        },
        {
          id: 'merge',
          label: 'Fusion vidéo initiale',
          status: 'pending',
          icon: <Film className="w-4 h-4 text-violet-400" />
        },
        {
          id: 'silence_detect',
          label: 'Détection des silences',
          status: 'pending',
          icon: <VolumeX className="w-4 h-4 text-orange-400" />
        },
        {
          id: 'silence_cut',
          label: 'Découpe des silences',
          status: 'pending',
          icon: <Scissors className="w-4 h-4 text-orange-400" />
        },
        {
          id: 'transcription',
          label: 'Transcription audio',
          status: 'pending',
          icon: <Mic className="w-4 h-4 text-amber-400" />
        },
        {
          id: 'pexels_analyze',
          label: 'Analyse pour clips Pexels',
          status: 'pending',
          icon: <Search className="w-4 h-4 text-green-400" />
        },
        {
          id: 'shorts_detect',
          label: 'Détection moments clés',
          status: 'pending',
          icon: <Zap className="w-4 h-4 text-yellow-400" />
        },
        {
          id: 'shorts_generate',
          label: 'Génération des shorts (9:16)',
          status: 'pending',
          icon: <Film className="w-4 h-4 text-pink-400" />
        },
        {
          id: 'final_video',
          label: 'Vidéo finale 16:9',
          status: 'pending',
          icon: <Layers className="w-4 h-4 text-indigo-400" />
        },
        {
          id: 'illustrated_video',
          label: 'Vidéo avec B-roll Pexels',
          status: 'pending',
          icon: <ImagePlus className="w-4 h-4 text-teal-400" />
        },
        {
          id: 'seo',
          label: 'Génération SEO YouTube',
          status: 'pending',
          icon: <Type className="w-4 h-4 text-purple-400" />
        },
        {
          id: 'thumbnail',
          label: 'Génération miniature',
          status: 'pending',
          icon: <ImageIcon className="w-4 h-4 text-rose-400" />
        }
      ];
      
      setSteps(fullSteps);
    } else if (autoProcess) {
      // Pipeline simplifié pour screen_only ou webcam_only
      const simpleSteps: WorkflowStep[] = [
        {
          id: 'prepare',
          label: 'Organisation des fichiers',
          status: 'pending',
          icon: <FileVideo className="w-4 h-4 text-blue-400" />
        },
        {
          id: 'upload',
          label: 'Envoi au serveur',
          status: 'pending',
          icon: <Upload className="w-4 h-4 text-cyan-400" />
        },
        {
          id: 'merge',
          label: 'Conversion vidéo',
          status: 'pending',
          icon: <Film className="w-4 h-4 text-violet-400" />
        },
        {
          id: 'silence_detect',
          label: 'Détection des silences',
          status: 'pending',
          icon: <VolumeX className="w-4 h-4 text-orange-400" />
        },
        {
          id: 'silence_cut',
          label: 'Découpe des silences',
          status: 'pending',
          icon: <Scissors className="w-4 h-4 text-orange-400" />
        },
        {
          id: 'transcription',
          label: 'Transcription audio',
          status: 'pending',
          icon: <Mic className="w-4 h-4 text-amber-400" />
        },
        {
          id: 'seo',
          label: 'Génération SEO YouTube',
          status: 'pending',
          icon: <Type className="w-4 h-4 text-purple-400" />
        },
        {
          id: 'thumbnail',
          label: 'Génération miniature',
          status: 'pending',
          icon: <ImageIcon className="w-4 h-4 text-rose-400" />
        }
      ];
      
      setSteps(simpleSteps);
    } else {
      // Sans auto-process - juste upload et fusion
      const baseSteps: WorkflowStep[] = [
        {
          id: 'prepare',
          label: 'Préparation des fichiers',
          status: 'pending',
          icon: <FileVideo className="w-4 h-4 text-blue-400" />
        },
        {
          id: 'upload',
          label: 'Envoi au serveur',
          status: 'pending',
          icon: <Upload className="w-4 h-4 text-cyan-400" />
        },
        {
          id: 'merge',
          label: 'Fusion vidéo',
          status: 'pending',
          icon: <Film className="w-4 h-4 text-violet-400" />
        },
        {
          id: 'transcription',
          label: 'Transcription audio',
          status: 'pending',
          icon: <Sparkles className="w-4 h-4 text-amber-400" />
        }
      ];

      setSteps(baseSteps);
    }

    setLogs([]);
    logIdRef.current = 0;
  }, [layout, autoProcess, autoIllustrate]);

  const updateStep = useCallback((stepId: string, updates: Partial<WorkflowStep>) => {
    setSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, ...updates } : step
    ));
  }, []);

  const addLog = useCallback((type: WorkflowLog['type'], message: string, stepId?: string) => {
    const log: WorkflowLog = {
      id: `log-${++logIdRef.current}`,
      timestamp: new Date(),
      type,
      message,
      stepId
    };
    setLogs(prev => [...prev, log]);
  }, []);

  const startStep = useCallback((stepId: string) => {
    updateStep(stepId, { status: 'running' });
    const step = steps.find(s => s.id === stepId);
    if (step) {
      addLog('action', `Démarrage: ${step.label}`, stepId);
    }
  }, [updateStep, addLog, steps]);

  const completeStep = useCallback((stepId: string, duration?: number, message?: string) => {
    updateStep(stepId, { status: 'success', duration, message });
    const step = steps.find(s => s.id === stepId);
    if (step) {
      addLog('success', message || `${step.label} terminé${duration ? ` (${duration}ms)` : ''}`, stepId);
    }
  }, [updateStep, addLog, steps]);

  const failStep = useCallback((stepId: string, errorMessage: string) => {
    updateStep(stepId, { status: 'error', message: errorMessage });
    const step = steps.find(s => s.id === stepId);
    if (step) {
      addLog('error', `Erreur ${step.label}: ${errorMessage}`, stepId);
    }
  }, [updateStep, addLog, steps]);

  const skipStep = useCallback((stepId: string) => {
    updateStep(stepId, { status: 'skipped' });
  }, [updateStep]);

  const reset = useCallback(() => {
    initializeSteps();
  }, [initializeSteps]);

  // Mettre à jour les étapes depuis la progression du backend
  const updateFromBackendProgress = useCallback((progress: any[]) => {
    if (!progress || progress.length === 0) return;

    // Map des étapes backend vers frontend
    const stepMapping: Record<string, string> = {
      'Organisation des fichiers': 'prepare',
      'Détection des silences': 'silence_detect',
      'Découpe des silences': 'silence_cut',
      'Transcription': 'transcription',
      'Analyse pour clips Pexels': 'pexels_analyze',
      'Détection moments clés': 'shorts_detect',
      'Génération des shorts': 'shorts_generate',
      'Vidéo finale 16:9': 'final_video',
      'Vidéo avec B-roll Pexels': 'illustrated_video',
      'Génération SEO YouTube': 'seo',
      'Génération miniature': 'thumbnail'
    };

    progress.forEach(p => {
      const stepId = stepMapping[p.step_name];
      if (stepId) {
        const status = p.status === 'completed' ? 'success' : 
                      p.status === 'error' ? 'error' : 
                      p.status === 'running' ? 'running' : 'pending';
        updateStep(stepId, { status, message: p.message });
        
        if (p.status === 'running') {
          addLog('action', p.message, stepId);
        } else if (p.status === 'completed') {
          addLog('success', p.message, stepId);
        } else if (p.status === 'error') {
          addLog('error', p.message, stepId);
        }
      }
    });
  }, [updateStep, addLog]);

  return {
    steps,
    logs,
    initializeSteps,
    updateStep,
    addLog,
    startStep,
    completeStep,
    failStep,
    skipStep,
    reset,
    updateFromBackendProgress
  };
}

// Export des icônes pour utilisation externe
export const WorkflowIcons = {
  FileVideo,
  Upload,
  Scissors,
  Sparkles,
  Image,
  Film,
  VolumeX,
  Mic,
  Search,
  Zap,
  Layers,
  ImagePlus,
  Type,
  ImageIcon
};
