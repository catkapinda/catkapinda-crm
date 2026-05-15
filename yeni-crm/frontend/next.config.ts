import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: { bodySizeLimit: '2mb' },
  },
  // /api/* için src/app/api/[...path]/route.ts catch-all proxy kullanılıyor.
  // Rewrites yerine Route Handler tercih edildi çünkü:
  //   - 'Connection: close' header'ı eklenerek keep-alive socket reuse engellenir.
  //   - Bağlantı hatası durumunda otomatik tek seferlik retry yapılır.
  // Bu sayede backend her redeploy'da frontend Node fetch keep-alive cache'i
  // stale olmuyor ve frontend restart gerekmiyor.
};

export default config;
