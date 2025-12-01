'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  FolderKanban,
  Clock,
  CheckCircle,
  AlertCircle,
  PlayCircle,
  Trash2,
  Play,
  RefreshCw,
  ExternalLink,
  Search,
  Filter,
  Settings,
  RotateCcw,
  Upload,
  Youtube
} from 'lucide-react';

interface ProjectStep {
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

interface Project {
  _id: string;
  name: string;
  folder_name: string;
  status: string;
  current_step: number | null;
  step_name: string | null;
  progress: number;
  steps: Record<string, ProjectStep>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface Stats {
  total: number;
  created: number;
  processing: number;
  completed: number;
  failed: number;
}

const STEPS_ORDER = [
  { key: 'convert', label: 'Conversion', icon: '⚙️' },
  { key: 'merge', label: 'Fusion', icon: '🎬' },
  { key: 'silence', label: 'Silences', icon: '🔇' },
  { key: 'cut_sources', label: 'Découpe', icon: '✂️' },
  { key: 'transcribe', label: 'Transcription', icon: '📝' },
  { key: 'shorts', label: 'Shorts', icon: '📱' },
  { key: 'broll', label: 'B-Roll', icon: '🎥' },
  { key: 'integrate_broll', label: 'Intégration', icon: '🔗' },
  { key: 'seo', label: 'SEO', icon: '🔍' },
  { key: 'thumbnail', label: 'Miniature', icon: '🖼️' },
  { key: 'schedule', label: 'Programmation', icon: '📅' },
  { key: 'upload', label: 'Upload', icon: '📤' },
];

const STATUS_LABELS: Record<string, string> = {
  created: 'En attente',
  uploading: '⬆️ Upload...',
  converting: '⚙️ Conversion...',
  processing: 'En cours',
  completed: 'Terminé',
  failed: 'Échoué',
  paused: 'En pause',
  pending: 'En attente',
  ready_to_upload: '🎬 Prêt pour YouTube',
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  const fetchProjects = async () => {
    try {
      const url = filter 
        ? `${API_URL}/api/projects?status=${filter}` 
        : `${API_URL}/api/projects`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Erreur chargement');
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (err) {
      console.error('Erreur:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/projects/stats`);
      if (!res.ok) throw new Error('Erreur stats');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Erreur stats:', err);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchProjects(), fetchStats()]);
      setLoading(false);
    };
    loadData();
    
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [filter]);

  const startPipeline = async (projectId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/start`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Erreur démarrage');
      fetchProjects();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur');
    }
  };

  const deleteProject = async (projectId: string) => {
    if (!confirm('Supprimer ce projet ?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Erreur suppression');
      fetchProjects();
      fetchStats();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur');
    }
  };

  const rebootProject = async (projectId: string) => {
    if (!confirm('Relancer ce projet depuis le début ?\n\nCela va:\n- Stopper les workers en cours\n- Supprimer tous les fichiers sauf config.json, screen.mp4, webcam.mp4\n- Relancer le pipeline depuis le début')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/reboot`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Erreur reboot');
      fetchProjects();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur');
    }
  };

  const uploadToYouTube = async (projectId: string) => {
    if (!confirm('Lancer l\'upload vers YouTube ?\n\nCette action va publier la vidéo sur votre chaîne YouTube.')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/upload`, {
        method: 'POST',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Erreur upload');
      }
      fetchProjects();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erreur');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStepStatus = (steps: Record<string, ProjectStep>, stepKey: string) => {
    return steps[stepKey]?.status || 'pending';
  };

  const filteredProjects = projects.filter(p => 
    searchQuery === '' || 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.folder_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Projets</h1>
          <p className="text-zinc-400">Gérez vos projets vidéo</p>
        </div>
        <Link href="/record" className="btn-primary flex items-center gap-2">
          <PlayCircle className="w-4 h-4" />
          Nouveau projet
        </Link>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-5 gap-4 mb-8">
          <button 
            onClick={() => setFilter('')}
            className={`card p-4 text-left transition ${filter === '' ? 'border-violet-500/30' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <FolderKanban className="w-4 h-4 text-zinc-400" />
              <span className="text-sm text-zinc-400">Total</span>
            </div>
            <p className="text-2xl font-bold text-white">{stats.total}</p>
          </button>

          <button 
            onClick={() => setFilter('created')}
            className={`card p-4 text-left transition ${filter === 'created' ? 'border-zinc-500/30' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-zinc-400" />
              <span className="text-sm text-zinc-400">En attente</span>
            </div>
            <p className="text-2xl font-bold text-zinc-400">{stats.created}</p>
          </button>

          <button 
            onClick={() => setFilter('processing')}
            className={`card p-4 text-left transition ${filter === 'processing' ? 'border-blue-500/30' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <PlayCircle className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-zinc-400">En cours</span>
            </div>
            <p className="text-2xl font-bold text-blue-400">{stats.processing}</p>
          </button>

          <button 
            onClick={() => setFilter('completed')}
            className={`card p-4 text-left transition ${filter === 'completed' ? 'border-green-500/30' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm text-zinc-400">Terminés</span>
            </div>
            <p className="text-2xl font-bold text-green-400">{stats.completed}</p>
          </button>

          <button 
            onClick={() => setFilter('failed')}
            className={`card p-4 text-left transition ${filter === 'failed' ? 'border-red-500/30' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-zinc-400">Échoués</span>
            </div>
            <p className="text-2xl font-bold text-red-400">{stats.failed}</p>
          </button>
        </div>
      )}

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            type="text"
            placeholder="Rechercher un projet..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      {/* Projects List */}
      {loading && projects.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500 mx-auto mb-3" />
          <p className="text-zinc-400">Chargement...</p>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="card p-12 text-center">
          <FolderKanban className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <p className="text-zinc-400 mb-2">Aucun projet trouvé</p>
          <p className="text-zinc-500 text-sm">
            {filter ? 'Essayez un autre filtre' : 'Commencez par enregistrer une vidéo'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredProjects.map((project) => (
            <div key={project._id} className="card overflow-hidden">
              {/* Header */}
              <div className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${
                    project.status === 'completed' ? 'bg-green-500' :
                    project.status === 'ready_to_upload' ? 'bg-yellow-500' :
                    project.status === 'processing' ? 'bg-blue-500 animate-pulse' :
                    project.status === 'failed' ? 'bg-red-500' :
                    'bg-zinc-500'
                  }`} />
                  <div>
                    <h3 className="font-semibold text-white">{project.name}</h3>
                    <p className="text-sm text-zinc-500 font-mono">{project.folder_name}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`badge ${
                    project.status === 'completed' ? 'badge-success' :
                    project.status === 'ready_to_upload' ? 'bg-yellow-500/20 text-yellow-400' :
                    project.status === 'processing' ? 'badge-info' :
                    project.status === 'failed' ? 'badge-error' :
                    'bg-zinc-800 text-zinc-400'
                  }`}>
                    {project.status === 'processing' && project.step_name 
                      ? project.step_name 
                      : STATUS_LABELS[project.status] || project.status}
                  </span>
                  <span className="text-sm text-zinc-500">{formatDate(project.created_at)}</span>
                </div>
              </div>

              {/* Progress */}
              <div className="px-5 pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 progress-bar">
                    <div 
                      className="progress-bar-fill" 
                      style={{ width: `${project.progress}%` }} 
                    />
                  </div>
                  <span className="text-sm text-zinc-400 w-12 text-right">{project.progress}%</span>
                </div>
              </div>

              {/* Steps */}
              <div className="px-5 pb-4">
                <div className="flex gap-1">
                  {STEPS_ORDER.map((step, index) => {
                    const stepNumber = index + 1;
                    const currentStep = project.current_step || 0;
                    const isCompleted = project.status === 'completed' || stepNumber < currentStep;
                    const isProcessing = project.status === 'processing' && stepNumber === currentStep;
                    const isFailed = project.status === 'failed' && stepNumber === currentStep;
                    const isUploadStep = step.key === 'upload';
                    const canUpload = isUploadStep && (project.status === 'ready_to_upload' || (project.status === 'completed' && project.current_step === 10));
                    
                    // Bouton Upload YouTube cliquable
                    if (isUploadStep && canUpload) {
                      return (
                        <button
                          key={step.key}
                          onClick={() => uploadToYouTube(project._id)}
                          className="flex-1 h-9 rounded-lg flex items-center justify-center text-xs transition bg-red-600 hover:bg-red-500 text-white cursor-pointer font-medium gap-1"
                          title="Cliquez pour lancer l'upload YouTube"
                        >
                          <Youtube className="w-4 h-4" />
                          Upload
                        </button>
                      );
                    }
                    
                    return (
                      <div
                        key={step.key}
                        className={`flex-1 h-9 rounded-lg flex items-center justify-center text-xs transition ${
                          isCompleted ? 'bg-green-500/10 text-green-400' :
                          isProcessing ? 'bg-blue-500/10 text-blue-400 animate-pulse' :
                          isFailed ? 'bg-red-500/10 text-red-400' :
                          'bg-zinc-800/50 text-zinc-500'
                        }`}
                        title={`${step.label}: ${isCompleted ? 'Terminé' : isProcessing ? 'En cours' : isFailed ? 'Échoué' : 'En attente'}`}
                      >
                        {step.icon}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Actions */}
              <div className="px-5 py-3 bg-zinc-900/50 flex items-center justify-between border-t border-white/5">
                <div className="flex gap-2">
                  {project.status === 'created' && (
                    <button
                      onClick={() => startPipeline(project._id)}
                      className="btn-primary flex items-center gap-2 text-sm py-1.5"
                    >
                      <Play className="w-4 h-4" />
                      Démarrer
                    </button>
                  )}
                  {project.status === 'failed' && (
                    <button
                      onClick={() => startPipeline(project._id)}
                      className="btn-secondary flex items-center gap-2 text-sm py-1.5 text-orange-400 border-orange-500/20 hover:border-orange-500/40"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Relancer
                    </button>
                  )}
                  {project.status === 'ready_to_upload' && (
                    <button
                      onClick={() => uploadToYouTube(project._id)}
                      className="btn-primary flex items-center gap-2 text-sm py-1.5 bg-red-600 hover:bg-red-500"
                    >
                      <Youtube className="w-4 h-4" />
                      Upload YouTube
                    </button>
                  )}
                  {/* Lien vers les détails pour tous les projets */}
                  <Link
                    href={`/projects/${project._id}`}
                    className={`flex items-center gap-2 text-sm py-1.5 px-3 rounded-lg transition ${
                      project.status === 'completed' 
                        ? 'btn-primary' 
                        : 'btn-secondary'
                    }`}
                  >
                    <ExternalLink className="w-4 h-4" />
                    {project.status === 'completed' ? 'Voir les fichiers' : 'Détails'}
                  </Link>
                  {/* Lien vers le dossier pour les projets en cours */}
                  {project.status === 'processing' && (
                    <a
                      href={`${API_URL}/output/${project.folder_name}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Dossier
                    </a>
                  )}
                  {/* Bouton Calibrage */}
                  <Link
                    href={`/projects/${project._id}/calibrate`}
                    className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                    title="Calibrer la position de la webcam"
                  >
                    <Settings className="w-4 h-4" />
                    Calibrage
                  </Link>
                  {/* Bouton Reboot */}
                  <button
                    onClick={() => rebootProject(project._id)}
                    className="btn-secondary flex items-center gap-2 text-sm py-1.5 text-amber-400 border-amber-500/20 hover:border-amber-500/40"
                    title="Relancer le pipeline depuis le début"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Reboot
                  </button>
                </div>
                <button
                  onClick={() => deleteProject(project._id)}
                  className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
