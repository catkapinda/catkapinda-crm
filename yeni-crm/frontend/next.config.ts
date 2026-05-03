import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: { bodySizeLimit: '2mb' },
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
    }
    // Render hostport format: "host:port" → http:// prefix gerekli
    const prefix = apiUrl.startsWith('http') ? '' : 'http://';
    return [{ source: '/api/:path*', destination: `${prefix}${apiUrl}/api/:path*` }];
  },
};

export default config;
