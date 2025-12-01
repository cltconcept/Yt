'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft,
  Download,
  Copy,
  Check,
  Music2,
  Smartphone,
  Loader2,
  ExternalLink,
  Clock,
  Hash,
  FolderOpen,
  RefreshCw
} from 'lucide-react';

interface ShortItem {
  project_id: string;
  project_name: string;
  folder_name: string;
  short_file: string;
  short_index: number;
  title: string;
  description: string;
  tags: string[];
  duration?: number;
  created_at: string;
  tiktok_published?: boolean;
  tiktok_published_at?: string;
}

export default function TikTokPage() {
  const [shorts, setShorts] = useState<ShortItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [hidePublished, setHidePublished] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';
  
  // Filtrer les shorts selon le filtre
  const filteredShorts = hidePublished 
    ? shorts.filter(s => !s.tiktok_published) 
    : shorts;

  const fetchShorts = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/tiktok/shorts`);
      if (res.ok) {
        const data = await res.json();
        setShorts(data.shorts || []);
      }
    } catch (err) {
      console.error('Erreur chargement shorts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShorts();
  }, []);

  const copyToClipboard = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const getVideoUrl = (folderName: string, shortFile: string) => {
    return `${API_URL}/output/${folderName}/shorts/${shortFile}`;
  };

  // Optimiser le texte pour TikTok (limite 2200 caractères, hashtags intégrés)
  const getTikTokCaption = (short: ShortItem) => {
    const hashtags = short.tags?.slice(0, 5).map(t => `#${t.replace(/\s+/g, '')}`).join(' ') || '';
    const desc = short.description?.substring(0, 150) || '';
    return `${short.title}\n\n${desc}\n\n${hashtags}`;
  };

  const copyAllForTikTok = (short: ShortItem) => {
    const caption = getTikTokCaption(short);
    copyToClipboard(caption, `all-${short.project_id}-${short.short_index}`);
  };

  const togglePublished = async (short: ShortItem) => {
    try {
      const res = await fetch(`${API_URL}/api/tiktok/shorts/mark-published`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_name: short.folder_name,
          short_index: short.short_index,
          published: !short.tiktok_published
        })
      });
      if (res.ok) {
        // Mettre à jour localement
        setShorts(prev => prev.map(s => 
          s.folder_name === short.folder_name && s.short_index === short.short_index
            ? { ...s, tiktok_published: !s.tiktok_published, tiktok_published_at: new Date().toISOString() }
            : s
        ));
      }
    } catch (err) {
      console.error('Erreur toggle published:', err);
    }
  };

  return (
    <div className="min-h-screen p-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/" className="p-2 hover:bg-zinc-800 rounded-lg transition">
          <ArrowLeft className="w-5 h-5 text-zinc-400" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 via-red-500 to-yellow-500 flex items-center justify-center">
              <Music2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">TikTok</h1>
              <p className="text-zinc-500 text-sm">Préparez vos shorts pour TikTok</p>
            </div>
          </div>
        </div>
        <button
          onClick={fetchShorts}
          disabled={loading}
          className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
        <a
          href="https://www.tiktok.com/upload"
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 hover:opacity-90 text-white font-medium rounded-lg transition flex items-center gap-2"
        >
          <ExternalLink className="w-4 h-4" />
          Ouvrir TikTok Studio
        </a>
      </div>

      {/* Instructions */}
      <div className="card p-4 mb-6 border-pink-500/20">
        <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-pink-500" />
          Comment publier sur TikTok
        </h3>
        <ol className="text-sm text-zinc-400 space-y-1 list-decimal list-inside">
          <li>Téléchargez le short en cliquant sur le bouton <strong className="text-white">Télécharger</strong></li>
          <li>Cliquez sur <strong className="text-white">Copier pour TikTok</strong> pour copier titre + description + hashtags</li>
          <li>Ouvrez <strong className="text-white">TikTok Studio</strong> et uploadez la vidéo</li>
          <li>Collez la description copiée et publiez !</li>
        </ol>
      </div>

      {/* Filtre publiés */}
      {shorts.length > 0 && (
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setHidePublished(!hidePublished)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              hidePublished 
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' 
                : 'bg-zinc-800 text-zinc-400'
            }`}
          >
            {hidePublished ? (
              <>
                <Check className="w-4 h-4" />
                Publiés cachés ({shorts.filter(s => s.tiktok_published).length})
              </>
            ) : (
              'Afficher tout'
            )}
          </button>
          <span className="text-sm text-zinc-500">
            {filteredShorts.length} short{filteredShorts.length > 1 ? 's' : ''} affiché{filteredShorts.length > 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Shorts Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-pink-500" />
        </div>
      ) : shorts.length === 0 ? (
        <div className="card p-12 text-center">
          <Smartphone className="w-16 h-16 text-zinc-600 mx-auto mb-4" />
          <p className="text-zinc-400 text-lg mb-2">Aucun short disponible</p>
          <p className="text-zinc-500 text-sm">
            Les shorts seront générés automatiquement après le traitement de vos vidéos.
          </p>
          <Link href="/projects" className="inline-block mt-4 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition">
            Voir mes projets
          </Link>
        </div>
      ) : filteredShorts.length === 0 ? (
        <div className="card p-12 text-center">
          <Check className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <p className="text-zinc-400 text-lg mb-2">Tous les shorts sont publiés ! 🎉</p>
          <button 
            onClick={() => setHidePublished(false)}
            className="mt-4 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition"
          >
            Voir les shorts publiés
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredShorts.map((short, idx) => (
            <div key={`${short.project_id}-${short.short_index}`} className="card overflow-hidden group">
              {/* Video Preview */}
              <div className="relative bg-black" style={{ paddingTop: '177.78%' }}>
                <video
                  src={getVideoUrl(short.folder_name, short.short_file)}
                  controls
                  className="absolute inset-0 w-full h-full object-contain"
                  poster=""
                />
                {/* Status Badge */}
                <div className={`absolute top-2 right-2 px-2 py-1 rounded-full flex items-center gap-1 ${
                  short.tiktok_published 
                    ? 'bg-green-500/80' 
                    : 'bg-black/70'
                }`}>
                  {short.tiktok_published ? (
                    <>
                      <Check className="w-3 h-3 text-white" />
                      <span className="text-xs text-white">Publié</span>
                    </>
                  ) : (
                    <>
                      <Music2 className="w-3 h-3 text-pink-500" />
                      <span className="text-xs text-white">À publier</span>
                    </>
                  )}
                </div>
              </div>

              {/* Info */}
              <div className="p-4 space-y-3">
                {/* Project info */}
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <FolderOpen className="w-3 h-3" />
                  <span className="truncate">{short.project_name}</span>
                  <span>•</span>
                  <span>Short {short.short_index + 1}</span>
                </div>

                {/* Title */}
                <h3 className="font-medium text-white line-clamp-2 text-sm">
                  {short.title || `Short ${short.short_index + 1}`}
                </h3>

                {/* Tags */}
                {short.tags && short.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {short.tags.slice(0, 4).map((tag, i) => (
                      <span key={i} className="text-xs bg-pink-500/10 text-pink-400 px-2 py-0.5 rounded-full">
                        #{tag}
                      </span>
                    ))}
                    {short.tags.length > 4 && (
                      <span className="text-xs text-zinc-500">+{short.tags.length - 4}</span>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-2 pt-2">
                  <div className="flex gap-2">
                    <a
                      href={getVideoUrl(short.folder_name, short.short_file)}
                      download={`tiktok_${short.folder_name}_short${short.short_index + 1}.mp4`}
                      className="flex-1 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium rounded-lg transition flex items-center justify-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      Télécharger
                    </a>
                    <button
                      onClick={() => copyAllForTikTok(short)}
                      className="flex-1 py-2 bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 hover:opacity-90 text-white text-sm font-medium rounded-lg transition flex items-center justify-center gap-2"
                    >
                      {copiedField === `all-${short.project_id}-${short.short_index}` ? (
                        <>
                          <Check className="w-4 h-4" />
                          Copié !
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copier
                        </>
                      )}
                    </button>
                  </div>
                  {/* Bouton marquer comme publié */}
                  <button
                    onClick={() => togglePublished(short)}
                    className={`w-full py-2 text-sm font-medium rounded-lg transition flex items-center justify-center gap-2 ${
                      short.tiktok_published
                        ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white'
                    }`}
                  >
                    <Check className="w-4 h-4" />
                    {short.tiktok_published ? 'Publié sur TikTok ✓' : 'Marquer comme publié'}
                  </button>
                </div>

                {/* Preview Caption */}
                <details className="text-xs">
                  <summary className="text-zinc-500 cursor-pointer hover:text-zinc-400">
                    Voir la description complète
                  </summary>
                  <div className="mt-2 p-2 bg-zinc-900 rounded-lg text-zinc-400 whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {getTikTokCaption(short)}
                  </div>
                </details>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {shorts.length > 0 && (
        <div className="mt-8 card p-4 flex items-center justify-between">
          <div className="text-sm text-zinc-400 flex items-center gap-4">
            <span>
              <span className="text-white font-semibold">{shorts.length}</span> shorts disponibles
            </span>
            <span className="text-green-400">
              <Check className="w-4 h-4 inline mr-1" />
              {shorts.filter(s => s.tiktok_published).length} publiés
            </span>
            <span className="text-amber-400">
              {shorts.filter(s => !s.tiktok_published).length} à publier
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <Clock className="w-4 h-4" />
            Format : 9:16 vertical, &lt; 3 min
          </div>
        </div>
      )}
    </div>
  );
}

