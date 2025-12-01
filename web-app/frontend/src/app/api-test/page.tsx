'use client';

import { useState } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Loader2, 
  RefreshCw,
  Key,
  Video,
  Mic,
  Brain,
  Image,
  Monitor,
  FolderOpen,
  Settings
} from 'lucide-react';
import Link from 'next/link';

interface ApiStatus {
  name: string;
  status: 'idle' | 'loading' | 'success' | 'error';
  message: string;
  details?: string;
  icon: React.ReactNode;
  color: string;
}

export default function ApiTestPage() {
  const [apis, setApis] = useState<ApiStatus[]>([
    { name: 'Groq (Transcription)', status: 'idle', message: 'Non testé', icon: <Mic className="w-5 h-5" />, color: 'orange' },
    { name: 'OpenRouter (IA/SEO)', status: 'idle', message: 'Non testé', icon: <Brain className="w-5 h-5" />, color: 'purple' },
    { name: 'Pexels (Clips vidéo)', status: 'idle', message: 'Non testé', icon: <Video className="w-5 h-5" />, color: 'green' },
    { name: 'Unsplash (Images)', status: 'idle', message: 'Non testé', icon: <Image className="w-5 h-5" />, color: 'pink' },
    { name: 'FFmpeg', status: 'idle', message: 'Non testé', icon: <Video className="w-5 h-5" />, color: 'blue' },
    { name: 'Backend API', status: 'idle', message: 'Non testé', icon: <Key className="w-5 h-5" />, color: 'cyan' },
  ]);

  const [testing, setTesting] = useState(false);

  const updateApi = (index: number, updates: Partial<ApiStatus>) => {
    setApis(prev => prev.map((api, i) => i === index ? { ...api, ...updates } : api));
  };

  const testAllApis = async () => {
    setTesting(true);
    
    // Reset all
    setApis(prev => prev.map(api => ({ ...api, status: 'loading', message: 'Test en cours...' })));

    // Test Backend
    try {
      const res = await fetch('/api/test-apis');
      const data = await res.json();
      
      // Groq
      if (data.groq) {
        updateApi(0, {
          status: data.groq.status ? 'success' : 'error',
          message: data.groq.status ? 'Connecté' : 'Non configuré',
          details: data.groq.details
        });
      }
      
      // OpenRouter
      if (data.openrouter) {
        updateApi(1, {
          status: data.openrouter.status ? 'success' : 'error',
          message: data.openrouter.status ? 'Connecté' : 'Non configuré',
          details: data.openrouter.details
        });
      }
      
      // Pexels
      if (data.pexels) {
        updateApi(2, {
          status: data.pexels.status ? 'success' : 'error',
          message: data.pexels.status ? 'Connecté' : 'Non configuré',
          details: data.pexels.details
        });
      }
      
      // Unsplash
      if (data.unsplash) {
        updateApi(3, {
          status: data.unsplash.status ? 'success' : 'error',
          message: data.unsplash.status ? 'Connecté' : 'Non configuré',
          details: data.unsplash.details
        });
      }
      
      // FFmpeg
      if (data.ffmpeg) {
        updateApi(4, {
          status: data.ffmpeg.status ? 'success' : 'error',
          message: data.ffmpeg.status ? 'Installé' : 'Non trouvé',
          details: data.ffmpeg.details
        });
      }
      
      // Backend
      updateApi(5, {
        status: 'success',
        message: 'En ligne',
        details: `Port 8000`
      });
      
    } catch (err) {
      // Backend offline
      updateApi(5, {
        status: 'error',
        message: 'Hors ligne',
        details: 'Impossible de contacter le backend'
      });
      
      // Mark others as unknown
      [0, 1, 2, 3, 4].forEach(i => {
        updateApi(i, {
          status: 'error',
          message: 'Backend requis',
          details: 'Démarrez le backend pour tester'
        });
      });
    }
    
    setTesting(false);
  };

  const getStatusColor = (status: ApiStatus['status']) => {
    switch (status) {
      case 'success': return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'error': return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'loading': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
    }
  };

  const getStatusIcon = (status: ApiStatus['status']) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error': return <XCircle className="w-5 h-5 text-red-400" />;
      case 'loading': return <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />;
      default: return <div className="w-5 h-5 rounded-full bg-gray-600" />;
    }
  };

  return (
    <main className="h-screen flex flex-col overflow-hidden bg-transparent">
      {/* Header */}
      <header className="glass border-b border-white/10 shrink-0 z-10">
        <div className="px-3 md:px-6 py-2 md:py-3">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 md:gap-3">
              <div className="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg md:rounded-xl flex items-center justify-center">
                <Video className="w-4 h-4 md:w-5 md:h-5 text-white" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-base md:text-xl font-bold text-white">YouTube Pipeline</h1>
                <p className="text-[10px] md:text-xs text-dark-400">Enregistrement & Traitement</p>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-1 md:gap-2">
              <Link
                href="/"
                className="flex items-center gap-1.5 md:gap-2 px-2 md:px-4 py-1.5 md:py-2 rounded-lg text-sm font-medium transition-all text-dark-400 hover:text-white hover:bg-white/5"
              >
                <Monitor className="w-4 h-4" />
                <span className="hidden md:inline">Enregistrer</span>
              </Link>
              <Link
                href="/"
                className="flex items-center gap-1.5 md:gap-2 px-2 md:px-4 py-1.5 md:py-2 rounded-lg text-sm font-medium transition-all text-dark-400 hover:text-white hover:bg-white/5"
              >
                <FolderOpen className="w-4 h-4" />
                <span className="hidden md:inline">Fichiers</span>
              </Link>
              
              <Link
                href="/api-test"
                className="flex items-center gap-1.5 md:gap-2 px-2 md:px-4 py-1.5 md:py-2 rounded-lg text-sm font-medium transition-all bg-primary-600 text-white"
              >
                <Settings className="w-4 h-4" />
                <span className="hidden md:inline">API</span>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-2xl mx-auto">
          {/* Title */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white">Test des APIs</h2>
            <p className="text-gray-400 text-sm">Vérifiez la configuration de vos services</p>
          </div>

          {/* Test Button */}
          <button
            onClick={testAllApis}
            disabled={testing}
            className="w-full mb-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-gray-600 disabled:to-gray-600 text-white font-semibold rounded-xl flex items-center justify-center gap-3 transition-all"
          >
            {testing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Test en cours...
              </>
            ) : (
              <>
                <RefreshCw className="w-5 h-5" />
                Tester toutes les APIs
              </>
            )}
          </button>

          {/* API List */}
          <div className="space-y-3">
            {apis.map((api, index) => (
              <div
                key={api.name}
                className={`p-4 rounded-xl border ${getStatusColor(api.status)} transition-all`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-${api.color}-500/20`}>
                      {api.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{api.name}</h3>
                      <p className="text-sm opacity-80">{api.message}</p>
                      {api.details && (
                        <p className="text-xs opacity-60 mt-1">{api.details}</p>
                      )}
                    </div>
                  </div>
                  {getStatusIcon(api.status)}
                </div>
              </div>
            ))}
          </div>

          {/* Help Section */}
          <div className="mt-8 p-4 rounded-xl bg-white/5 border border-white/10">
            <h3 className="font-semibold text-white mb-3">📝 Configuration requise</h3>
            <div className="space-y-2 text-sm text-gray-400">
              <p><span className="text-orange-400">Groq:</span> GROQ_API_KEY dans .env (gratuit sur console.groq.com)</p>
              <p><span className="text-purple-400">OpenRouter:</span> OPENROUTER_API_KEY dans .env (openrouter.ai)</p>
              <p><span className="text-green-400">Pexels:</span> PEXELS_API_KEY dans .env (pexels.com/api)</p>
              <p><span className="text-pink-400">Unsplash:</span> UNSPLASH_ACCESS_KEY dans .env (unsplash.com/developers)</p>
              <p><span className="text-blue-400">FFmpeg:</span> Dossier ffmpeg/ à la racine du projet</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
