'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft,
  Play,
  Download,
  Copy,
  Check,
  Image as ImageIcon,
  Film,
  FileText,
  Hash,
  MessageSquare,
  Youtube,
  Smartphone,
  Loader2,
  ExternalLink,
  Calendar,
  Clock,
  Upload,
  Video,
  Terminal,
  StopCircle,
  RefreshCw,
  Scissors
} from 'lucide-react';
import VideoCutterModal from '@/components/VideoCutterModal';

interface SEOData {
  main_video: {
    title: string;
    description: string;
    tags: string[];
    pinned_comment: string;
  };
  shorts: Array<{
    title: string;
    description: string;
    tags: string[];
    pinned_comment: string;
    file: string;
  }>;
}

interface ScheduledUpload {
  type: string;
  file: string;
  title: string;
  description: string;
  tags: string[];
  privacy: string;
  scheduled_date: string;
  scheduled_time: string;
  thumbnail?: string;
  status: string;
}

interface Schedule {
  created_at: string;
  status: string;
  uploads: ScheduledUpload[];
}

interface ProjectFiles {
  illustrated: string | null;
  nosilence: string | null;
  original: string | null;
  thumbnail: string | null;
  shorts: string[];
  seo: SEOData | null;
  transcription: string | null;
  schedule: Schedule | null;
}

interface Project {
  _id: string;
  name: string;
  folder_name: string;
  status: string;
  current_step: number | null;
  step_name: string | null;
  progress: number;
  created_at: string;
  completed_at: string | null;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<ProjectFiles | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'videos' | 'shorts' | 'seo' | 'schedule' | 'terminal'>('videos');
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [taskState, setTaskState] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [showCutModal, setShowCutModal] = useState(false);
  const [restartStep, setRestartStep] = useState(1);
  const [thumbnailCorrection, setThumbnailCorrection] = useState('');
  const [regeneratingThumbnail, setRegeneratingThumbnail] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  const PIPELINE_STEPS = [
    { step: 0, name: 'Conversion' },
    { step: 1, name: 'Merge (Fusion)' },
    { step: 2, name: 'Silence (Suppression)' },
    { step: 3, name: 'Cut sources' },
    { step: 4, name: 'Transcription' },
    { step: 5, name: 'Shorts' },
    { step: 6, name: 'B-Roll' },
    { step: 7, name: 'Intégration B-Roll' },
    { step: 8, name: 'SEO' },
    { step: 9, name: 'Thumbnail' },
    { step: 10, name: 'Schedule' },
    { step: 11, name: 'Upload YouTube' },
  ];

  const handleRestartFromStep = async (overrideStep?: number) => {
    const step = overrideStep !== undefined ? overrideStep : restartStep;
    const stepName = PIPELINE_STEPS.find(s => s.step === step)?.name || 'Inconnue';
    
    setRestarting(true);
    try {
      const url = `${API_URL}/api/projects/${projectId}/start?start_step=${step}&end_step=12`;
      console.log(`[Restart] Appel API: ${url}`);
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log(`[Restart] Réponse status: ${res.status}`);
      
      if (res.ok) {
        const data = await res.json();
        console.log('[Restart] Success:', data);
        alert(`✅ Pipeline relancé depuis l'étape ${step} (${stepName})`);
        window.location.reload();
      } else {
        const errorText = await res.text();
        console.error('[Restart] Erreur response:', errorText);
        alert(`❌ Erreur ${res.status}: ${errorText}`);
      }
    } catch (err) {
      console.error('[Restart] Exception:', err);
      alert(`❌ Erreur de connexion: ${err}`);
    } finally {
      setRestarting(false);
    }
  };

