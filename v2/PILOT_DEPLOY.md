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
  - Render acilis adimlari

Yerel smoke check:
- `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain>`
- kolay pilot preset:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --preset pilot`
- kolay cutover preset:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --preset cutover`
- opsiyonel JSON rapor:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --json --output pilot-report.json`
- opsiyonel Markdown rapor:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --markdown --output pilot-report.md`
- opsiyonel gerçek login smoke:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --identity ebru@catkapinda.com --password <sifre>`
- opsiyonel eski Streamlit banner smoke:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --legacy-url https://crmcatkapinda.com --legacy-cutover-mode banner`
- opsiyonel eski Streamlit redirect smoke:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --legacy-url https://crmcatkapinda.com --legacy-cutover-mode redirect`

Env bloklarini tek komutta hazirlamak icin:
- `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain>`
- JSON cikti istenirse:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --json`
- sadece eski Streamlit banner env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service streamlit --cutover-mode banner`
- sadece eski Streamlit redirect env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service streamlit --cutover-mode redirect`
- sadece API env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service api`
- sadece frontend env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service frontend`

Acilis paketi uretmek icin:
- `python v2/scripts/pilot_launch_packet.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output pilot-launch.md`
- redirect provasi paketi icin:
  - `python v2/scripts/pilot_launch_packet.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --cutover-mode redirect --output pilot-cutover.md`
- bu paket artik hazir env bloklarini da icerir

Canli pilot durum raporu icin:
- `python v2/scripts/pilot_status_report.py --base-url https://<v2-frontend-domain> --output pilot-status-live.md`
- JSON raporu istenirse:
  - `python v2/scripts/pilot_status_report.py --base-url https://<v2-frontend-domain> --json --output pilot-status-live.json`
- bu rapor `/api/pilot-status` verisini cekip paylasilabilir tek dosyada toplar

Pilot gate karari icin:
- `python v2/scripts/pilot_gate.py --base-url https://<v2-frontend-domain> --mode pilot`
- redirect cutover karari icin:
  - `python v2/scripts/pilot_gate.py --base-url https://<v2-frontend-domain> --mode cutover`
- bu helper basariliysa `0`, blokaj varsa `2` ile cikar

Pilot preflight paketi icin:
- `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight`
- smoke sonucunu da preflight paketine gommek istersen:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight --include-smoke --preset pilot`
- ayni output klasorune yeniden preflight ureteceksen:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight --fresh-output`
- smoke da exit koduna girsin istersen:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight --include-smoke --preset pilot --strict-smoke`
- bu helper tek klasorde:
  - canli status markdown
  - canli status json
  - pilot gate json
  - cutover gate json
  - preflight summary markdown
  - smoke aciksa:
    - smoke markdown
    - smoke json
  uretir
- pilot gate gecerliyse `0`, degilse `2` ile cikar
- smoke kapaliyken eski `pilot-smoke-live.*` dosyalari varsa otomatik temizlenir; stale smoke artefakti kalmaz

Pilot cutover guard icin:
- `python v2/scripts/pilot_cutover_guard.py --base-url https://<v2-frontend-domain> --mode banner`
- `python v2/scripts/pilot_cutover_guard.py --base-url https://<v2-frontend-domain> --mode redirect`
- bu helper canli gate sonucuna gore env blogunu verir
- blokaj varsa `2` ile cikar
- zorunlu override gerektiginde `--force` kullanilabilir

Pilot day zero kiti icin:
- `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero`
- smoke sonucunu da day-zero kitine gommek istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --include-smoke --smoke-preset pilot`
- verify de exit koduna dahil olsun istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --strict`
- smoke da exit koduna dahil olsun istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --include-smoke --smoke-preset pilot --strict-smoke`
- `--api-url` verilmezse canli `/api/pilot-status` uzerinden backend servisi bulunmaya calisilir
- bu helper ayni klasorde:
  - env bundle
  - launch packet
  - preflight summary
  - gate jsonlari
  - verify markdown/json
  - streamlit banner/redirect env
  - streamlit banner/redirect guard json
  - streamlit banner/redirect guarded env
  - `00-START-HERE.md`
  toplar
- ayrica ayni isimle `.zip` arsivi de uretir
- kit ozetinde verify ve smoke sonucu ile onerilen sonraki adimlar da yazilir
- kit tam mi diye hizli kontrol icin:
  - `python v2/scripts/pilot_day_zero_verify.py --output-dir pilot-day-zero`
- ayni output klasorune yeniden kit ureteceksen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --fresh-output`
  - bu flag mevcut output klasorunu ve ayni isimli zip arsivini temizleyip kiti bastan kurar
