/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // En dev local, utiliser localhost:8000
    // En production Docker, utiliser backend:8000
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/output/:path*',
        destination: `${backendUrl}/output/:path*`,
      },
    ];
  },
  // Désactiver le cache pour les vidéos
  async headers() {
    return [
      {
        source: '/output/:path*.mp4',
        headers: [
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Pragma', value: 'no-cache' },
          { key: 'Expires', value: '0' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;

