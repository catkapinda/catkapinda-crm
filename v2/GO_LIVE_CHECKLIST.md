# Cat Kapinda CRM v2 Go-Live Checklist

Bu dosya, `PILOT_DEPLOY.md` icindeki uzun runbook'un kisa operasyon karsiligidir.
Deploy gununde once bu listeye bakilir.

## 1. Su An Kalan Gercek Blokajlar

- `CK_V2_DATABASE_URL`
- `CK_V2_DEFAULT_AUTH_PASSWORD`
- Render servislerine gercek env girisleri
- `crmcatkapinda.com` domain ve cutover adimi

Kod tarafinda ana omurga hazir; bu maddeler kapanmadan pilot acilmaz.

## 2. Streamlit Verisi Buraya Nasil Gelir

Tercih edilen yol:

- v2 backend'i Streamlit'in kullandigi ayni PostgreSQL veritabanina bagla
- `CK_V2_DATABASE_URL` olarak mevcut canli PostgreSQL baglantisini kullan

Alternatif yol:

- Elinde yalnizca SQLite veya tekil yedek varsa
- once bos bir harici veritabani hazirla
- sonra v2 `backups` hattiyla ice aktar

Canli veri varken rastgele import yapma; once yedek al.

## 3. Render Servisleri

Iki servis acilacak:

- `crmcatkapinda-v2-api`
- `crmcatkapinda-v2`

`render.yaml` zaten hazir. Render'da eksik kalan kisim sadece gercek env degerlerini girmek.

## 4. Backend Env

Zorunlu:

- `CK_V2_APP_ENV=production`
- `CK_V2_RENDER_SERVICE_NAME=crmcatkapinda-v2-api`
- `CK_V2_DATABASE_URL=<gercek-postgresql-url>?sslmode=require`
- `CK_V2_FRONTEND_BASE_URL=https://<pilot-frontend-domain>`
- `CK_V2_PUBLIC_APP_URL=https://<pilot-frontend-domain>`
- `CK_V2_API_PUBLIC_URL=https://<pilot-api-domain>`
- `CK_V2_DEFAULT_AUTH_PASSWORD=<guclu-sifre>`

Guclu sifre kurali:

- en az 12 karakter
- buyuk harf
- kucuk harf
- rakam
- sembol

Opsiyonel ama onerilen:

- `AUTH_EBRU_PHONE`
- `AUTH_MERT_PHONE`
- `AUTH_MUHAMMED_PHONE`
- `SMS_PROVIDER=netgsm`
- `SMS_API_URL=https://api.netgsm.com.tr/sms/rest/v2/send`
- `SMS_NETGSM_USERNAME`
- `SMS_NETGSM_PASSWORD`
- `SMS_SENDER=CATKAPINDA`
- `SMS_NETGSM_ENCODING=TR`

## 5. Frontend Env

- `CK_V2_FRONTEND_SERVICE_NAME=crmcatkapinda-v2`
- `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
- `CK_V2_INTERNAL_API_HOSTPORT=<fromService>`
- `NEXT_TELEMETRY_DISABLED=1`

## 6. Deploy Once Calistirilacak Komutlar

Render env uygunluk kontrolu:

```bash
python3 v2/scripts/render_env_bundle.py \
  --frontend-url https://<pilot-frontend-domain> \
  --api-url https://<pilot-api-domain> \
  --database-url 'postgresql://<...>?sslmode=require' \
  --default-auth-password '<GucluSifre!2026>' \
  --validate-only
```

Canli pilot guard:

```bash
python3 v2/scripts/pilot_deploy_guard.py \
  --base-url https://<pilot-frontend-domain> \
  --api-url https://<pilot-api-domain> \
  --json
```

Smoke:

```bash
python3 v2/scripts/pilot_smoke.py \
  --base-url https://<pilot-frontend-domain> \
  --preset pilot \
  --json
```

Canli PostgreSQL omurgasi dogrulamasi:

```bash
python3 v2/scripts/database_preflight.py \
  --database-url 'postgresql://<...>?sslmode=require' \
  --json
```

Not:

- `database_preflight.py` artik sadece tablo ve kolonlari degil, `cutover` icin aktif restoran, aktif personel, subeye atanmis personel ve guncel puantaj tazeligini de kontrol eder.
- Ayni script artik PostgreSQL kullanicisinin tablo ve sequence yetkilerini de kontrol eder; `restaurants`, `personnel`, `daily_entries`, `deductions`, `inventory_purchases`, `sales_leads`, `courier_equipment_issues`, `box_returns` ile auth/session/audit tarafinda en az `SELECT`, `INSERT`, `UPDATE`, `DELETE` tablo yetkileri ve `id` sequence'lerinde `USAGE` yetkisi olmali.
- Ayni script kritik iliski kopukluklarini da tarar; `personel -> restoran`, `puantaj -> restoran/personel`, `kesinti -> personel`, `ekipman -> personel`, `box iade -> personel` zincirinde orphan kayit varsa `cutover` bloklanir.
- `pilot` acilisi ile `crmcatkapinda.com` cutover ayni esik degildir; `cutover` daha siki kalir.

## 7. Guvenli Pilot Sirasi

1. Render backend env'lerini gir.
2. Render frontend env'lerini gir.
3. API deploy al.
4. Frontend deploy al.
5. `database_preflight.py` ile canli PostgreSQL'i salt-okunur kontrol et.
6. `/api/health`, `/api/health/pilot`, `/status` kontrol et.
7. `pilot_deploy_guard.py` calistir.
8. Gercek login ve temel akislari ofis icinde dene.
9. Streamlit acik kalsin; v2 ilk asamada sadece pilot linkten kullanilsin.

## 8. crmcatkapinda.com Cutover Sirasi

1. Pilot 2-5 is gunu sorunsuz calissin.
2. Streamlit ustune banner koy.
3. Ekip gecis duyurusunu yap.
4. Dusuk trafikli saat sec.
5. Domain'i v2 frontend'e yonlendir.
6. Hemen ardindan:
   - giris
   - personel
   - puantaj
   - kesinti
   - raporlar
   - aylik hakedis
   kontrol et.
7. Sorun cikarsa gecici olarak Streamlit'e geri donus plani hazir olsun.

## 9. Veri Guvenligi

- Canliya cikmadan once PostgreSQL yedegi al.
- Mumkunse once staging/pilot veritabaninda prova yap.
- Varsayilan `123456` benzeri sifreyle canliya cikma.
- Yalnizca `https` domain kullan.
- Backend production security header'lari aktif olmadan cutover yapma.
- Yedek alma yetkisini yalnizca gerekli kullanicilarda tut.

## 10. Go / No-Go Karari

Go demek icin bu dort madde birlikte yesil olmali:

- `pilot_deploy_guard.py` passed
- `pilot_smoke.py` passed
- `database_preflight.py` passed
- `CK_V2_DATABASE_URL` gercek degerde
- `CK_V2_DEFAULT_AUTH_PASSWORD` guclu gercek degerde

Bu maddelerden biri kirmiziysa cutover yapma.
