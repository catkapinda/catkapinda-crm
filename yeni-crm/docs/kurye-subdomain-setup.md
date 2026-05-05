# `kurye.crmcatkapinda.com` Subdomain Kurulumu

Hedef: Kuryelerin doğrudan `https://kurye.crmcatkapinda.com` ile giriş yapabilmesi.
Şu an `crmcatkapinda-v3.onrender.com/kurye` üzerinden çalışıyor.

İki adım var: **Render**'da custom domain ekle, **GoDaddy**'de DNS kaydı oluştur.

---

## Adım 1 — Render Dashboard

1. https://dashboard.render.com aç → giriş yap
2. Sol menüden frontend servisi seç: **`crmcatkapinda-v3`**
3. Üst menüde **Settings** sekmesine geç
4. Sol kolonda **Custom Domain** veya **Custom Domains** bölümünü bul
5. **Add Custom Domain** tıkla
6. Domain alanına şunu gir: `kurye.crmcatkapinda.com`
7. **Save** tıkla
8. Render sana bir **CNAME hedefi** verir, örneğin:
   ```
   crmcatkapinda-v3.onrender.com
   ```
   Bu adresi kopyala — DNS adımında lazım olacak.
9. Sayfada bu domain için "**Verification: Pending**" yazacak. DNS kaydını ekledikten sonra Render otomatik doğrulayıp Let's Encrypt SSL sertifikası kuracak (5–30 dk).

---

## Adım 2 — GoDaddy DNS

1. https://dcc.godaddy.com/domains/ aç → giriş yap
2. **catkapinda.com** domain'ini bul → yanındaki **DNS** butonuna tıkla
3. **DNS Records** sayfasında **Add New Record** veya **Add** butonuna tıkla
4. Şu kaydı ekle:

   | Alan | Değer |
   |---|---|
   | **Type** | `CNAME` |
   | **Name** | `kurye` |
   | **Value** | `crmcatkapinda-v3.onrender.com` |
   | **TTL** | `1 Hour` (veya **Custom: 600**) |

5. **Save** tıkla
6. Aynı sayfada başka kayıt yoksa GoDaddy bazen otomatik bir _parking_ A kaydı eklemiş olabilir — `kurye` adında varsa onu sil ki sadece CNAME kalsın.

DNS yayılımı genelde 5–30 dakika sürer. Bazen 2 saat uzayabilir.

---

## Adım 3 — Doğrulama

DNS yayıldıktan sonra:

1. **Tarayıcıda** `https://kurye.crmcatkapinda.com` aç
2. Çalışıyor olmalı — kurye giriş ekranı açılmalı (telefon numarası inputu)
3. Render dashboard'da custom domain durumu **Verified · Active** olmalı
4. SSL sertifikası otomatik kurulu — adres çubuğunda kilit ikonu görünür

---

## Adım 4 — Frontend kök yönlendirmesi (opsiyonel iyileştirme)

Şu an `kurye.crmcatkapinda.com` açıldığında ana ekran `/` olur (admin login sayfası).
Kurye için `/kurye` olarak gelmesi daha güzel.

İki seçenek:

**A) Next.js middleware ile** (önerilen, kod tarafı):

`yeni-crm/frontend/src/middleware.ts` dosyası oluştur:

```ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(req: NextRequest) {
  const host = req.headers.get('host') ?? '';
  if (host.startsWith('kurye.')) {
    const url = req.nextUrl.clone();
    // Zaten /kurye altındaysa dokunma
    if (!url.pathname.startsWith('/kurye') && !url.pathname.startsWith('/api') &&
        !url.pathname.startsWith('/_next')) {
      url.pathname = '/kurye' + url.pathname;
      return NextResponse.rewrite(url);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|api).*)'],
};
```

Bu sayede:
- `kurye.crmcatkapinda.com/` → `/kurye` (login sayfası)
- `kurye.crmcatkapinda.com/dashboard` → `/kurye/dashboard`
- vb.

**B) Render rewrite kuralı ile** (panelden):

Render frontend service'inde **Settings → Redirects/Rewrites** ekle:
- Source: `*`
- Destination: `/kurye/*`
- Type: Rewrite
- Conditions: `Host header equals kurye.crmcatkapinda.com`

---

## Sorun giderme

**"DNS_PROBE_FINISHED_NXDOMAIN"** → DNS henüz yayılmamış, 30 dk bekle, DNS Checker ile kontrol et:
```
https://dnschecker.org/#CNAME/kurye.crmcatkapinda.com
```

**Render: "Domain Not Verified"** → CNAME yanlış girilmiş veya GoDaddy'de eski kayıt var. GoDaddy'de `kurye` ile başlayan tüm kayıtları gör, sadece CNAME kalmalı.

**SSL hatası "NET::ERR_CERT_AUTHORITY_INVALID"** → Render hâlâ Let's Encrypt sertifikası kuruyor. 30 dk bekle, sayfa yenile.

**Sonsuz redirect** → middleware kuralı çift sayım yapıyor. `req.nextUrl.pathname.startsWith('/kurye')` kontrolünün doğru çalıştığından emin ol.

---

## Sıralama özeti (3 dakikalık iş)

1. Render dashboard → Custom Domain ekle (`kurye.crmcatkapinda.com`)
2. GoDaddy DNS → CNAME ekle (`kurye` → `crmcatkapinda-v3.onrender.com`)
3. 30 dk bekle, `https://kurye.crmcatkapinda.com` aç → çalışıyor mu kontrol
4. (Opsiyonel) middleware ekle, push et

Hata yaşarsan ekran görüntüsünü gönder, birlikte hallederiz.
