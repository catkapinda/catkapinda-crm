# v2 Pilot Deploy

Bu runbook, Streamlit sistemi kapatmadan v2'yi paralel pilot olarak açmak icin kullanilir.

## Hedef

- Mevcut `crmcatkapinda.com` Streamlit olarak calismaya devam eder.
- v2 ayri bir frontend ve ayri bir backend olarak Render'da acilir.
- Ofis ekibi once pilot linkinden v2'yi test eder.

## Render Uzerinde Acilacak Servisler

`v2/render.yaml` iki web service tanimlar:

- `crmcatkapinda-v2-api`
- `crmcatkapinda-v2`

Frontend health check:
- `https://<v2-frontend-domain>/api/health`
- `https://<v2-frontend-domain>/api/ready`

Backend health check:
- `https://<v2-api-domain>/api/health`
- `https://<v2-api-domain>/api/health/ready`
- `https://<v2-api-domain>/api/health/pilot`

Pilot durum sayfasi:
- `https://<v2-frontend-domain>/status`
  - deploy hazirligi
  - eksik env listesi
  - siradaki adimlar
  - modül hazirlik durumu

Yerel smoke check:
- `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain>`

## Zorunlu Ayarlar

### Backend

- `CK_V2_DATABASE_URL`
  - mevcut CRM'in baglandigi ayni PostgreSQL URL'si
  - not: backend plain `DATABASE_URL` de okuyabilir
- `CK_V2_FRONTEND_BASE_URL`
  - v2 frontend public URL'si
- `CK_V2_PUBLIC_APP_URL`
  - v2 frontend public URL'si
- `CK_V2_DEFAULT_AUTH_PASSWORD`
  - yonetici ve mobil operasyon kullanicilarinin ilk sifresi

Not:
- `CK_V2_FRONTEND_BASE_URL` veya `CK_V2_PUBLIC_APP_URL` alanlarindan en az biri pilot icin yeterlidir.
- Ikisini de girersen status ekrani ikisini de gosterebilir; ama readiness icin tek URL yeterlidir.

### SMS login icin opsiyonel ayarlar

- `AUTH_EBRU_PHONE`
- `AUTH_MERT_PHONE`
- `AUTH_MUHAMMED_PHONE`
- `SMS_PROVIDER=netgsm`
- `SMS_API_URL=https://api.netgsm.com.tr/sms/rest/v2/send`
- `SMS_NETGSM_USERNAME`
- `SMS_NETGSM_PASSWORD`
- `SMS_SENDER=CATKAPINDA`
- `SMS_NETGSM_ENCODING=TR`

Not:
- v2 backend acilisinda auth tarafindaki temel tablolar/kolonlar (`auth_users`, `auth_sessions`, `auth_phone_codes`) icin runtime bootstrap dener.
- Bu sayede eski veritabani varyasyonlarinda login katmani daha dayanikli acilir.
- Yine de ana operasyon tablolari (`daily_entries`, `restaurants`, `personnel`, vb.) mevcut CRM veritabaninda bulunmali; `/status` ekrani bunlari ayrica gosterir.
- SMS env alanlari ilk pilot acilisi icin zorunlu degildir.
- Pilot e-posta/sifre ile acilip test edilebilir; SMS login sonradan da aktif edilebilir.

### Frontend

- `NEXT_PUBLIC_V2_API_BASE_URL`
  - Render blueprint ile `/v2-api` olarak gelir
- `CK_V2_INTERNAL_API_HOSTPORT`
  - Render blueprint ile backend servisinden gelir

## Pilot Hazir Sayilmasi Icin

Asagidaki ekranlar calisir olmali:

- `Genel Bakis`
- `Puantaj`
- `Personel`
- `Kesintiler`
- `Aylik Hakedis`
- `Satin Alma`
- `Satis`
- `Restoranlar`
- `Raporlar`
- `Telefon / SMS kodlu giris`

## Cikis Anini Nasil Anlariz

Asagidaki kosullar saglandiginda Streamlit'ten fiilen cikis asamasina gelinmis olur:

- Ofis gunluk operasyonu v2 linkinden yapabiliyor
- Kritik CRUD ekranlari v2'de sorunsuz calisiyor
- Raporlar ve hakedis ekranlari yeterli dogruluga ulasiyor
- Streamlit sadece yedek panel gibi kalıyor

## Son Adim

Pilot stabil oldugunda:

1. kullanicilar yeni v2 linkine yonlendirilir
2. Streamlit yalnizca yedek/geri donus yolu olarak tutulur
3. sonra ana domain v2'ye gecirilir

## Streamlit Cutover Switch

Ana Streamlit panelde yeni sisteme gecisi kod degistirmeden acmak icin:

- `CK_V2_PILOT_URL=https://<v2-frontend-domain>`
- `CK_V2_CUTOVER_MODE=banner`
  - eski panel acilir ama ustte yeni sisteme gecis butonu gosterir
- `CK_V2_CUTOVER_MODE=redirect`
  - eski panel yerine kullaniciyi dogrudan v2'ye yonlendirir

Bu iki alan Render Environment veya `secrets.toml` icindeki `[v2]` bolumu ile de verilebilir.

## Pilot Acildiginda Ilk Kontrol

1. frontend `api/health` 200 donmeli
2. frontend `api/ready` 200 donmeli ve backend erisimi `true` olmali
3. backend `api/health` 200 donmeli
4. backend `api/health/ready` 200 donmeli
5. backend `api/health/pilot` 200 donmeli
6. `status` sayfasi acilip kontrolleri gostermeli
7. `login` ekrani acilmali
8. e-posta/sifre girisi calismali
9. SMS login env'leri girildiyse telefon kodu akisi da calismali
10. smoke script temiz donmeli:
   - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain>`
11. `status` ekranindaki `zorunlu eksik env` sayisi `0` olmali
