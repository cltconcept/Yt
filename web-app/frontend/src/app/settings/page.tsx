'use client';

import { useState, useEffect } from 'react';
import { 
  Key, 
  Save, 
  Eye, 
  EyeOff, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  Sparkles,
  Database,
  Server
} from 'lucide-react';

interface ApiKey {
  name: string;
  masked_value: string;
  description: string;
  has_value: boolean;
  updated_at: string | null;
}

const API_KEY_INFO: Record<string, { label: string; description: string; placeholder: string }> = {
  OPENROUTER_API_KEY: {
    label: 'OpenRouter',
    description: 'Pour GPT-4, Claude, Gemini (transcription, SEO, miniatures)',
    placeholder: 'sk-or-...',
  },
  GROQ_API_KEY: {
    label: 'Groq',
    description: 'Pour Whisper (transcription audio rapide)',
    placeholder: 'gsk_...',
  },
  PEXELS_API_KEY: {
    label: 'Pexels',
    description: 'Pour les clips B-roll (vidéos stock gratuites)',
    placeholder: 'Votre clé Pexels',
  },
  YOUTUBE_API_KEY: {
    label: 'YouTube',
    description: 'Pour l\'upload automatique sur YouTube',
    placeholder: 'AIza...',
  },
};

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010';

  const fetchApiKeys = async () => {
    try {
      const res = await fetch(`${API_URL}/api/settings/keys`);
      if (!res.ok) throw new Error('Erreur chargement');
      const data = await res.json();
      setApiKeys(data);
    } catch (err) {
      console.error('Erreur:', err);
      setMessage({ type: 'error', text: 'Erreur de connexion à la base de données' });
    } finally {
      setLoading(false);
    }
  };

  const initApiKeys = async () => {
    try {
      await fetch(`${API_URL}/api/settings/keys/init`, { method: 'POST' });
      fetchApiKeys();
    } catch (err) {
      console.error('Erreur init:', err);
    }
  };

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const saveApiKey = async (keyName: string) => {
    const value = editValues[keyName];
    if (!value) return;

    setSaving(keyName);
    setMessage(null);

    try {
      const res = await fetch(`${API_URL}/api/settings/keys/${keyName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          value, 
          description: API_KEY_INFO[keyName]?.description || '' 
        }),
      });

      if (!res.ok) throw new Error('Erreur sauvegarde');

      setMessage({ type: 'success', text: `Clé ${API_KEY_INFO[keyName]?.label || keyName} sauvegardée` });
      setEditValues(prev => ({ ...prev, [keyName]: '' }));
      fetchApiKeys();
    } catch (err) {
      setMessage({ type: 'error', text: 'Erreur lors de la sauvegarde' });
    } finally {
      setSaving(null);
    }
  };

  const getKeyStatus = (key: ApiKey) => {
    if (key.has_value) {
      return { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10' };
    }
    return { icon: AlertCircle, color: 'text-zinc-500', bg: 'bg-zinc-800' };
  };

  return (
    <div className="min-h-screen p-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Paramètres</h1>
        <p className="text-zinc-400">Configurez vos clés API et préférences</p>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-xl flex items-center gap-3 ${
          message.type === 'success' 
            ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Status Card */}
      <div className="card p-6 mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center">
              <Database className="w-6 h-6 text-violet-400" />
            </div>
            <div>
              <h2 className="font-semibold text-white">Base de données</h2>
              <p className="text-sm text-zinc-400">Les clés sont stockées dans MongoDB</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-sm text-zinc-400">Connecté</span>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Key className="w-5 h-5 text-violet-400" />
          Clés API
        </h2>
        <button 
          onClick={initApiKeys}
          className="btn-secondary text-sm py-1.5 flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Réinitialiser
        </button>
      </div>

      {loading ? (
        <div className="card p-12 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500 mx-auto mb-3" />
          <p className="text-zinc-400">Chargement...</p>
        </div>
      ) : apiKeys.length === 0 ? (
        <div className="card p-12 text-center">
          <Key className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <p className="text-zinc-400 mb-4">Aucune clé API configurée</p>
          <button onClick={initApiKeys} className="btn-primary">
            Initialiser les clés
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {apiKeys.map((key) => {
            const info = API_KEY_INFO[key.name] || { label: key.name, description: '', placeholder: '' };
            const status = getKeyStatus(key);
            const StatusIcon = status.icon;

            return (
              <div key={key.name} className="card p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg ${status.bg} flex items-center justify-center`}>
                      <StatusIcon className={`w-5 h-5 ${status.color}`} />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{info.label}</h3>
                      <p className="text-sm text-zinc-500">{info.description}</p>
                    </div>
                  </div>
                  {key.has_value && (
                    <span className="badge badge-success">Configurée</span>
                  )}
                </div>

                {key.has_value && (
                  <div className="mb-4 p-3 bg-zinc-900 rounded-lg">
                    <div className="flex items-center justify-between">
                      <code className="text-sm text-zinc-400 font-mono">
                        {showValues[key.name] ? key.masked_value : '••••••••••••••••'}
                      </code>
                      <button
                        onClick={() => setShowValues(prev => ({ ...prev, [key.name]: !prev[key.name] }))}
                        className="p-1.5 text-zinc-500 hover:text-white transition"
                      >
                        {showValues[key.name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex gap-3">
                  <input
                    type="password"
                    placeholder={key.has_value ? 'Nouvelle valeur...' : info.placeholder}
                    value={editValues[key.name] || ''}
                    onChange={(e) => setEditValues(prev => ({ ...prev, [key.name]: e.target.value }))}
                    className="input flex-1"
                  />
                  <button
                    onClick={() => saveApiKey(key.name)}
                    disabled={!editValues[key.name] || saving === key.name}
                    className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving === key.name ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Sauvegarder
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Info */}
      <div className="mt-8 card p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="font-medium text-white mb-1">Obtenir les clés API</h3>
            <ul className="text-sm text-zinc-400 space-y-1">
              <li>• <strong>OpenRouter:</strong> <a href="https://openrouter.ai/keys" target="_blank" className="text-violet-400 hover:underline">openrouter.ai/keys</a></li>
              <li>• <strong>Groq:</strong> <a href="https://console.groq.com/keys" target="_blank" className="text-violet-400 hover:underline">console.groq.com/keys</a></li>
              <li>• <strong>Pexels:</strong> <a href="https://www.pexels.com/api/new/" target="_blank" className="text-violet-400 hover:underline">pexels.com/api</a></li>
              <li>• <strong>YouTube:</strong> <a href="https://console.cloud.google.com/apis/credentials" target="_blank" className="text-violet-400 hover:underline">Google Cloud Console</a></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