- `pilot_day_zero.py` verify raporunu iki asamada gunceller; bu sayede bundle icindeki `pilot-day-zero-verify.*` dosyalari final kitin kendisini anlatir
- `pilot_day_zero.py` bundle klasorunu canonical path ile manifestler; boylece `/var` ve `/private` alias path farklari verify tarafinda gereksiz fail uretmez
- `pilot_day_zero_verify.py` da manifest ve embedded verify icindeki path alanlarini canonical olarak karsilastirir; symlink/alias path kullanimi dogru bundle'larda sahte blokaj yaratmaz
- smoke ile uretilen kitlerde verify ayrica:
  - smoke dosyalari var mi
  - smoke sonucu manifestle tutarli mi
  - zip arsivinde smoke dosyalari tasiniyor mu
  - checksum katmaniyla dosya ve zip icerigi manifestle birebir uyusuyor mu
  - zip icindeki `pilot-day-zero-manifest.json` kopyasi disaridaki manifestle birebir uyusuyor mu
  - release snapshot ile pilot-status-live.json ayni build bilgisini veriyor mu
  - `00-START-HERE.md` icindeki rehber satirlari manifest durumuyla uyusuyor mu
  - render-env-bundle / render-env-bundle.json / streamlit banner / streamlit redirect env dosyalari dogru URL ve mode'u tasiyor mu
  - env dosyalarinda manifestte olmayan stale / beklenmeyen servis bolumu kalmis mi
  - env bolumlerinin icinde beklenmeyen stale anahtar kalmis mi
  - streamlit guard json dosyalari dogru mode / base_url / service / gate bilgisi tasiyor mu
  - guarded env dosyalari guard json icindeki env bloguyla birebir uyusuyor mu
  - pilot launch / cutover paketleri dogru link, komut ve gomulu env bloklarinin butununu tasiyor mu
  - `pilot-status-live.md` ve `pilot-preflight-summary.md` raporlari karar/gate/release satirlarini guncel tasiyor mu
  - `pilot-smoke-live.md` raporu `pilot-smoke-live.json` ile, metadata, karar satirlari ve check tablosu, satir sirasi, beklenmeyen/tekrarlanan tablo satirlari ve stale summary bullet'lari dahil, birebir uyusuyor mu
  - `pilot-smoke-live.json` icindeki passed/failed/overall ve failing_checks alanlari result listesiyle, sirasi dahil, tutarli mi
  - `pilot-smoke-live.json` icindeki cekirdek decision alanlari (`status`, `headline`, `primary_blocker`, `recommended_next_step`) result listesiyle tutarli mi
  - smoke dahil kitlerde `pilot-smoke-live.json` icindeki result listesi bos mu
  - `pilot-day-zero-verify.json` ve `pilot-day-zero-verify.md` dosyalari manifestteki verify sonucu ile uyumlu mu
  - gomulu verify raporlari `Release Snapshot`, `Env Payloads`, `Launch Packets` ve `Manifest Core/Summary/Files` sonuclarini da guncel verify ile ayni tasiyor mu
  - `pilot-day-zero-manifest.json` icindeki gate/guard/verify ozet alanlari alttaki json raporlarla uyumlu mu
  - `pilot-day-zero-manifest.json` icindeki files haritasi dogru etiketleri dogru dosya adlarina bagliyor mu
  - `pilot-day-zero-manifest.json` icindeki frontend/api/streamlit URL'leri, service name'ler ve archive path cekirdek metadata'si artefaktlarla uyumlu mu
  - output klasoru ya da zip arsivi icinde manifestte olmayan stale / beklenmeyen dosya kalmis mi
  kontrol eder

