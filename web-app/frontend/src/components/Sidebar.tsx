'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Home,
  Video,
  FolderKanban,
  Settings,
  Sparkles,
  MonitorPlay,
  ExternalLink,
  Youtube,
  Instagram
} from 'lucide-react';

// Icône TikTok personnalisée
const TikTokIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z"/>
  </svg>
);

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Enregistrer', href: '/record', icon: Video },
  { name: 'Projets', href: '/projects', icon: FolderKanban },
  { name: 'YouTube', href: '/youtube', icon: Youtube },
  { name: 'TikTok', href: '/tiktok', icon: TikTokIcon },
  { name: 'Instagram', href: '/instagram', icon: Instagram },
  { name: 'Paramètres', href: '/settings', icon: Settings },
];

const externalLinks = [
  { name: 'Flower', href: 'http://localhost:5555', color: 'text-orange-400' },
  { name: 'MongoDB', href: 'http://localhost:8081', color: 'text-green-400' },
  { name: 'MinIO', href: 'http://localhost:9001', color: 'text-red-400' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-zinc-950 border-r border-white/5 flex flex-col fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="p-6 border-b border-white/5">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-white">VibeAcademy</h1>
            <p className="text-xs text-zinc-500">YouTube Pipeline</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="px-3 py-2 text-xs font-medium text-zinc-500 uppercase tracking-wider">
          Menu
        </p>
        {navigation.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'active bg-white/5 text-white'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon className="w-5 h-5" />
              {item.name}
            </Link>
          );
        })}

        {/* External Links */}
        <div className="pt-6">
          <p className="px-3 py-2 text-xs font-medium text-zinc-500 uppercase tracking-wider">
            Services
          </p>
          {externalLinks.map((item) => (
            <a
              key={item.name}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-zinc-400 hover:text-white hover:bg-white/5`}
            >
              <ExternalLink className={`w-4 h-4 ${item.color}`} />
              {item.name}
            </a>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <div className="card p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500/20 to-cyan-500/20 flex items-center justify-center">
              <MonitorPlay className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">v2.0</p>
              <p className="text-xs text-zinc-500">Pipeline actif</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-zinc-400">Services connectés</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

