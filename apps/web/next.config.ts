import type { NextConfig } from 'next';

const rawApiUrl =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000'
    : 'https://gate-ds9h.onrender.com');

// Guard against self-referencing rewrites in production if API_URL points back to fabgate.vercel.app
const apiUrl =
  rawApiUrl.includes('fabgate.vercel.app') || rawApiUrl.includes('vercel.app')
    ? 'https://gate-ds9h.onrender.com'
    : rawApiUrl;

const nextConfig: NextConfig = {
  transpilePackages: ['@examshield/ui', '@examshield/utils', '@examshield/types'],
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'img.clerk.com' },
      { protocol: 'https', hostname: '*.supabase.co' },
      { protocol: 'https', hostname: '*.vercel-storage.com' },
    ],
  },
  experimental: {
    serverActions: {
      bodySizeLimit: '4mb',
    },
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(self), microphone=(self), fullscreen=(self)',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
