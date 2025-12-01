import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { YouTubeAuthProvider } from '@/components/YouTubeAuthModal';

export const metadata: Metadata = {
  title: 'VibeAcademy - YouTube Pipeline',
  description: 'Enregistrez, éditez et publiez vos vidéos YouTube automatiquement',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="font-sans antialiased bg-zinc-950">
        <YouTubeAuthProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-64">
              {children}
            </main>
          </div>
        </YouTubeAuthProvider>
      </body>
    </html>
  );
}
