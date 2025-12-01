'use client';

import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { Youtube, AlertCircle, ExternalLink, Loader2, CheckCircle } from 'lucide-react';

interface YouTubeAuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
}

const YouTubeAuthContext = createContext<YouTubeAuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  checkAuth: async () => {},
});

export const useYouTubeAuth = () => useContext(YouTubeAuthContext);

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

export function YouTubeAuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = async () => {
    try {
      const res = await fetch(`${API_URL}/api/youtube/status`);
      if (res.ok) {
        const data = await res.json();
        const isConnected = data.connected === true;
        console.log('[YouTube Auth] Status:', data, 'Connected:', isConnected);
        setIsAuthenticated(isConnected);
        setShowModal(!isConnected);
      } else {
        setIsAuthenticated(false);
        setShowModal(true);
      }
    } catch (err) {
      console.error('Erreur vérification YouTube:', err);
      setIsAuthenticated(false);
      setShowModal(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  // Vérifier si on revient de l'auth YouTube
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authStatus = urlParams.get('auth');
    
    if (authStatus === 'success') {
      console.log('[YouTube Auth] Auth success détecté, re-vérification...');
      // Re-vérifier le statut pour être sûr
      checkAuth();
      // Nettoyer l'URL
      window.history.replaceState({}, '', window.location.pathname);
    } else if (authStatus === 'error') {
      setError('Erreur lors de la connexion YouTube. Veuillez réessayer.');
      setIsLoading(false);
      // Nettoyer l'URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    
    try {
      const res = await fetch(`${API_URL}/api/youtube/auth/url`);
      if (res.ok) {
        const data = await res.json();
        // Rediriger vers Google OAuth
        window.location.href = data.auth_url;
      } else {
        const errorData = await res.json();
        setError(errorData.detail || 'Impossible de démarrer la connexion');
        setConnecting(false);
      }
    } catch (err) {
      setError('Erreur de connexion au serveur');
      setConnecting(false);
    }
  };

  // Modal de connexion obligatoire
  if (showModal && !isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
              <Youtube className="w-8 h-8 text-red-500" />
            </div>
          </div>
          
          <h2 className="text-2xl font-bold text-white text-center mb-2">
            Connexion YouTube requise
          </h2>
          
          <p className="text-zinc-400 text-center mb-6">
            Pour utiliser l'application, vous devez connecter votre compte YouTube.
            Cela permet de programmer et publier vos vidéos automatiquement.
          </p>
          
          {/* Erreur */}
          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
          
          {/* Fonctionnalités */}
          <div className="space-y-3 mb-6">
            <div className="flex items-center gap-3 text-sm text-zinc-300">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Publication automatique des vidéos</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-zinc-300">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Programmation des shorts</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-zinc-300">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Statistiques de votre chaîne</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-zinc-300">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span>Upload des miniatures</span>
            </div>
          </div>
          
          {/* Bouton de connexion */}
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="w-full py-3 bg-red-600 hover:bg-red-500 disabled:bg-zinc-700 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2"
          >
            {connecting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Redirection vers Google...
              </>
            ) : (
              <>
                <Youtube className="w-5 h-5" />
                Se connecter avec YouTube
              </>
            )}
          </button>
          
          {/* Note */}
          <p className="text-xs text-zinc-500 text-center mt-4">
            Nous ne stockons pas vos données personnelles.
            <br />
            Seul un token d'accès est utilisé pour publier vos vidéos.
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-violet-500 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Vérification de la connexion YouTube...</p>
        </div>
      </div>
    );
  }

  return (
    <YouTubeAuthContext.Provider value={{ isAuthenticated, isLoading, checkAuth }}>
      {children}
    </YouTubeAuthContext.Provider>
  );
}