  const handleStopPipeline = async () => {
    if (!confirm('Êtes-vous sûr de vouloir arrêter le pipeline en cours ?')) return;
    
    setStopping(true);
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/stop`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Pipeline arrêté à l'étape ${data.stopped_at_step}`);
        // Recharger le projet
        window.location.reload();
      } else {
        alert('Erreur lors de l\'arrêt du pipeline');
      }
    } catch (err) {
      console.error('Erreur stop:', err);
      alert('Erreur de connexion');
    } finally {
      setStopping(false);
    }
  };

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await fetch(`${API_URL}/api/projects/${projectId}`);
        if (!res.ok) throw new Error('Projet non trouvé');
        const data = await res.json();
        setProject(data);

        // Charger les fichiers
        const filesRes = await fetch(`${API_URL}/api/projects/${projectId}/files`);
        if (filesRes.ok) {
          const filesData = await filesRes.json();
          setFiles(filesData);
        }
      } catch (err) {
        console.error('Erreur:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
  }, [projectId, API_URL]);

  // Récupérer les logs en temps réel quand l'onglet Terminal est actif
  useEffect(() => {
    if (activeTab !== 'terminal' || !projectId) return;

    const fetchLogs = async () => {
      try {
        const res = await fetch(`${API_URL}/api/projects/${projectId}/logs?limit=50`);
        if (res.ok) {
          const data = await res.json();
          setLogs(data.logs || []);
          setTaskState(data.task_state);
        }
      } catch (err) {
        console.error('Erreur logs:', err);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000); // Toutes les 2 secondes
    return () => clearInterval(interval);
  }, [activeTab, projectId, API_URL]);

  const handleUploadNow = async (index: number) => {
    if (!files?.schedule?.uploads[index] || !project) return;
    
    const upload = files.schedule.uploads[index];
    setUploadingIndex(index);
    
    try {
      const response = await fetch(`${API_URL}/api/youtube/upload-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: project._id,
          type: upload.type,
          title: upload.title,
          privacy: upload.privacy
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        // Mettre à jour le statut localement
        setFiles(prev => {
          if (!prev?.schedule) return prev;
          const newUploads = [...prev.schedule.uploads];
          newUploads[index] = { ...newUploads[index], status: 'uploaded' };
          return { ...prev, schedule: { ...prev.schedule, uploads: newUploads } };
        });
        alert(`✅ "${upload.title}" est maintenant en ligne !\n\nURL: ${result.url}`);
      } else {
        const error = await response.json();
        alert(`❌ Erreur: ${error.detail || 'Échec de la mise en ligne'}`);
      }
    } catch (err) {
      console.error('Erreur upload:', err);
      alert('❌ Erreur de connexion au serveur');
    } finally {
      setUploadingIndex(null);
    }
  };

  const handleUploadAll = async () => {
    if (!files?.schedule?.uploads) return;
    
    const pendingUploads = files.schedule.uploads
      .map((u, i) => ({ ...u, index: i }))
      .filter(u => u.status !== 'uploaded');
    
    for (const upload of pendingUploads) {
      await handleUploadNow(upload.index);
    }
  };

  const handleRegenerateThumbnail = async () => {
    if (!thumbnailCorrection.trim()) {
      alert('Veuillez entrer des corrections pour la miniature');
      return;
    }
    
    setRegeneratingThumbnail(true);
    try {
      const res = await fetch(`${API_URL}/api/projects/${projectId}/regenerate-thumbnail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ corrections: thumbnailCorrection })
      });
      
      if (res.ok) {
        alert('✅ Miniature régénérée avec succès !');
        setThumbnailCorrection('');
        // Recharger la page pour voir la nouvelle miniature
        window.location.reload();
      } else {
        const error = await res.json();
        alert(`❌ Erreur: ${error.detail || 'Échec de la régénération'}`);
      }
    } catch (err) {
      console.error('Erreur régénération:', err);
      alert('❌ Erreur de connexion au serveur');
    } finally {
      setRegeneratingThumbnail(false);
    }
  };

  const copyToClipboard = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const getVideoUrl = (filename: string) => {
    if (!project) return '';
    return `${API_URL}/output/${project.folder_name}/${filename}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-zinc-400">Projet non trouvé</p>
        <Link href="/projects" className="btn-secondary">
          Retour aux projets
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button 
          onClick={() => router.back()}
          className="p-2 hover:bg-zinc-800 rounded-lg transition"
        >
          <ArrowLeft className="w-5 h-5 text-zinc-400" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{project.name}</h1>
          <p className="text-zinc-500 font-mono text-sm">{project.folder_name}</p>
        </div>
        <div className="flex items-center gap-3">
          {project.status === 'processing' && (
            <button
              onClick={handleStopPipeline}
              disabled={stopping}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
            >
              {stopping ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <StopCircle className="w-4 h-4" />
              )}
              Stopper
            </button>
          )}
          <span className={`badge ${
            project.status === 'completed' ? 'badge-success' :
            project.status === 'processing' ? 'badge-info' :
            project.status === 'failed' ? 'badge-error' :
            project.status === 'stopped' ? 'bg-orange-500/20 text-orange-400' :
            'bg-zinc-800 text-zinc-400'
          }`}>
            {project.status === 'completed' ? 'Terminé' : 
             project.status === 'stopped' ? 'Arrêté' : 
             project.status}
          </span>
          
          {/* Bouton relancer upload */}
          {(project.status === 'completed' || project.status === 'stopped') && (
            <button
              onClick={() => handleRestartFromStep(11)}
              disabled={restarting}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
            >
              {restarting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              Relancer Upload
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('videos')}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === 'videos' 
              ? 'bg-violet-600 text-white' 
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          <Film className="w-4 h-4" />
          Vidéos
        </button>
        <button
          onClick={() => setActiveTab('shorts')}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === 'shorts' 
              ? 'bg-violet-600 text-white' 
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          <Smartphone className="w-4 h-4" />
          Shorts ({files?.shorts?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('seo')}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === 'seo' 
              ? 'bg-violet-600 text-white' 
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          <FileText className="w-4 h-4" />
          SEO
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === 'schedule' 
              ? 'bg-green-600 text-white' 
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          <Calendar className="w-4 h-4" />
          Programmation ({files?.schedule?.uploads?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('terminal')}
          className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
            activeTab === 'terminal' 
              ? 'bg-amber-600 text-white' 
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
        >
          <Terminal className="w-4 h-4" />
          Terminal
          {taskState && taskState !== 'SUCCESS' && taskState !== 'FAILURE' && (
            <Loader2 className="w-3 h-3 animate-spin" />
          )}
        </button>
      </div>

      {/* Content */}
      {activeTab === 'videos' && (
        <div className="space-y-6">
          {/* Vidéos traitées */}
          {(files?.illustrated || files?.nosilence) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Vidéo YouTube (illustrated) */}
              <div className="card overflow-hidden">
                <div className="p-4 border-b border-white/5 flex items-center gap-3">
                  <Youtube className="w-5 h-5 text-red-500" />
                  <h3 className="font-semibold text-white">Vidéo YouTube</h3>
                  <span className="text-xs text-zinc-500 ml-auto">illustrated.mp4</span>
                </div>
                <div className="aspect-video bg-black">
                  {files?.illustrated ? (
                    <video 
                      src={getVideoUrl('illustrated.mp4')} 
                      controls 
                      className="w-full h-full"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-600">
                      <Film className="w-12 h-12" />
                    </div>
                  )}
                </div>
                <div className="p-3 bg-zinc-900/50 flex gap-2">
                  <a 
                    href={getVideoUrl('illustrated.mp4')} 
                    download
                    className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                  >
                    <Download className="w-4 h-4" />
                    Télécharger
                  </a>
                </div>
              </div>

              {/* Vidéo Classroom (nosilence) */}
              <div className="card overflow-hidden">
                <div className="p-4 border-b border-white/5 flex items-center gap-3">
                  <Film className="w-5 h-5 text-blue-500" />
                  <h3 className="font-semibold text-white">Vidéo Classroom</h3>
                  <span className="text-xs text-zinc-500 ml-auto">nosilence.mp4</span>
                </div>
                <div className="aspect-video bg-black">
                  {files?.nosilence ? (
                    <video 
                      src={getVideoUrl('nosilence.mp4')} 
                      controls 
                      className="w-full h-full"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-zinc-600">
                      <Film className="w-12 h-12" />
                    </div>
                  )}
                </div>
                <div className="p-3 bg-zinc-900/50 flex gap-2">
                  <a 
                    href={getVideoUrl('nosilence.mp4')} 
                    download
                    className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                  >
                    <Download className="w-4 h-4" />
                    Télécharger
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Miniature */}
          {files?.thumbnail && (
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-white/5 flex items-center gap-3">
                <ImageIcon className="w-5 h-5 text-violet-500" />
                <h3 className="font-semibold text-white">Miniature YouTube</h3>
                <span className="text-xs text-zinc-500 ml-auto">thumbnail.png</span>
              </div>
              <div className="flex flex-col lg:flex-row gap-4 p-4 bg-zinc-900/30">
                <div className="w-full lg:w-96">
                  <img 
                    src={getVideoUrl('thumbnail.png')} 
                    alt="Miniature"
                    className="w-full rounded-lg shadow-xl"
                  />
                </div>
                <div className="flex-1 flex flex-col gap-3">
                  <div className="text-sm text-zinc-400 font-medium">🎨 Corrections miniature</div>
                  <textarea
                    value={thumbnailCorrection}
                    onChange={(e) => setThumbnailCorrection(e.target.value)}
                    placeholder="Ex: Plus de contraste, texte plus gros, fond plus sombre, enlever les flèches..."
                    className="w-full h-32 bg-zinc-800 text-white text-sm rounded-lg p-3 border border-zinc-700 focus:border-violet-500 focus:outline-none resize-none"
                  />
                  <p className="text-xs text-zinc-500">💡 Le visage sera conservé, seuls le style et les éléments seront modifiés.</p>
                  <button
                    onClick={handleRegenerateThumbnail}
                    disabled={regeneratingThumbnail || !thumbnailCorrection.trim()}
                    className="w-full px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
                  >
                    {regeneratingThumbnail ? (
                      <><Loader2 className="w-4 h-4 animate-spin" />Régénération...</>
                    ) : (
                      <><RefreshCw className="w-4 h-4" />Régénérer</>
                    )}
                  </button>
                </div>
              </div>
              <div className="p-3 bg-zinc-900/50 flex gap-2">
                <a 
                  href={getVideoUrl('thumbnail.png')} 
                  download
                  className="btn-secondary flex items-center gap-2 text-sm py-1.5"
                >
                  <Download className="w-4 h-4" />
                  Télécharger
                </a>
              </div>
            </div>
          )}

          {/* Fichiers sources */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center gap-3">
              <Video className="w-5 h-5 text-zinc-400" />
              <h3 className="font-semibold text-white">Fichiers sources</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
              {/* Original */}
              {files?.original && (
                <div className="bg-zinc-800/50 rounded-lg overflow-hidden">
                  <div className="aspect-video bg-black">
                    <video 
                      src={getVideoUrl('original.mp4')} 
                      controls 
                      className="w-full h-full"
                    />
                  </div>
                  <div className="p-3 flex items-center justify-between">
                    <span className="text-sm text-zinc-400">original.mp4</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowCutModal(true)}
                        className="p-1.5 text-amber-400 hover:text-amber-300 hover:bg-amber-500/20 rounded transition"
                        title="Découper la vidéo"
                      >
                        <Scissors className="w-4 h-4" />
                      </button>
                      <a 
                        href={getVideoUrl('original.mp4')} 
                        download
                        className="text-zinc-400 hover:text-white"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Screen */}
              <div className="bg-zinc-800/50 rounded-lg overflow-hidden">
                <div className="aspect-video bg-black">
                  <video 
                    src={getVideoUrl('screen.mp4')} 
                    controls 
                    className="w-full h-full"
                  />
                </div>
                <div className="p-3 flex items-center justify-between">
                  <span className="text-sm text-zinc-400">screen.mp4</span>
                  <a 
                    href={getVideoUrl('screen.mp4')} 
                    download
                    className="text-zinc-400 hover:text-white"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              </div>
              
              {/* Webcam */}
              <div className="bg-zinc-800/50 rounded-lg overflow-hidden">
                <div className="aspect-video bg-black">
                  <video 
                    src={getVideoUrl('webcam.mp4')} 
                    controls 
                    className="w-full h-full"
                  />
                </div>
                <div className="p-3 flex items-center justify-between">
                  <span className="text-sm text-zinc-400">webcam.mp4</span>
                  <a 
                    href={getVideoUrl('webcam.mp4')} 
                    download
                    className="text-zinc-400 hover:text-white"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Message si pas de vidéos traitées */}
          {!files?.illustrated && !files?.nosilence && (
            <div className="card p-8 text-center border-amber-500/20">
              <Loader2 className="w-8 h-8 text-amber-500 mx-auto mb-3 animate-spin" />
              <p className="text-zinc-400">Pipeline en cours de traitement...</p>
              <p className="text-zinc-500 text-sm mt-1">Les vidéos traitées apparaîtront ici une fois terminées.</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'shorts' && (
        <div className="flex flex-wrap justify-center gap-6">
          {files?.shorts && files.shorts.length > 0 ? (
            files.shorts.map((shortFile, index) => {
              const shortSeo = files.seo?.shorts?.[index];
              return (
                <div key={index} className="card overflow-hidden w-[280px] flex-shrink-0">
                  <div className="p-3 border-b border-white/5">
                    <h3 className="font-medium text-white text-sm truncate">
                      {shortSeo?.title || `Short ${index + 1}`}
                    </h3>
                  </div>
                  {/* Container 9:16 ratio */}
                  <div className="relative bg-black" style={{ paddingTop: '177.78%' }}>
                    <video 
                      src={getVideoUrl(`shorts/${shortFile}`)} 
                      controls 
                      className="absolute inset-0 w-full h-full object-contain"
                    />
                  </div>
                  <div className="p-3 bg-zinc-900/50 space-y-2">
                    {shortSeo && (
                      <>
                        <p className="text-xs text-zinc-400 line-clamp-2">
                          {shortSeo.description?.substring(0, 100)}...
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {shortSeo.tags?.slice(0, 3).map((tag, i) => (
                            <span key={i} className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </>
                    )}
                    <a 
                      href={getVideoUrl(`shorts/${shortFile}`)} 
                      download
                      className="btn-secondary flex items-center justify-center gap-2 text-sm py-1.5 w-full"
                    >
                      <Download className="w-4 h-4" />
                      Télécharger
                    </a>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="w-full card p-12 text-center">
              <Smartphone className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
              <p className="text-zinc-400">Aucun short généré</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'seo' && files?.seo && (
        <div className="space-y-6">
          {/* Vidéo principale */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center gap-3">
              <Youtube className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold text-white">SEO - Vidéo principale</h3>
            </div>
            <div className="p-6 space-y-6">
              {/* Titre */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-zinc-400">Titre</label>
                  <button
                    onClick={() => copyToClipboard(files.seo!.main_video.title, 'title')}
                    className="text-xs text-zinc-500 hover:text-white flex items-center gap-1"
                  >
                    {copiedField === 'title' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedField === 'title' ? 'Copié!' : 'Copier'}
                  </button>
                </div>
                <div className="bg-zinc-900 rounded-lg p-3 text-white">
                  {files.seo.main_video.title}
                </div>
              </div>

              {/* Description */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-zinc-400">Description</label>
                  <button
                    onClick={() => copyToClipboard(files.seo!.main_video.description, 'description')}
                    className="text-xs text-zinc-500 hover:text-white flex items-center gap-1"
                  >
                    {copiedField === 'description' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedField === 'description' ? 'Copié!' : 'Copier'}
                  </button>
                </div>
                <div className="bg-zinc-900 rounded-lg p-3 text-zinc-300 text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {files.seo.main_video.description}
                </div>
              </div>

              {/* Tags */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-zinc-400">
                    <Hash className="w-4 h-4 inline mr-1" />
                    Tags ({files.seo.main_video.tags?.length || 0})
                  </label>
                  <button
                    onClick={() => copyToClipboard(files.seo!.main_video.tags?.join(', ') || '', 'tags')}
                    className="text-xs text-zinc-500 hover:text-white flex items-center gap-1"
                  >
                    {copiedField === 'tags' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedField === 'tags' ? 'Copié!' : 'Copier tous'}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {files.seo.main_video.tags?.map((tag, i) => (
                    <span key={i} className="bg-violet-500/10 text-violet-400 px-3 py-1 rounded-full text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Commentaire épinglé */}
              {files.seo.main_video.pinned_comment && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-zinc-400">
                      <MessageSquare className="w-4 h-4 inline mr-1" />
                      Commentaire épinglé
                    </label>
                    <button
                      onClick={() => copyToClipboard(files.seo!.main_video.pinned_comment, 'comment')}
                      className="text-xs text-zinc-500 hover:text-white flex items-center gap-1"
                    >
                      {copiedField === 'comment' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      {copiedField === 'comment' ? 'Copié!' : 'Copier'}
                    </button>
                  </div>
                  <div className="bg-zinc-900 rounded-lg p-3 text-zinc-300 text-sm whitespace-pre-wrap">
                    {files.seo.main_video.pinned_comment}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Shorts SEO */}
          {files.seo.shorts && files.seo.shorts.length > 0 && (
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-white/5 flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-violet-500" />
                <h3 className="font-semibold text-white">SEO - Shorts</h3>
              </div>
              <div className="divide-y divide-white/5">
                {files.seo.shorts.map((short, index) => (
                  <div key={index} className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-white">Short {index + 1}</h4>
                      <button
                        onClick={() => copyToClipboard(
                          `${short.title}\n\n${short.description}\n\nTags: ${short.tags?.join(', ')}`,
                          `short-${index}`
                        )}
                        className="text-xs text-zinc-500 hover:text-white flex items-center gap-1"
                      >
                        {copiedField === `short-${index}` ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        Copier tout
                      </button>
                    </div>
                    <div className="text-sm text-zinc-300">{short.title}</div>
                    <div className="text-xs text-zinc-500 line-clamp-2">{short.description}</div>
                    <div className="flex flex-wrap gap-1">
                      {short.tags?.slice(0, 5).map((tag, i) => (
                        <span key={i} className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">
                          #{tag}
                        </span>
                      ))}
                      {short.tags && short.tags.length > 5 && (
                        <span className="text-xs text-zinc-500">+{short.tags.length - 5}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Schedule Tab */}
      {activeTab === 'schedule' && (
        <div className="space-y-4">
          {files?.schedule && files.schedule.uploads.length > 0 ? (
            <>
              <div className="card p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-green-500" />
                    Uploads programmés
                  </h3>
                  <span className="text-xs text-zinc-500">
                    Créé le {new Date(files.schedule.created_at).toLocaleDateString('fr-FR')}
                  </span>
                </div>
                
                <div className="space-y-3">
                  {files.schedule.uploads.map((upload, index) => (
                    <div 
                      key={index} 
                      className="bg-zinc-800/50 rounded-lg p-4 border border-white/5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            upload.type === 'illustrated' ? 'bg-red-500/20' : 
                            upload.type === 'classroom' ? 'bg-blue-500/20' : 'bg-violet-500/20'
                          }`}>
                            {upload.type === 'short' ? (
                              <Smartphone className="w-5 h-5 text-violet-400" />
                            ) : (
                              <Video className={`w-5 h-5 ${upload.type === 'illustrated' ? 'text-red-400' : 'text-blue-400'}`} />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-white">{upload.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                upload.type === 'illustrated' ? 'bg-red-500/20 text-red-400' :
                                upload.type === 'classroom' ? 'bg-blue-500/20 text-blue-400' :
                                'bg-violet-500/20 text-violet-400'
                              }`}>
                                {upload.type === 'illustrated' ? 'YouTube' : 
                                 upload.type === 'classroom' ? 'Classroom' : 'Short'}
                              </span>
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                upload.privacy === 'public' ? 'bg-green-500/20 text-green-400' :
                                'bg-yellow-500/20 text-yellow-400'
                              }`}>
                                {upload.privacy === 'public' ? 'Publique' : 'Non répertoriée'}
                              </span>
                              {upload.status === 'uploaded' && (
                                <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                                  ✓ En ligne
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="flex items-center gap-1 text-white">
                              <Calendar className="w-4 h-4 text-zinc-500" />
                              {upload.scheduled_date}
                            </div>
                            <div className="flex items-center gap-1 text-zinc-400 text-sm">
                              <Clock className="w-3 h-3" />
                              {upload.scheduled_time}
                            </div>
                          </div>
                          
                          {upload.status !== 'uploaded' && (
                            <button
                              onClick={() => handleUploadNow(index)}
                              disabled={uploadingIndex === index}
                              className="px-3 py-2 bg-green-600 hover:bg-green-500 disabled:bg-zinc-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
                            >
                              {uploadingIndex === index ? (
                                <>
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  Upload...
                                </>
                              ) : (
                                <>
                                  <Upload className="w-4 h-4" />
                                  Mettre en ligne
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {/* Description preview */}
                      <div className="mt-3 text-xs text-zinc-500 line-clamp-2">
                        {upload.description}
                      </div>
                      
                      {/* Tags */}
                      {upload.tags && upload.tags.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {upload.tags.slice(0, 5).map((tag, i) => (
                            <span key={i} className="text-xs bg-zinc-900 text-zinc-500 px-2 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                          {upload.tags.length > 5 && (
                            <span className="text-xs text-zinc-600">+{upload.tags.length - 5}</span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Actions globales */}
              <div className="card p-4 flex items-center justify-between">
                <div className="text-sm text-zinc-400">
                  {files.schedule.uploads.filter(u => u.status === 'uploaded').length} / {files.schedule.uploads.length} uploads effectués
                </div>
                <button
                  onClick={handleUploadAll}
                  disabled={uploadingIndex !== null || files.schedule.uploads.every(u => u.status === 'uploaded')}
                  className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-zinc-700 text-white font-medium rounded-lg transition flex items-center gap-2"
                >
                  <Upload className="w-4 h-4" />
                  Tout mettre en ligne maintenant
                </button>
              </div>
            </>
          ) : (
            <div className="card p-12 text-center">
              <Calendar className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
              <p className="text-zinc-400">Aucun upload programmé.</p>
              <p className="text-zinc-500 text-sm mt-2">
                La programmation sera créée automatiquement après le traitement.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Terminal Tab */}
      {activeTab === 'terminal' && (
        <div className="space-y-4">
          {/* Contrôles du pipeline */}
          <div className="card p-4">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Play className="w-5 h-5 text-green-500" />
              Contrôle du pipeline
            </h3>
            <div className="flex flex-wrap items-center gap-4">
              {/* Sélecteur d'étape */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-zinc-400">Relancer depuis :</label>
                <select
                  value={restartStep}
                  onChange={(e) => setRestartStep(Number(e.target.value))}
                  className="bg-zinc-800 text-white text-sm rounded-lg px-3 py-2 border border-zinc-700 focus:border-violet-500 focus:outline-none"
                >
                  {PIPELINE_STEPS.map((s) => (
                    <option key={s.step} value={s.step}>
                      {s.step}. {s.name}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Bouton relancer */}
              <button
                onClick={() => handleRestartFromStep()}
                disabled={restarting || (project?.status === 'processing' && taskState === 'PROGRESS')}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-2"
              >
                {restarting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Relancement...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Relancer
                  </>
                )}
              </button>

              {/* Indicateur étape actuelle */}
              {project?.current_step !== null && project?.current_step !== undefined && (
                <div className="text-sm text-zinc-400">
                  Étape actuelle : <span className="text-white font-medium">{project.current_step}. {PIPELINE_STEPS.find(s => s.step === project.current_step)?.name || 'Inconnue'}</span>
                </div>
              )}
            </div>
            
            {/* Info */}
            <p className="text-xs text-zinc-500 mt-3">
              💡 Les étapes précédentes ne seront pas ré-exécutées. Utilisez cette option si une étape a échoué ou est bloquée.
            </p>
          </div>

          {/* Logs */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-amber-500" />
                Logs en temps réel
              </h3>
              {taskState && (
                <span className={`text-xs px-2 py-1 rounded ${
                  taskState === 'SUCCESS' ? 'bg-green-500/20 text-green-400' :
                  taskState === 'FAILURE' ? 'bg-red-500/20 text-red-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {taskState === 'SUCCESS' ? '✓ Terminé' :
                   taskState === 'FAILURE' ? '✗ Échoué' :
                   taskState === 'PROGRESS' ? '⏳ En cours' :
                   '⏸ En attente'}
                </span>
              )}
            </div>
            <div className="p-4 bg-black/50 font-mono text-sm">
              <div className="h-[400px] overflow-y-auto space-y-1">
                {logs.length > 0 ? (
                  logs.map((log, index) => {
                    const isError = log.includes('[ERROR]') || log.includes('Erreur');
                    const isSuccess = log.includes('[SUCCESS]') || log.includes('OK');
                    const isInfo = log.includes('[INFO]') || log.includes('[STATUS]');
                    const isStep = log.includes('[Step');
                    
                    return (
                      <div
                        key={index}
                        className={`${
                          isError ? 'text-red-400' :
                          isSuccess ? 'text-green-400' :
                          isStep ? 'text-violet-400' :
                          isInfo ? 'text-blue-400' :
                          'text-zinc-300'
                        }`}
                      >
                        {log}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-zinc-500">Aucun log disponible...</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de découpe vidéo */}
      {project && (
        <VideoCutterModal
          isOpen={showCutModal}
          onClose={() => setShowCutModal(false)}
          videoUrl={getVideoUrl('original.mp4')}
          projectId={projectId}
          folderName={project.folder_name}
          onCutComplete={() => {
            setShowCutModal(false);
            // Recharger la page pour voir le nouveau pipeline
            window.location.reload();
          }}
        />
      )}
    </div>
  );
}

