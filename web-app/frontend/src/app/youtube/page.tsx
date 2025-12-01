'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Youtube,
  Users,
  Eye,
  ThumbsUp,
  MessageSquare,
  Clock,
  TrendingUp,
  Play,
  ExternalLink,
  LogIn,
  LogOut,
  Loader2,
  Video,
  Smartphone,
  BarChart3,
  Calendar,
  Share2,
  CalendarClock,
  Upload,
  CheckCircle,
  Info,
  Sparkles
} from 'lucide-react';

interface ChannelInfo {
  id: string;
  title: string;
  description: string;
  custom_url: string;
  thumbnail: string;
  banner: string | null;
  statistics: {
    subscribers: number;
    views: number;
    videos: number;
    hidden_subscribers: boolean;
  };
}

interface VideoInfo {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  published_at: string;
  duration: string;
  is_short: boolean;
  statistics: {
    views: number;
    likes: number;
    comments: number;
  };
  url: string;
}

interface Analytics {
  period: string;
  days: number;
  totals: {
    views: number;
    watch_time_minutes: number;
    subscribers_gained: number;
    subscribers_lost: number;
    likes: number;
    comments: number;
    shares: number;
  };
  daily: Array<{
    date: string;
    views: number;
    watch_time: number;
    subs_gained: number;
    subs_lost: number;
    likes: number;
    comments: number;
  }>;
}

interface Project {
  _id: string;
  name: string;
  folder_name: string;
  status: string;
  outputs: {
    illustrated: string | null;
    nosilence: string | null;
    thumbnail: string | null;
    shorts: Array<{ title: string; path: string }>;
    seo: {
      main_video: {
        title: string;
        description: string;
        tags: string[];
        pinned_comment: string;
      };
      shorts: Array<{
        title: string;
        description: string;
        tags?: string[];
        hashtags?: string[];
      }>;
    } | null;
  };
}

interface ScheduledUpload {
  projectId: string;
  projectName: string;
  type: 'illustrated' | 'classroom' | 'short';
  title: string;
  scheduledDate: string;
  scheduledTime: string;
  privacy: 'public' | 'unlisted' | 'private';
  status: 'pending' | 'uploaded' | 'failed';
}

// Heures optimales pour YouTube (France)
const OPTIMAL_HOURS = [
  { hour: '12:00', label: '12h - Pause déjeuner', score: 85 },
  { hour: '13:00', label: '13h - Pause déjeuner', score: 80 },
  { hour: '17:00', label: '17h - Fin de journée', score: 90 },
  { hour: '18:00', label: '18h - Soirée', score: 95 },
  { hour: '19:00', label: '19h - Prime time', score: 100 },
  { hour: '20:00', label: '20h - Prime time', score: 98 },
  { hour: '21:00', label: '21h - Soirée', score: 85 },
];

// Meilleurs jours (0 = Dimanche)
const OPTIMAL_DAYS = {
  0: { name: 'Dimanche', score: 75 },
  1: { name: 'Lundi', score: 70 },
  2: { name: 'Mardi', score: 90 },
  3: { name: 'Mercredi', score: 95 },
  4: { name: 'Jeudi', score: 90 },
  5: { name: 'Vendredi', score: 80 },
  6: { name: 'Samedi', score: 85 },
};

