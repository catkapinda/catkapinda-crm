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

const STATIC_ASSET_RE =
  /\.(?:png|jpg|jpeg|gif|webp|svg|ico|txt|xml|json|css|js|map|woff|woff2|ttf|eot)$/i;

// Auth gerektirmeyen path'ler
const PUBLIC_PATHS = ['/login', '/sifre-sifirla'];

export function middleware(req: NextRequest) {
  const host = req.headers.get('host') ?? '';
  const url = req.nextUrl;
  const { pathname } = url;

  // 1) kurye. subdomain rewrite (önceki davranış)
  if (host.startsWith('kurye.')) {
    if (
      !pathname.startsWith('/kurye') &&
      !pathname.startsWith('/api') &&
      !pathname.startsWith('/_next') &&
      !STATIC_ASSET_RE.test(pathname)
    ) {
      const newUrl = url.clone();
      newUrl.pathname = '/kurye' + (pathname === '/' ? '' : pathname);
      return NextResponse.rewrite(newUrl);
    }
    // Kurye subdomain'i kendi auth akışına sahip — middleware orada koruma yok
    return NextResponse.next();
  }

  // 2) CRM auth gating
  // /api / _next / static asset — dokunma
  if (
    pathname.startsWith('/api') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/kurye') ||
    STATIC_ASSET_RE.test(pathname)
  ) {
    return NextResponse.next();
  }

  const token = req.cookies.get('ck_auth')?.value;
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  if (!token && !isPublic) {
    const redirectUrl = url.clone();
    redirectUrl.pathname = '/login';
    redirectUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(redirectUrl);
  }

  if (token && pathname === '/login') {
    const homeUrl = url.clone();
    homeUrl.pathname = '/';
    homeUrl.search = '';
    return NextResponse.redirect(homeUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
