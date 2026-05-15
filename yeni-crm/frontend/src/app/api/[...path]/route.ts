/**
 * /api/* için catch-all proxy Route Handler.
 *
 * NEDEN BU DOSYA?
 * Next.js rewrites (next.config.ts) backend'e proxy yaparken Node'un default
 * fetch dispatcher'ını kullanır → keep-alive socket havuzu vardır. Backend
 * yeniden deploy edilince eski socket'ler stale olur ve frontend'den gelen
 * her istek 500 ile patlar. Çözüm: her istekte 'Connection: close' header'ı
 * göndererek socket reuse'u devre dışı bırakmak + tek seferlik retry.
 *
 * Bu Route Handler app router'da rewrites'ın önüne geçer; /api/* trafiği
 * artık bu dosyadan geçer.
 */
import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BACKEND = (() => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return 'http://localhost:8000';
  return apiUrl.startsWith('http') ? apiUrl : `http://${apiUrl}`;
})();

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = req.nextUrl.search ?? '';
  const url = `${BACKEND}/api/${path.join('/')}${search}`;

  // İsteğin body'sini bir kez oku (retry için tekrar gerekli)
  const hasBody = req.method !== 'GET' && req.method !== 'HEAD';
  const bodyBuf = hasBody ? await req.arrayBuffer() : undefined;

  // Backend'e ileteceğimiz header'lar (host/origin'i kaldır, Connection: close ekle)
  const headers = new Headers();
  req.headers.forEach((v, k) => {
    const kl = k.toLowerCase();
    if (kl === 'host' || kl === 'connection' || kl === 'content-length') return;
    headers.set(k, v);
  });
  headers.set('Connection', 'close');

  async function attempt(): Promise<Response> {
    return fetch(url, {
      method: req.method,
      headers,
      body: bodyBuf,
      cache: 'no-store',
      // @ts-expect-error — undici-specific option, Next.js routes runtime'da geçerli
      duplex: 'half',
    });
  }

  let upstream: Response;
  try {
    upstream = await attempt();
  } catch {
    // Bağlantı seviyesinde hata (stale keep-alive socket vs.) → tek seferlik retry
    await new Promise((r) => setTimeout(r, 200));
    upstream = await attempt();
  }

  // Backend response'unu olduğu gibi clone'la döndür
  const respHeaders = new Headers();
  upstream.headers.forEach((v, k) => {
    const kl = k.toLowerCase();
    if (kl === 'content-encoding' || kl === 'transfer-encoding') return;
    respHeaders.set(k, v);
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