export default function YouTubePage() {
  const searchParams = useSearchParams();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState<ChannelInfo | null>(null);
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [shorts, setShorts] = useState<VideoInfo[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'videos' | 'shorts' | 'analytics' | 'schedule'>('overview');
  
  // Programmation
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [scheduledUploads, setScheduledUploads] = useState<ScheduledUpload[]>([]);
  const [scheduleForm, setScheduleForm] = useState({
    videoType: 'illustrated' as 'illustrated' | 'classroom' | 'both',
    videoDate: '',
    videoTime: '18:00',
    classroomDate: '',
    classroomTime: '10:00',
    shortDates: [] as { date: string; time: string }[],
  });

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  useEffect(() => {
    // Vérifier si on revient de l'auth
    const authStatus = searchParams.get('auth');
    if (authStatus === 'success') {
      window.history.replaceState({}, '', '/youtube');
    }
    
    checkStatus();
  }, [searchParams]);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/youtube/status`);
      const data = await res.json();
      setConnected(data.connected);
      setChannel(data.channel);
      
      if (data.connected) {
        loadData();
      }
    } catch (err) {
      console.error('Erreur:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadData = async () => {
    try {
      // Charger les vidéos
      const videosRes = await fetch(`${API_URL}/api/youtube/videos?max_results=20`);
      if (videosRes.ok) {
        const videosData = await videosRes.json();
        setVideos(videosData.videos || []);
        setShorts(videosData.shorts || []);
      }

      // Charger les analytics
      const analyticsRes = await fetch(`${API_URL}/api/youtube/analytics?days=28`);
      if (analyticsRes.ok) {
        const analyticsData = await analyticsRes.json();
        setAnalytics(analyticsData);
      }

      // Charger les projets terminés
      const projectsRes = await fetch(`${API_URL}/api/projects?status=completed`);
      if (projectsRes.ok) {
        const projectsData = await projectsRes.json();
        setProjects(projectsData.projects || []);
      }
    } catch (err) {
      console.error('Erreur chargement données:', err);
    }
  };

  // Générer les dates optimales pour la programmation
  const generateOptimalDates = (numDays: number = 7) => {
    const dates = [];
    const now = new Date();
    
    for (let i = 1; i <= numDays * 2; i++) {
      const date = new Date(now);
      date.setDate(date.getDate() + i);
      const dayOfWeek = date.getDay();
      const dayInfo = OPTIMAL_DAYS[dayOfWeek as keyof typeof OPTIMAL_DAYS];
      
      if (dayInfo.score >= 85) {
        dates.push({
          date: date.toISOString().split('T')[0],
          dayName: dayInfo.name,
          score: dayInfo.score,
        });
      }
      
      if (dates.length >= numDays) break;
    }
    
    return dates;
  };

  // Sélectionner un projet
  const handleSelectProject = async (project: Project) => {
    // Charger les détails complets du projet
    try {
      const res = await fetch(`${API_URL}/api/projects/${project._id}`);
      if (res.ok) {
        const fullProject = await res.json();
        setSelectedProject(fullProject);
        
        // Générer les dates optimales automatiquement
        const optimalDates = generateOptimalDates(2 + (fullProject.outputs?.shorts?.length || 0));
        
        // Date pour la vidéo principale (premier jour optimal)
        const videoDate = optimalDates[0]?.date || '';
        // Date pour Classroom (même jour ou lendemain)
        const classroomDate = optimalDates[0]?.date || '';
        
        // Dates pour les shorts (jours suivants, espacés)
        const shortDates = (fullProject.outputs?.shorts || []).map((_: any, index: number) => ({
          date: optimalDates[Math.min(index + 1, optimalDates.length - 1)]?.date || '',
          time: OPTIMAL_HOURS[index % OPTIMAL_HOURS.length].hour,
        }));
        
        setScheduleForm({
          videoType: 'illustrated',
          videoDate,
          videoTime: '18:00',
          classroomDate,
          classroomTime: '10:00',
          shortDates,
        });
      } else {
        setSelectedProject(project);
      }
    } catch (err) {
      console.error('Erreur chargement projet:', err);
      setSelectedProject(project);
    }
  };

  // Programmer les uploads
  const [scheduling, setScheduling] = useState(false);
  const [uploadingIndex, setUploadingIndex] = useState<number | null>(null);

  // Mettre en ligne immédiatement
  const handleUploadNow = async (index: number) => {
    const upload = scheduledUploads[index];
    if (!upload) return;
    
    setUploadingIndex(index);
    
    try {
      const response = await fetch(`${API_URL}/api/youtube/upload-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: upload.projectId,
          type: upload.type,
          title: upload.title,
          privacy: upload.privacy
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        // Mettre à jour le statut
        const newUploads = [...scheduledUploads];
        newUploads[index] = { ...newUploads[index], status: 'uploaded' };
        setScheduledUploads(newUploads);
        
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
  
  const handleScheduleUploads = async () => {
    if (!selectedProject) return;
    
    setScheduling(true);
    
    const uploads: any[] = [];
    
    // Vidéo Illustrated (publique)
    if ((scheduleForm.videoType === 'illustrated' || scheduleForm.videoType === 'both') && 
        selectedProject.outputs?.illustrated && scheduleForm.videoDate) {
      uploads.push({
        type: 'illustrated',
        file: selectedProject.outputs.illustrated,
        title: selectedProject.outputs?.seo?.main_video?.title || selectedProject.name,
        description: selectedProject.outputs?.seo?.main_video?.description || '',
        tags: selectedProject.outputs?.seo?.main_video?.tags || [],
        privacy: 'public',
        scheduledDate: scheduleForm.videoDate,
        scheduledTime: scheduleForm.videoTime,
      });
    }
    
    // Vidéo Classroom (non répertoriée)
    if ((scheduleForm.videoType === 'classroom' || scheduleForm.videoType === 'both') && 
        selectedProject.outputs?.nosilence && scheduleForm.classroomDate) {
      uploads.push({
        type: 'classroom',
        file: selectedProject.outputs.nosilence,
        title: `[Classroom] ${selectedProject.outputs?.seo?.main_video?.title || selectedProject.name}`,
        description: `Version complète pour les étudiants.\n\n${selectedProject.outputs?.seo?.main_video?.description || ''}`,
        tags: selectedProject.outputs?.seo?.main_video?.tags || [],
        privacy: 'unlisted',
        scheduledDate: scheduleForm.classroomDate,
        scheduledTime: scheduleForm.classroomTime,
      });
    }
    
    // Shorts (publics) - Format vertical 9:16, #Shorts obligatoire
    (selectedProject.outputs?.shorts || []).forEach((short: any, index: number) => {
      if (scheduleForm.shortDates[index]?.date) {
        const seoData = selectedProject.outputs?.seo?.shorts?.[index];
        
        // Utiliser le titre SEO en priorité (titre accrocheur généré par l'IA)
        let shortTitle = seoData?.title || short.title;
        
        // S'assurer que le titre contient #Shorts
        if (!shortTitle.includes('#Shorts') && !shortTitle.toLowerCase().includes('#shorts')) {
          shortTitle = `${shortTitle} #Shorts`;
        }
        
        // Description avec hashtags
        const hashtags = seoData?.hashtags || seoData?.tags || [];
        const hashtagsStr = hashtags.map((h: string) => h.startsWith('#') ? h : `#${h}`).join(' ');
        
        uploads.push({
          type: 'short',
          file: short.path,
          title: shortTitle,
          description: `${seoData?.description || ''}\n\n${hashtagsStr}\n\n#Shorts #Short #YouTubeShorts`,
          tags: [...hashtags.map((h: string) => h.replace('#', '')), 'Shorts', 'Short', 'YouTubeShorts'],
          privacy: 'public',
          scheduledDate: scheduleForm.shortDates[index].date,
          scheduledTime: scheduleForm.shortDates[index].time,
        });
      }
    });
    
    try {
      const response = await fetch(`${API_URL}/api/youtube/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject._id,
          folder_name: selectedProject.folder_name,
          uploads
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        // Ajouter à la liste locale
        const newScheduled = uploads.map(u => ({
          projectId: selectedProject._id,
          projectName: selectedProject.name,
          type: u.type,
          title: u.title,
          scheduledDate: u.scheduledDate,
          scheduledTime: u.scheduledTime,
          privacy: u.privacy,
          status: 'pending' as const,
        }));
        
        setScheduledUploads([...scheduledUploads, ...newScheduled]);
        setSelectedProject(null);
        alert(`✅ ${uploads.length} upload(s) programmé(s) avec succès !`);
      } else {
        const error = await response.json();
        alert(`❌ Erreur: ${error.detail || 'Échec de la programmation'}`);
      }
    } catch (err) {
      console.error('Erreur programmation:', err);
      alert('❌ Erreur de connexion au serveur');
    } finally {
      setScheduling(false);
    }
  };

  const handleConnect = async () => {
    try {
      const res = await fetch(`${API_URL}/api/youtube/auth/url`);
      const data = await res.json();
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      alert('Erreur connexion YouTube');
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Déconnecter votre chaîne YouTube ?')) return;
    
    try {
      await fetch(`${API_URL}/api/youtube/disconnect`, { method: 'POST' });
      setConnected(false);
      setChannel(null);
      setVideos([]);
      setShorts([]);
      setAnalytics(null);
    } catch (err) {
      alert('Erreur déconnexion');
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatWatchTime = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    if (hours >= 24) {
      const days = Math.floor(hours / 24);
      return `${days}j ${hours % 24}h`;
    }
    return `${hours}h ${Math.floor(minutes % 60)}m`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-red-500" />
      </div>
    );
  }

  // Non connecté
  if (!connected) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-2xl mx-auto">
          <div className="card p-12 text-center">
            <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <Youtube className="w-10 h-10 text-red-500" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-3">Connectez votre chaîne YouTube</h1>
            <p className="text-zinc-400 mb-8">
              Connectez votre compte Google pour voir vos statistiques, 
              gérer vos vidéos et publier directement depuis l'application.
            </p>
            <button
              onClick={handleConnect}
              className="btn-primary bg-red-600 hover:bg-red-700 flex items-center gap-2 mx-auto"
            >
              <LogIn className="w-5 h-5" />
              Se connecter avec Google
            </button>
            
            <div className="mt-8 pt-8 border-t border-white/5">
              <p className="text-xs text-zinc-500 mb-4">Configuration requise :</p>
              <ol className="text-left text-sm text-zinc-400 space-y-2">
                <li>1. Créer un projet sur <a href="https://console.cloud.google.com" target="_blank" className="text-violet-400 hover:underline">Google Cloud Console</a></li>
                <li>2. Activer <strong>YouTube Data API v3</strong> et <strong>YouTube Analytics API</strong></li>
                <li>3. Créer des identifiants <strong>OAuth 2.0</strong> (Type: Application Web)</li>
                <li>4. Ajouter <code className="bg-zinc-800 px-1 rounded text-xs">{API_URL}/api/youtube/auth/callback</code> comme URI de redirection</li>
                <li>5. Copier le <strong>Client ID</strong> et <strong>Client Secret</strong> dans <a href="/settings" className="text-violet-400 hover:underline">Paramètres</a></li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Connecté
  return (
    <div className="min-h-screen p-8">
      {/* Header avec infos chaîne */}
      <div className="card overflow-hidden mb-8">
        <div className="p-6 flex items-center gap-6">
          {channel?.thumbnail && (
            <img 
              src={channel.thumbnail} 
              alt={channel.title}
              className="w-20 h-20 rounded-full border-4 border-zinc-800"
            />
          )}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white">{channel?.title}</h1>
            <p className="text-zinc-400">{channel?.custom_url}</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{formatNumber(channel?.statistics.subscribers || 0)}</p>
              <p className="text-xs text-zinc-500">Abonnés</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{formatNumber(channel?.statistics.views || 0)}</p>
              <p className="text-xs text-zinc-500">Vues totales</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{channel?.statistics.videos || 0}</p>
              <p className="text-xs text-zinc-500">Vidéos</p>
            </div>
          </div>
          <button
            onClick={handleDisconnect}
            className="btn-secondary text-red-400 border-red-500/20 hover:border-red-500/40 flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Déconnecter
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {[
          { id: 'overview', label: 'Vue d\'ensemble', icon: BarChart3 },
          { id: 'videos', label: `Vidéos (${videos.length})`, icon: Video },
          { id: 'shorts', label: `Shorts (${shorts.length})`, icon: Smartphone },
          { id: 'analytics', label: 'Analytics', icon: TrendingUp },
          { id: 'schedule', label: 'Programmation', icon: CalendarClock },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === tab.id 
                ? 'bg-red-600 text-white' 
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'overview' && analytics && (
        <div className="space-y-6">
          {/* Stats 28 jours */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Eye className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-zinc-500">Vues</span>
              </div>
              <p className="text-xl font-bold text-white">{formatNumber(analytics.totals.views)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-green-400" />
                <span className="text-xs text-zinc-500">Temps regardé</span>
              </div>
              <p className="text-xl font-bold text-white">{formatWatchTime(analytics.totals.watch_time_minutes)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-violet-400" />
                <span className="text-xs text-zinc-500">Nouveaux abonnés</span>
              </div>
              <p className="text-xl font-bold text-green-400">+{formatNumber(analytics.totals.subscribers_gained)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4 text-red-400" />
                <span className="text-xs text-zinc-500">Désabonnés</span>
              </div>
              <p className="text-xl font-bold text-red-400">-{formatNumber(analytics.totals.subscribers_lost)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsUp className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-zinc-500">Likes</span>
              </div>
              <p className="text-xl font-bold text-white">{formatNumber(analytics.totals.likes)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="w-4 h-4 text-yellow-400" />
                <span className="text-xs text-zinc-500">Commentaires</span>
              </div>
              <p className="text-xl font-bold text-white">{formatNumber(analytics.totals.comments)}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <Share2 className="w-4 h-4 text-pink-400" />
                <span className="text-xs text-zinc-500">Partages</span>
              </div>
              <p className="text-xl font-bold text-white">{formatNumber(analytics.totals.shares)}</p>
            </div>
          </div>

          {/* Dernières vidéos */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-white/5 flex items-center gap-2">
                <Video className="w-5 h-5 text-red-500" />
                <h3 className="font-semibold text-white">Dernières vidéos</h3>
              </div>
              <div className="divide-y divide-white/5">
                {videos.slice(0, 5).map((video) => (
                  <a 
                    key={video.id}
                    href={video.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 hover:bg-zinc-800/50 transition"
                  >
                    <img 
                      src={video.thumbnail} 
                      alt={video.title}
                      className="w-24 h-14 object-cover rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{video.title}</p>
                      <p className="text-xs text-zinc-500">
                        {formatNumber(video.statistics.views)} vues • {formatDate(video.published_at)}
                      </p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-zinc-500" />
                  </a>
                ))}
              </div>
            </div>

            <div className="card overflow-hidden">
              <div className="p-4 border-b border-white/5 flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-violet-500" />
                <h3 className="font-semibold text-white">Derniers shorts</h3>
              </div>
              <div className="divide-y divide-white/5">
                {shorts.length > 0 ? shorts.slice(0, 5).map((short) => (
                  <a 
                    key={short.id}
                    href={short.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 hover:bg-zinc-800/50 transition"
                  >
                    <img 
                      src={short.thumbnail} 
                      alt={short.title}
                      className="w-10 h-14 object-cover rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{short.title}</p>
                      <p className="text-xs text-zinc-500">
                        {formatNumber(short.statistics.views)} vues
                      </p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-zinc-500" />
                  </a>
                )) : (
                  <div className="p-8 text-center text-zinc-500">
                    Aucun short trouvé
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'videos' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {videos.map((video) => (
            <a 
              key={video.id}
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card overflow-hidden group"
            >
              <div className="relative aspect-video">
                <img 
                  src={video.thumbnail} 
                  alt={video.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                  <Play className="w-12 h-12 text-white" />
                </div>
              </div>
              <div className="p-3">
                <h3 className="font-medium text-white text-sm line-clamp-2 mb-2">{video.title}</h3>
                <div className="flex items-center gap-3 text-xs text-zinc-500">
                  <span className="flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    {formatNumber(video.statistics.views)}
                  </span>
                  <span className="flex items-center gap-1">
                    <ThumbsUp className="w-3 h-3" />
                    {formatNumber(video.statistics.likes)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(video.published_at)}
                  </span>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {activeTab === 'shorts' && (
        <div className="flex flex-wrap justify-center gap-4">
          {shorts.length > 0 ? shorts.map((short) => (
            <a 
              key={short.id}
              href={short.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card overflow-hidden w-[200px] group"
            >
              <div className="relative" style={{ paddingTop: '177.78%' }}>
                <img 
                  src={short.thumbnail} 
                  alt={short.title}
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                  <Play className="w-10 h-10 text-white" />
                </div>
              </div>
              <div className="p-3">
                <h3 className="font-medium text-white text-xs line-clamp-2 mb-1">{short.title}</h3>
                <p className="text-xs text-zinc-500">{formatNumber(short.statistics.views)} vues</p>
              </div>
            </a>
          )) : (
            <div className="card p-12 text-center w-full">
              <Smartphone className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
              <p className="text-zinc-400">Aucun short trouvé</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'analytics' && analytics && (
        <div className="space-y-6">
          <div className="card p-4">
            <h3 className="font-semibold text-white mb-4">Vues par jour (28 derniers jours)</h3>
            <div className="h-48 flex items-end gap-1">
              {analytics.daily.map((day, i) => {
                const maxViews = Math.max(...analytics.daily.map(d => d.views));
                const height = maxViews > 0 ? (day.views / maxViews) * 100 : 0;
                return (
                  <div 
                    key={i}
                    className="flex-1 bg-red-500/20 hover:bg-red-500/40 transition rounded-t relative group"
                    style={{ height: `${Math.max(height, 2)}%` }}
                  >
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-zinc-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap">
                      {day.date}: {formatNumber(day.views)} vues
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="p-4 border-b border-white/5">
              <h3 className="font-semibold text-white">Détail par jour</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-zinc-900/50">
                    <th className="text-left p-3 text-xs font-medium text-zinc-500">Date</th>
                    <th className="text-right p-3 text-xs font-medium text-zinc-500">Vues</th>
                    <th className="text-right p-3 text-xs font-medium text-zinc-500">Temps regardé</th>
                    <th className="text-right p-3 text-xs font-medium text-zinc-500">Abonnés</th>
                    <th className="text-right p-3 text-xs font-medium text-zinc-500">Likes</th>
                    <th className="text-right p-3 text-xs font-medium text-zinc-500">Commentaires</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {analytics.daily.slice().reverse().map((day, i) => (
                    <tr key={i} className="hover:bg-zinc-800/30">
                      <td className="p-3 text-sm text-white">{day.date}</td>
                      <td className="p-3 text-sm text-zinc-300 text-right">{formatNumber(day.views)}</td>
                      <td className="p-3 text-sm text-zinc-300 text-right">{formatWatchTime(day.watch_time)}</td>
                      <td className="p-3 text-sm text-right">
                        <span className="text-green-400">+{day.subs_gained}</span>
                        <span className="text-zinc-500 mx-1">/</span>
                        <span className="text-red-400">-{day.subs_lost}</span>
                      </td>
                      <td className="p-3 text-sm text-zinc-300 text-right">{formatNumber(day.likes)}</td>
                      <td className="p-3 text-sm text-zinc-300 text-right">{formatNumber(day.comments)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Onglet Programmation */}
      {activeTab === 'schedule' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sélection du projet */}
          <div className="lg:col-span-1">
            <div className="card p-4">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Video className="w-5 h-5 text-violet-400" />
                Projets terminés
              </h3>
              
              {projects.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">
                  <Video className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Aucun projet terminé</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {projects.map((project) => (
                    <button
                      key={project._id}
                      onClick={() => handleSelectProject(project)}
                      className={`w-full text-left p-3 rounded-lg border transition ${
                        selectedProject?._id === project._id
                          ? 'border-violet-500 bg-violet-500/10'
                          : 'border-white/5 hover:border-white/20 bg-zinc-800/50'
                      }`}
                    >
                      <p className="font-medium text-white text-sm truncate">{project.name}</p>
                      <p className="text-xs text-zinc-500 truncate">{project.folder_name}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {project.outputs.illustrated && (
                          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                            YouTube
                          </span>
                        )}
                        {project.outputs.nosilence && (
                          <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">
                            Classroom
                          </span>
                        )}
                        {project.outputs.shorts?.length > 0 && (
                          <span className="text-xs bg-violet-500/20 text-violet-400 px-2 py-0.5 rounded">
                            {project.outputs.shorts.length} shorts
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Heures optimales */}
            <div className="card p-4 mt-4">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-yellow-400" />
                Heures optimales
              </h3>
              <div className="space-y-2">
                {OPTIMAL_HOURS.map((h) => (
                  <div key={h.hour} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400">{h.label}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-yellow-500 to-green-500 rounded-full"
                          style={{ width: `${h.score}%` }}
                        />
                      </div>
                      <span className="text-xs text-zinc-500 w-8">{h.score}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Formulaire de programmation */}
          <div className="lg:col-span-2">
            {selectedProject ? (
              <div className="space-y-4">
                {/* Infos projet sélectionné */}
                <div className="card p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-white">{selectedProject.name}</h3>
                    <button 
                      onClick={() => setSelectedProject(null)}
                      className="text-zinc-500 hover:text-white text-sm"
                    >
                      ✕ Fermer
                    </button>
                  </div>

                  {/* SEO Preview */}
                  {selectedProject.outputs.seo?.main_video && (
                    <div className="bg-zinc-800/50 rounded-lg p-3 mb-4">
                      <p className="font-medium text-white text-sm mb-1">
                        {selectedProject.outputs.seo.main_video.title}
                      </p>
                      <p className="text-xs text-zinc-400 line-clamp-2">
                        {selectedProject.outputs.seo.main_video.description}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {selectedProject.outputs.seo.main_video.tags.slice(0, 5).map((tag, i) => (
                          <span key={i} className="text-xs bg-zinc-700 text-zinc-300 px-2 py-0.5 rounded">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Choix du type de vidéo */}
                <div className="card p-4">
                  <h4 className="font-medium text-white mb-3">Type de vidéo à publier</h4>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => setScheduleForm({ ...scheduleForm, videoType: 'illustrated' })}
                      className={`p-3 rounded-lg border text-center transition ${
                        scheduleForm.videoType === 'illustrated'
                          ? 'border-red-500 bg-red-500/10 text-white'
                          : 'border-white/10 text-zinc-400 hover:border-white/20'
                      }`}
                    >
                      <Video className="w-5 h-5 mx-auto mb-1" />
                      <p className="text-xs font-medium">Illustrated</p>
                      <p className="text-[10px] text-zinc-500">Publique</p>
                    </button>
                    <button
                      onClick={() => setScheduleForm({ ...scheduleForm, videoType: 'classroom' })}
                      className={`p-3 rounded-lg border text-center transition ${
                        scheduleForm.videoType === 'classroom'
                          ? 'border-blue-500 bg-blue-500/10 text-white'
                          : 'border-white/10 text-zinc-400 hover:border-white/20'
                      }`}
                    >
                      <Video className="w-5 h-5 mx-auto mb-1" />
                      <p className="text-xs font-medium">Classroom</p>
                      <p className="text-[10px] text-zinc-500">Non répertoriée</p>
                    </button>
                    <button
                      onClick={() => setScheduleForm({ ...scheduleForm, videoType: 'both' })}
                      className={`p-3 rounded-lg border text-center transition ${
                        scheduleForm.videoType === 'both'
                          ? 'border-violet-500 bg-violet-500/10 text-white'
                          : 'border-white/10 text-zinc-400 hover:border-white/20'
                      }`}
                    >
                      <Video className="w-5 h-5 mx-auto mb-1" />
                      <p className="text-xs font-medium">Les deux</p>
                      <p className="text-[10px] text-zinc-500">Pub + Non rép.</p>
                    </button>
                  </div>
                </div>

                {/* Programmation vidéo Illustrated */}
                {(scheduleForm.videoType === 'illustrated' || scheduleForm.videoType === 'both') && 
                 selectedProject.outputs.illustrated && (
                  <div className="card p-4">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                        <Video className="w-5 h-5 text-red-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-white">Vidéo YouTube</h4>
                        <p className="text-xs text-zinc-500">illustrated.mp4</p>
                      </div>
                      <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">Publique</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-zinc-400 mb-1">Date</label>
                        <input
                          type="date"
                          value={scheduleForm.videoDate}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, videoDate: e.target.value })}
                          className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-zinc-400 mb-1">Heure</label>
                        <select
                          value={scheduleForm.videoTime}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, videoTime: e.target.value })}
                          className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-violet-500 focus:outline-none"
                        >
                          {OPTIMAL_HOURS.map((h) => (
                            <option key={h.hour} value={h.hour}>
                              {h.hour} - {h.score}% optimal
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                )}

                {/* Programmation vidéo Classroom */}
                {(scheduleForm.videoType === 'classroom' || scheduleForm.videoType === 'both') && 
                 selectedProject.outputs.nosilence && (
                  <div className="card p-4">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                        <Video className="w-5 h-5 text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-white">Vidéo Classroom</h4>
                        <p className="text-xs text-zinc-500">nosilence.mp4 (sans B-roll)</p>
                      </div>
                      <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">Non répertoriée</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-zinc-400 mb-1">Date</label>
                        <input
                          type="date"
                          value={scheduleForm.classroomDate}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, classroomDate: e.target.value })}
                          className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-zinc-400 mb-1">Heure</label>
                        <select
                          value={scheduleForm.classroomTime}
                          onChange={(e) => setScheduleForm({ ...scheduleForm, classroomTime: e.target.value })}
                          className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-violet-500 focus:outline-none"
                        >
                          <option value="08:00">08:00 - Matin</option>
                          <option value="09:00">09:00 - Matin</option>
                          <option value="10:00">10:00 - Matin</option>
                          <option value="14:00">14:00 - Après-midi</option>
                          <option value="15:00">15:00 - Après-midi</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}

                {/* Programmation shorts */}
                {selectedProject.outputs.shorts?.length > 0 && (
                  <div className="card p-4">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
                        <Smartphone className="w-5 h-5 text-violet-400" />
                      </div>
                      <div>
                        <h4 className="font-medium text-white">Shorts ({selectedProject.outputs.shorts.length})</h4>
                        <p className="text-xs text-zinc-500">Programmez chaque short séparément</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {selectedProject.outputs.shorts.map((short, index) => (
                        <div key={index} className="bg-zinc-800/50 rounded-lg p-3">
                          <p className="text-sm text-white mb-2 truncate">{short.title}</p>
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="date"
                              value={scheduleForm.shortDates[index]?.date || ''}
                              onChange={(e) => {
                                const newDates = [...scheduleForm.shortDates];
                                newDates[index] = { ...newDates[index], date: e.target.value };
                                setScheduleForm({ ...scheduleForm, shortDates: newDates });
                              }}
                              className="bg-zinc-700 border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:border-violet-500 focus:outline-none"
                            />
                            <select
                              value={scheduleForm.shortDates[index]?.time || '18:00'}
                              onChange={(e) => {
                                const newDates = [...scheduleForm.shortDates];
                                newDates[index] = { ...newDates[index], time: e.target.value };
                                setScheduleForm({ ...scheduleForm, shortDates: newDates });
                              }}
                              className="bg-zinc-700 border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:border-violet-500 focus:outline-none"
                            >
                              {OPTIMAL_HOURS.map((h) => (
                                <option key={h.hour} value={h.hour}>{h.hour}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Aperçu de la publication */}
                <div className="card p-4">
                  <h4 className="font-medium text-white mb-4 flex items-center gap-2">
                    <Eye className="w-5 h-5 text-cyan-400" />
                    Aperçu de la publication
                  </h4>

                  {/* Aperçu Illustrated */}
                  {(scheduleForm.videoType === 'illustrated' || scheduleForm.videoType === 'both') && 
                   selectedProject.outputs.illustrated && (
                    <div className="mb-4 p-4 bg-zinc-800/50 rounded-lg border border-red-500/20">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-6 h-6 rounded bg-red-500/20 flex items-center justify-center">
                          <Video className="w-3 h-3 text-red-400" />
                        </div>
                        <span className="text-sm font-medium text-white">Vidéo YouTube</span>
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded ml-auto">Publique</span>
                      </div>
                      
                      <div className="space-y-3">
                        <div>
                          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Titre</label>
                          <p className="text-sm text-white font-medium">
                            {selectedProject.outputs.seo?.main_video?.title || selectedProject.name}
                          </p>
                        </div>
                        
                        <div>
                          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Description</label>
                          {selectedProject.outputs.seo?.main_video?.description ? (
                            <p className="text-xs text-zinc-400 whitespace-pre-wrap line-clamp-4">
                              {selectedProject.outputs.seo.main_video.description}
                            </p>
                          ) : (
                            <p className="text-xs text-zinc-500 italic">Description générée automatiquement</p>
                          )}
                        </div>
                        
                        <div>
                          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">
                            Tags {selectedProject.outputs?.seo?.main_video?.tags?.length ? `(${selectedProject.outputs.seo.main_video.tags.length})` : ''}
                          </label>
                          {selectedProject.outputs?.seo?.main_video?.tags && selectedProject.outputs.seo.main_video.tags.length > 0 ? (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {selectedProject.outputs.seo.main_video.tags.slice(0, 8).map((tag: string, i: number) => (
                                <span key={i} className="text-[10px] bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded">#{tag}</span>
                              ))}
                              {selectedProject.outputs.seo.main_video.tags.length > 8 && (
                                <span className="text-[10px] text-zinc-500">+{selectedProject.outputs.seo.main_video.tags.length - 8}</span>
                              )}
                            </div>
                          ) : (
                            <p className="text-xs text-zinc-500 italic mt-1">Tags générés automatiquement</p>
                          )}
                        </div>

                        {selectedProject.outputs?.seo?.main_video?.pinned_comment && (
                          <div>
                            <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Commentaire épinglé</label>
                            <p className="text-xs text-zinc-400 italic">"{String(selectedProject.outputs.seo.main_video.pinned_comment).slice(0, 100)}..."</p>
                          </div>
                        )}

                        <div className="flex items-center gap-4 pt-2 border-t border-white/5">
                          <div>
                            <label className="text-[10px] text-zinc-500">Date</label>
                            <p className="text-sm text-white">{scheduleForm.videoDate || 'Non définie'}</p>
                          </div>
                          <div>
                            <label className="text-[10px] text-zinc-500">Heure</label>
                            <p className="text-sm text-white">{scheduleForm.videoTime}</p>
                          </div>
                        </div>

                        <div className="text-xs text-zinc-500 pt-2 border-t border-white/5 space-y-1">
                          <div>📁 Fichier: <span className="text-zinc-400">illustrated.mp4</span></div>
                          {selectedProject.outputs?.thumbnail && (
                            <div>🖼️ Miniature: <span className="text-green-400">thumbnail.png ✓</span></div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Aperçu Classroom */}
                  {(scheduleForm.videoType === 'classroom' || scheduleForm.videoType === 'both') && 
                   selectedProject.outputs.nosilence && (
                    <div className="mb-4 p-4 bg-zinc-800/50 rounded-lg border border-blue-500/20">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center">
                          <Video className="w-3 h-3 text-blue-400" />
                        </div>
                        <span className="text-sm font-medium text-white">Vidéo Classroom</span>
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded ml-auto">Non répertoriée</span>
                      </div>
                      
                      <div className="space-y-3">
                        <div>
                          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Titre</label>
                          <p className="text-sm text-white font-medium">
                            [Classroom] {selectedProject.outputs.seo?.main_video?.title || selectedProject.name}
                          </p>
                        </div>
                        
                        <div>
                          <label className="text-[10px] text-zinc-500 uppercase tracking-wide">Description</label>
                          <p className="text-xs text-zinc-400">Version complète sans illustrations pour les étudiants.</p>
                          <p className="text-xs text-zinc-500 mt-1">+ Description originale de la vidéo</p>
                        </div>

                        <div className="flex items-center gap-4 pt-2 border-t border-white/5">
                          <div>
                            <label className="text-[10px] text-zinc-500">Date</label>
                            <p className="text-sm text-white">{scheduleForm.classroomDate || 'Non définie'}</p>
                          </div>
                          <div>
                            <label className="text-[10px] text-zinc-500">Heure</label>
                            <p className="text-sm text-white">{scheduleForm.classroomTime}</p>
                          </div>
                        </div>

                        <div className="text-xs text-zinc-500 pt-2 border-t border-white/5 space-y-1">
                          <div>📁 Fichier: <span className="text-zinc-400">nosilence.mp4</span></div>
                          {selectedProject.outputs?.thumbnail && (
                            <div>🖼️ Miniature: <span className="text-green-400">thumbnail.png ✓</span></div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Aperçu Shorts */}
                  {selectedProject.outputs?.shorts && selectedProject.outputs.shorts.length > 0 && (
                    <div className="p-4 bg-zinc-800/50 rounded-lg border border-violet-500/20">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-6 h-6 rounded bg-violet-500/20 flex items-center justify-center">
                          <Smartphone className="w-3 h-3 text-violet-400" />
                        </div>
                        <span className="text-sm font-medium text-white">Shorts ({selectedProject.outputs.shorts.length})</span>
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded ml-auto">Publiques</span>
                      </div>

                      <div className="space-y-3">
                        {(selectedProject.outputs?.shorts || []).map((short: any, index: number) => {
                          const seoData = selectedProject.outputs?.seo?.shorts?.[index];
                          const dateInfo = scheduleForm.shortDates[index];
                          // Titre SEO en priorité
                          const displayTitle = seoData?.title || short.title;
                          
                          return (
                            <div key={index} className="p-3 bg-zinc-900/50 rounded-lg">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-medium text-white truncate">
                                    {displayTitle} {!displayTitle.includes('#Shorts') && '#Shorts'}
                                  </p>
                                  {seoData && (
                                    <>
                                      <p className="text-[10px] text-zinc-500 mt-1 line-clamp-2">{seoData.description}</p>
                                      {((seoData.tags || seoData.hashtags) && (seoData.tags?.length || seoData.hashtags?.length)) ? (
                                        <div className="flex flex-wrap gap-1 mt-1">
                                          {(seoData.tags || seoData.hashtags || []).slice(0, 4).map((tag: string, i: number) => (
                                            <span key={i} className="text-[9px] bg-zinc-700 text-zinc-400 px-1 py-0.5 rounded">{tag.startsWith('#') ? tag : `#${tag}`}</span>
                                          ))}
                                        </div>
                                      ) : null}
                                    </>
                                  )}
                                </div>
                                <div className="text-right shrink-0">
                                  <p className="text-xs text-white">{dateInfo?.date || '—'}</p>
                                  <p className="text-[10px] text-zinc-500">{dateInfo?.time || '—'}</p>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bouton programmer */}
                <button
                  onClick={handleScheduleUploads}
                  disabled={scheduling}
                  className="w-full bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 disabled:from-zinc-600 disabled:to-zinc-600 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition"
                >
                  {scheduling ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Programmation en cours...
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5" />
                      Programmer les uploads
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="card p-12 text-center">
                <CalendarClock className="w-16 h-16 text-zinc-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Programmez vos uploads</h3>
                <p className="text-zinc-400 mb-4">
                  Sélectionnez un projet terminé pour programmer la publication de la vidéo et des shorts sur YouTube.
                </p>
                <div className="flex items-center justify-center gap-2 text-sm text-zinc-500">
                  <Info className="w-4 h-4" />
                  Les dates sont suggérées selon les meilleurs moments pour publier
                </div>
              </div>
            )}

            {/* Uploads programmés */}
            {scheduledUploads.length > 0 && (
              <div className="card p-4 mt-4">
                <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  Uploads programmés ({scheduledUploads.length})
                </h3>
                <div className="space-y-2">
                  {scheduledUploads.map((upload, index) => (
                    <div key={index} className="flex items-center justify-between bg-zinc-800/50 rounded-lg p-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded flex items-center justify-center ${
                          upload.type === 'illustrated' ? 'bg-red-500/20' : 
                          upload.type === 'classroom' ? 'bg-blue-500/20' : 'bg-violet-500/20'
                        }`}>
                          {upload.type === 'short' ? (
                            <Smartphone className="w-4 h-4 text-violet-400" />
                          ) : (
                            <Video className={`w-4 h-4 ${upload.type === 'illustrated' ? 'text-red-400' : 'text-blue-400'}`} />
                          )}
                        </div>
                        <div>
                          <p className="text-sm text-white truncate max-w-xs">{upload.title}</p>
                          <div className="flex items-center gap-2">
                            <p className="text-xs text-zinc-500">{upload.projectName}</p>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                              upload.privacy === 'public' ? 'bg-green-500/20 text-green-400' :
                              upload.privacy === 'unlisted' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-zinc-500/20 text-zinc-400'
                            }`}>
                              {upload.privacy === 'public' ? 'Publique' : 
                               upload.privacy === 'unlisted' ? 'Non répertoriée' : 'Privée'}
                            </span>
                            {upload.status === 'pending' && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">
                                En attente
                              </span>
                            )}
                            {upload.status === 'uploaded' && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">
                                ✓ En ligne
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <p className="text-sm text-white">{upload.scheduledDate}</p>
                          <p className="text-xs text-zinc-500">{upload.scheduledTime}</p>
                        </div>
                        {upload.status === 'pending' && (
                          <button
                            onClick={() => handleUploadNow(index)}
                            disabled={uploadingIndex === index}
                            className="px-3 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-zinc-600 text-white text-xs font-medium rounded-lg transition flex items-center gap-1"
                          >
                            {uploadingIndex === index ? (
                              <>
                                <Loader2 className="w-3 h-3 animate-spin" />
                                Upload...
                              </>
                            ) : (
                              <>
                                <Upload className="w-3 h-3" />
                                Mettre en ligne
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

