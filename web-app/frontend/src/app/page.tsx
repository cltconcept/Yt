'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Video, 
  FolderKanban, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  PlayCircle,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Youtube,
  Users,
  Eye,
  ThumbsUp,
  ExternalLink,
  Instagram
} from 'lucide-react';

interface Stats {
  total: number;
  created: number;
  processing: number;
  completed: number;
  failed: number;
}

interface RecentProject {
  _id: string;
  name: string;
  folder_name: string;
  status: string;
  progress: number;
  created_at: string;
}

interface YouTubeStats {
  connected: boolean;
  channel: {
    title: string;
    thumbnail: string;
    statistics: {
      subscribers: number;
      views: number;
      videos: number;
    };
  } | null;
  analytics: {
    totals: {
      views: number;
      subscribers_gained: number;
      likes: number;
    };
  } | null;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
  const [youtubeStats, setYoutubeStats] = useState<YouTubeStats | null>(null);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch stats
        const statsRes = await fetch(`${API_URL}/api/projects/stats`);
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }

        // Fetch recent projects
        const projectsRes = await fetch(`${API_URL}/api/projects?limit=5`);
        if (projectsRes.ok) {
          const projectsData = await projectsRes.json();
          setRecentProjects(projectsData.projects || []);
        }

        // Fetch YouTube stats
        const ytRes = await fetch(`${API_URL}/api/youtube/dashboard-stats`);
        if (ytRes.ok) {
          const ytData = await ytRes.json();
          setYoutubeStats(ytData);
        }
      } catch (error) {
        console.error('Erreur chargement données:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [API_URL]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'processing': return <PlayCircle className="w-4 h-4 text-blue-400 animate-pulse" />;
      case 'failed': return <AlertCircle className="w-4 h-4 text-red-400" />;
      default: return <Clock className="w-4 h-4 text-zinc-400" />;
    }
  };

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-zinc-400">Bienvenue sur votre pipeline vidéo YouTube</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link href="/record" className="group">
          <div className="card p-6 hover:border-violet-500/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-violet-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Video className="w-6 h-6 text-violet-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Nouvel enregistrement</h3>
                  <p className="text-sm text-zinc-400">Démarrer une nouvelle vidéo</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-violet-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        </Link>

        <Link href="/projects" className="group">
          <div className="card p-6 hover:border-cyan-500/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <FolderKanban className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Mes projets</h3>
                  <p className="text-sm text-zinc-400">Gérer vos vidéos</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        </Link>

        <Link href="/youtube" className="group">
          <div className="card p-6 hover:border-red-500/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500/20 to-red-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Youtube className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">YouTube</h3>
                  <p className="text-sm text-zinc-400">
                    {youtubeStats?.connected ? 'Voir vos stats' : 'Connecter votre chaîne'}
                  </p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-red-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        </Link>

        <Link href="/tiktok" className="group">
          <div className="card p-6 hover:border-pink-500/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500/20 via-red-500/10 to-yellow-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <svg className="w-6 h-6 text-pink-400" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z"/>
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-white">TikTok</h3>
                  <p className="text-sm text-zinc-400">Préparer vos shorts</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-pink-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        </Link>

        <Link href="/instagram" className="group">
          <div className="card p-6 hover:border-purple-500/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 via-pink-500/10 to-orange-500/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Instagram className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Instagram</h3>
                  <p className="text-sm text-zinc-400">Publier vos Reels</p>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-zinc-500 group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        </Link>
      </div>

      {/* YouTube Stats */}
      {youtubeStats?.connected && youtubeStats.channel && (
        <div className="card mb-8 overflow-hidden">
          <div className="p-4 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Youtube className="w-5 h-5 text-red-500" />
              <span className="font-semibold text-white">YouTube Stats</span>
              <span className="text-xs text-zinc-500">28 derniers jours</span>
            </div>
            <Link href="/youtube" className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1">
              Voir plus <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-6">
              <img 
                src={youtubeStats.channel.thumbnail} 
                alt={youtubeStats.channel.title}
                className="w-14 h-14 rounded-full border-2 border-red-500/20"
              />
              <div className="flex-1">
                <p className="font-semibold text-white">{youtubeStats.channel.title}</p>
                <p className="text-sm text-zinc-500">{formatNumber(youtubeStats.channel.statistics.subscribers)} abonnés</p>
              </div>
              <div className="flex gap-8">
                <div className="text-center">
                  <div className="flex items-center gap-1 justify-center mb-1">
                    <Eye className="w-4 h-4 text-blue-400" />
                  </div>
                  <p className="text-xl font-bold text-white">
                    {formatNumber(youtubeStats.analytics?.totals.views || 0)}
                  </p>
                  <p className="text-xs text-zinc-500">Vues</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1 justify-center mb-1">
                    <Users className="w-4 h-4 text-green-400" />
                  </div>
                  <p className="text-xl font-bold text-green-400">
                    +{formatNumber(youtubeStats.analytics?.totals.subscribers_gained || 0)}
                  </p>
                  <p className="text-xs text-zinc-500">Abonnés</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center gap-1 justify-center mb-1">
                    <ThumbsUp className="w-4 h-4 text-violet-400" />
                  </div>
                  <p className="text-xl font-bold text-white">
                    {formatNumber(youtubeStats.analytics?.totals.likes || 0)}
                  </p>
                  <p className="text-xs text-zinc-500">Likes</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div className="card p-5">
          <div className="flex items-center gap-3 mb-2">
            <FolderKanban className="w-5 h-5 text-zinc-400" />
            <span className="text-sm text-zinc-400">Total</span>
          </div>
          <p className="text-3xl font-bold text-white">{stats?.total || 0}</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-3 mb-2">
            <Clock className="w-5 h-5 text-zinc-400" />
            <span className="text-sm text-zinc-400">En attente</span>
          </div>
          <p className="text-3xl font-bold text-zinc-400">{stats?.created || 0}</p>
        </div>

        <div className="card p-5 border-blue-500/20">
          <div className="flex items-center gap-3 mb-2">
            <PlayCircle className="w-5 h-5 text-blue-400" />
            <span className="text-sm text-zinc-400">En cours</span>
          </div>
          <p className="text-3xl font-bold text-blue-400">{stats?.processing || 0}</p>
        </div>

        <div className="card p-5 border-green-500/20">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-sm text-zinc-400">Terminés</span>
          </div>
          <p className="text-3xl font-bold text-green-400">{stats?.completed || 0}</p>
        </div>

        <div className="card p-5 border-red-500/20">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-sm text-zinc-400">Échoués</span>
          </div>
          <p className="text-3xl font-bold text-red-400">{stats?.failed || 0}</p>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="card">
        <div className="p-5 border-b border-white/5 flex items-center justify-between">
          <h2 className="font-semibold text-white">Projets récents</h2>
          <Link href="/projects" className="text-sm text-violet-400 hover:text-violet-300 transition">
            Voir tout →
          </Link>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500 mx-auto mb-3" />
            <p className="text-zinc-400 text-sm">Chargement...</p>
          </div>
        ) : recentProjects.length === 0 ? (
          <div className="p-12 text-center">
            <Sparkles className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400 mb-2">Aucun projet pour le moment</p>
            <p className="text-zinc-500 text-sm mb-4">Commencez par enregistrer une vidéo</p>
            <Link href="/record" className="btn-primary inline-flex items-center gap-2">
              <Video className="w-4 h-4" />
              Enregistrer
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {recentProjects.map((project) => (
              <Link 
                key={project._id} 
                href={`/projects`}
                className="flex items-center gap-4 p-4 hover:bg-white/[0.02] transition"
              >
                <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center">
                  {getStatusIcon(project.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-white truncate">{project.name}</p>
                  <p className="text-sm text-zinc-500 truncate">{project.folder_name}</p>
                </div>
                <div className="text-right">
                  <div className={`badge ${
                    project.status === 'completed' ? 'badge-success' :
                    project.status === 'processing' ? 'badge-info' :
                    project.status === 'failed' ? 'badge-error' :
                    'bg-zinc-800 text-zinc-400'
                  }`}>
                    {project.status === 'completed' ? 'Terminé' :
                     project.status === 'processing' ? 'En cours' :
                     project.status === 'failed' ? 'Échoué' : 'En attente'}
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">{formatDate(project.created_at)}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Pipeline Info */}
      <div className="mt-8 card p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center shrink-0">
            <TrendingUp className="w-6 h-6 text-violet-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white mb-1">Pipeline automatique</h3>
            <p className="text-sm text-zinc-400 mb-3">
              Chaque enregistrement passe par 12 étapes automatiques :
            </p>
            <div className="flex flex-wrap gap-2">
              {['Conversion', 'Fusion', 'Silences', 'Découpe', 'Transcription', 'Shorts', 'B-Roll', 'Intégration', 'SEO', 'Miniature', 'Programmation', 'Upload'].map((step, i) => (
                <span key={step} className="px-2.5 py-1 rounded-lg bg-zinc-800 text-xs text-zinc-400">
                  {i + 1}. {step}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