## Zorunlu Ayarlar

### Backend

- `CK_V2_DATABASE_URL`
  - mevcut CRM'in baglandigi ayni PostgreSQL URL'si
  - not: backend plain `DATABASE_URL` de okuyabilir
- `CK_V2_FRONTEND_BASE_URL`
  - v2 frontend public URL'si
- `CK_V2_PUBLIC_APP_URL`
  - v2 frontend public URL'si
- `CK_V2_API_PUBLIC_URL`
  - v2 backend public URL'si
  - `/status` ekraninda backend servis adresini dogru gostermek icin onerilir
- `CK_V2_APP_ENV=production`
  - backend status ekraninin production olarak gorunmesini saglar
- `CK_V2_RENDER_SERVICE_NAME=crmcatkapinda-v2-api`
  - backend servis adini status ekraninda sabit ve net gosterir
- `CK_V2_DEFAULT_AUTH_PASSWORD`
  - yonetici ve mobil operasyon kullanicilarinin ilk sifresi
  - not: varsayilan `123456` yerine pilot oncesi yeni bir sifre girmen onerilir

Not:
- `CK_V2_FRONTEND_BASE_URL` veya `CK_V2_PUBLIC_APP_URL` alanlarindan en az biri pilot icin yeterlidir.
- Ikisini de girersen status ekrani ikisini de gosterebilir; ama readiness icin tek URL yeterlidir.
- `CK_V2_API_PUBLIC_URL` zorunlu degildir ama pilot status ve servis linklerini temiz gormek icin tavsiye edilir.

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
  - Render pilotunda tercih edilen ayar budur
- `CK_V2_INTERNAL_API_BASE_URL`
  - yalnizca yerel frontend calistirirken gerekir
  - ornek: `http://127.0.0.1:8000`
  - Render pilotunda bunu kullanmak zorunda degilsin

Frontend env ozeti:

- Yerel deneme:
  - `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
  - `CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000`
- Render pilot:
  - `CK_V2_FRONTEND_SERVICE_NAME=crmcatkapinda-v2`
  - `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
  - `CK_V2_INTERNAL_API_HOSTPORT=<fromService>`

Not:
- `/status` ekranindaki env planinda bu iki frontend modu da ayri kartlar halinde gorunur.

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
`/status` ekranindaki `Eski Streamlit Servisi Gecis Env Bloku` karti da bu degerleri kopyalamak icin hazir durur.

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
   - istenirse JSON raporu da alinabilir:
     - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --json --output pilot-report.json`
   - istenirse Markdown raporu da alinabilir:
     - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --markdown --output pilot-report.md`
   - istenirse login de dogrulanabilir:
     - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --identity ebru@catkapinda.com --password <sifre>`
11. `status` ekranindaki `zorunlu eksik env` sayisi `0` olmali
12. `status` ekranindaki `Streamlit'ten cikis ozeti` karti en az `Pilot Acilabilir` seviyesinde olmali
13. `status` ekranindaki `Pilot Acilis Sirasi` kartinda adimlar bloklu olmamali

Not:
- smoke script artik opsiyonel SMS env eksiklerini blokaj saymaz
- gecme mantigi:
  - `required_missing_env_vars = 0`
  - `cutover.phase = ready_for_pilot` veya `ready_for_cutover`
- `--identity` ve `--password` verilirse script login + `/auth/me` akisini da test eder
- login smoke aciksa ek olarak korumali v2 sayfalarini da dogrular:
  - `/attendance`
  - `/personnel`
  - `/deductions`
  - `/reports`
- legacy smoke aciksa eski Streamlit panelde:
  - `banner` modunda v2 geçiş kartını
  - `redirect` modunda otomatik geçiş yüzeyini
  da doğrular
- JSON / Markdown smoke raporlari ayrica sunlari da verir:
  - pilot karar ozeti
  - ana blokaj
  - onerilen siradaki adim
- `--preset pilot` otomatik olarak legacy banner smoke'u da acar
- `--preset cutover` otomatik olarak legacy redirect smoke'u da acar
