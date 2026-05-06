/**
 * Next.js middleware — kurye.crmcatkapinda.com subdomain'inden gelen
 * istekleri /kurye altına yönlendir.
 *
 * Kuruluş:
 * - GoDaddy'de CNAME kurye → crmcatkapinda-v3.onrender.com
 * - Render'da custom domain: kurye.crmcatkapinda.com
 *
 * Bu middleware host header'ında 'kurye.' ile başlayan tüm istekler için path
 * başına /kurye ekler (rewrite — URL değişmez, sunucu içinde yönlendirilir).
 * 'kurye.' prefix kontrolü domain-bağımsız çalışır; üretim domain'i
 * crmcatkapinda.com da olsa catkapinda.com da olsa fark etmez.
 */
import { NextRequest, NextResponse } from 'next/server';

// public/ altındaki statik dosyaların uzantıları — bunları /kurye'ye rewrite etme
// (örn. /catkapinda-logo.png → 404 olmasın diye)
const STATIC_ASSET_RE =
  /\.(?:png|jpg|jpeg|gif|webp|svg|ico|txt|xml|json|css|js|map|woff|woff2|ttf|eot)$/i;

export function middleware(req: NextRequest) {
  const host = req.headers.get('host') ?? '';
  const url = req.nextUrl;

  // Sadece kurye. subdomain'inden gelenler için
  if (host.startsWith('kurye.')) {
    // Zaten /kurye altındaysa, /api / _next ise veya statik asset ise dokunma
    if (
      !url.pathname.startsWith('/kurye') &&
      !url.pathname.startsWith('/api') &&
      !url.pathname.startsWith('/_next') &&
      !STATIC_ASSET_RE.test(url.pathname)
    ) {
      const newUrl = url.clone();
      newUrl.pathname = '/kurye' + (url.pathname === '/' ? '' : url.pathname);
      return NextResponse.rewrite(newUrl);
    }
  }
  return NextResponse.next();
}

export const config = {
  // _next ve api hariç tüm yollar
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
