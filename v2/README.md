# Cat Kapinda CRM v2

This directory contains the parallel rebuild track for the CRM.

Goals:
- Keep the existing Streamlit app live while rebuilding the product as a
  standard web application.
- Move high-traffic operational flows first.
- Reuse the current PostgreSQL schema and business rules incrementally.

Structure:
- `backend/`: FastAPI application for auth, attendance, personnel, reporting.
- `frontend/`: Next.js application for the browser UI.
- `MIGRATION_PLAN.md`: phased migration roadmap.
- `PILOT_DEPLOY.md`: Render pilot acilisi icin kisa runbook.

Run locally:
- Backend:
  - copy `backend/.env.example` to `backend/.env`
  - install from `backend/`
  - run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend:
  - copy `frontend/.env.example` to `frontend/.env.local`
  - keep `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
  - keep `CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000`
  - install from `frontend/`
  - run `npm run dev`

Deploy:
- `render.yaml` inside this folder defines two services:
  - `crmcatkapinda-v2-api`
  - `crmcatkapinda-v2`
- Import this blueprint separately from the existing Streamlit deployment.
- Point `CK_V2_DATABASE_URL` to the same PostgreSQL database used by the current app.
- Set these two env vars on the API service after deploy:
  - `CK_V2_FRONTEND_BASE_URL=https://<frontend-domain>`
  - `CK_V2_PUBLIC_APP_URL=https://<frontend-domain>`
- Recommended on the API service for cleaner pilot status links:
  - `CK_V2_API_PUBLIC_URL=https://<api-domain>`
- Required for first management/mobile auth bootstrap on the API service:
  - `CK_V2_DEFAULT_AUTH_PASSWORD`
- Recommended on the API service for cleaner pilot status metadata:
  - `CK_V2_APP_ENV=production`
  - `CK_V2_RENDER_SERVICE_NAME=crmcatkapinda-v2-api`
- Frontend proxy env strategy:
  - local dev:
    - `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
    - `CK_V2_INTERNAL_API_BASE_URL=http://127.0.0.1:8000`
  - Render pilot:
    - `CK_V2_FRONTEND_SERVICE_NAME=crmcatkapinda-v2`
    - `NEXT_PUBLIC_V2_API_BASE_URL=/v2-api`
    - `CK_V2_INTERNAL_API_HOSTPORT=<fromService>`
  - `/status` ekraninda her iki frontend modu da ayri env blogu olarak gorunur
- Optional but recommended for phone/SMS login on the API service:
  - `AUTH_EBRU_PHONE`
  - `AUTH_MERT_PHONE`
  - `AUTH_MUHAMMED_PHONE`
  - `SMS_PROVIDER=netgsm`
  - `SMS_API_URL=https://api.netgsm.com.tr/sms/rest/v2/send`
  - `SMS_NETGSM_USERNAME`
  - `SMS_NETGSM_PASSWORD`
  - `SMS_SENDER=CATKAPINDA`
  - `SMS_NETGSM_ENCODING=TR`
- Keep the current Streamlit app live during pilot rollout; v2 is intended to run in parallel first.

Render env bundle helper:
- Pilot acilisinda kopyalanabilir env bloklarini tek komutta uretmek icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain>`
- istenirse JSON olarak:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --json`
- sadece eski Streamlit banner env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service streamlit --cutover-mode banner`
- sadece eski Streamlit redirect env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service streamlit --cutover-mode redirect`
- sadece API env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service api`
- sadece frontend env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service frontend`

Pilot launch packet helper:
- Ekipte paylaşılabilir markdown açılış paketi üretmek için:
  - `python v2/scripts/pilot_launch_packet.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output pilot-launch.md`
- redirect provası için:
  - `python v2/scripts/pilot_launch_packet.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --cutover-mode redirect --output pilot-cutover.md`
- bu paket artık doğrudan hazır env bloklarını da içerir

Live pilot status report helper:
- Anlik `/api/pilot-status` verisini paylasilabilir rapora cevirmek icin:
  - `python v2/scripts/pilot_status_report.py --base-url https://<v2-frontend-domain> --output pilot-status-live.md`
- ham JSON gerekiyorsa:
  - `python v2/scripts/pilot_status_report.py --base-url https://<v2-frontend-domain> --json --output pilot-status-live.json`
- bu rapor sunlari tek dosyada toplar:
  - bugunun karari
  - cutover ozeti
  - blokajlar ve kalan maddeler
  - pilot linkleri
  - komut paketi / smoke / helper komutlari

Pilot gate helper:
- Pilot acilabilir mi diye anlik karar almak icin:
  - `python v2/scripts/pilot_gate.py --base-url https://<v2-frontend-domain> --mode pilot`
- Redirect cutover'a gecilebilir mi diye bakmak icin:
  - `python v2/scripts/pilot_gate.py --base-url https://<v2-frontend-domain> --mode cutover`
- bu helper `/api/pilot-status` verisine gore:
  - `0` ile gecer
  - blokaj varsa `2` ile cikar
  - yani terminal cikis koduyla da net karar verir

Pilot preflight bundle helper:
- Canli pilot durumu icin tum ciktıları tek klasorde toplamak icin:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight`
- smoke sonucunu da preflight paketine gommek istersen:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight --include-smoke --preset pilot`
- smoke da exit koduna girsin istersen:
  - `python v2/scripts/pilot_preflight.py --base-url https://<v2-frontend-domain> --output-dir pilot-preflight --include-smoke --preset pilot --strict-smoke`
- bu helper sunlari birlikte uretir:
  - `pilot-preflight-summary.md`
  - `pilot-status-live.md`
  - `pilot-status-live.json`
  - `pilot-gate-pilot.json`
  - `pilot-gate-cutover.json`
  - smoke aciksa:
    - `pilot-smoke-live.md`
    - `pilot-smoke-live.json`
- pilot gate gecerliyse `0`, degilse `2` ile cikar

Pilot cutover guard helper:
- Streamlit `banner` env'ini yalnizca canli pilot gecerliyse uretmek icin:
  - `python v2/scripts/pilot_cutover_guard.py --base-url https://<v2-frontend-domain> --mode banner`
- Streamlit `redirect` env'ini yalnizca canli cutover gecerliyse uretmek icin:
  - `python v2/scripts/pilot_cutover_guard.py --base-url https://<v2-frontend-domain> --mode redirect`
- blokaj varsa `2` ile cikar
- acil durumda override icin:
  - `--force`

Pilot day zero kit helper:
- Pilot gunu tum ana artefaktlari tek klasorde toplamak icin:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero`
- smoke sonucunu da day-zero kitine gommek istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --include-smoke --smoke-preset pilot`
- verify de exit koduna girsin istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --strict`
- smoke da exit koduna girsin istersen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --include-smoke --smoke-preset pilot --strict-smoke`
- `--api-url` verilmezse script bunu canli `/api/pilot-status` verisinden cikarmayi dener
- bu helper sunlari bir arada uretir:
  - render env bundle
  - streamlit banner env
  - streamlit redirect env
  - streamlit banner/redirect guard json
  - streamlit banner/redirect guarded env
  - pilot launch packet
  - pilot cutover packet
  - canli preflight ciktıları
  - day-zero manifest json
  - day-zero verify markdown/json
  - `00-START-HERE.md`
  - paylasilabilir `.zip` arsivi
- manifest ve konsol ozetinde artik:
  - verify pass/fail
  - verify sonrasi onerilen adim
  - smoke pass/fail
  - smoke sonrasi onerilen adim
  da gorunur
- uretilen kitin eksik ve tutarlilik kontrolu icin:
  - `python v2/scripts/pilot_day_zero_verify.py --output-dir pilot-day-zero`
- ayni output klasorune yeniden kit ureteceksen:
  - `python v2/scripts/pilot_day_zero.py --base-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --output-dir pilot-day-zero --fresh-output`
  - bu flag mevcut output klasorunu ve ayni isimli zip arsivini temizleyip kiti bastan kurar
- `pilot_day_zero.py` output klasorunu canonical path'e (`resolve`) cevirerek manifestler; boylece `/var` ve `/private` gibi alias path farklari verify tarafinda sahte uyumsuzluk yaratmaz
- `pilot_day_zero_verify.py` da manifest/verify icindeki path alanlarini canonical olarak karsilastirir; symlink veya alias path kullanilsa bile ayni hedefe bakiyorsa gereksiz fail uretmez
- eger kit smoke ile uretildiyse verify artik:
  - smoke markdown/json dosyalarini
  - smoke sonucunun manifest ile uyumunu
  - zip arsivinin smoke dosyalarini da tasiyip tasimadigini
  - checksum katmaniyla dosya ve zip iceriginin manifestle birebir uyumunu
  - zip icindeki `pilot-day-zero-manifest.json` kopyasinin disaridaki manifestle birebir uyumlu kalip kalmadigini
  - release snapshot'in pilot-status-live.json ile ayni build bilgisini tasiyip tasimadigini
  - `00-START-HERE.md` rehberinin verify/smoke/release satirlarini guncel tutup tutmadigini
  - env dosyalarinin ve `render-env-bundle.json` esleniginin dogru URL ve cutover modlarini tasiyip tasimadigini
  - env dosyalarinda manifestte olmayan stale / beklenmeyen servis bolumu kalip kalmadigini
  - env bolumlerinin icinde beklenmeyen stale anahtar kalip kalmadigini
  - guard json dosyalarinin (`streamlit-banner-guard.json`, `streamlit-redirect-guard.json`) dogru mode/base_url/service/gate bilgisi tasiyip tasimadigini
  - guarded env dosyalarinin guard json icindeki env bloguyla birebir uyumlu kalip kalmadigini
  - `pilot-launch.md` ve `pilot-cutover.md` paketlerinin dogru link ve cutover komutlarini tasiyip tasimadigini
  - `pilot-status-live.md` ve `pilot-preflight-summary.md` raporlarinin karar/gate/release satirlarini guncel tutup tutmadigini
  - `pilot-day-zero-verify.json` ve `pilot-day-zero-verify.md` dosyalarinin manifestteki verify sonucu ile uyumlu kalip kalmadigini
  - gomulu verify raporlarinin `Release Snapshot`, `Env Payloads`, `Launch Packets` ve `Manifest Core/Summary/Files` durumlarini da guncel verify ile ayni tasiyip tasimadigini
  - `pilot-day-zero-manifest.json` icindeki gate/guard/verify ozet alanlarinin alttaki json raporlarla uyumlu kalip kalmadigini
  - `pilot-day-zero-manifest.json` icindeki `files` haritasinin dogru etiketleri dogru dosya adlarina baglayip baglamadigini
  - `pilot-day-zero-manifest.json` icindeki `frontend_url` / `api_url` / `streamlit_url` / `service_names` / `archive_path` cekirdek metadata'sinin artefaktlarla uyumlu kalip kalmadigini
  - output klasoru ya da zip arsivi icinde manifestte olmayan stale / beklenmeyen dosya kalip kalmadigini
  da kontrol eder

Pilot smoke check:
- After deploy, run:
  - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain>`
  - easier pilot preset:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --preset pilot`
  - easier cutover preset:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --preset cutover`
  - optional JSON report:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --json --output pilot-report.json`
  - optional Markdown report:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --markdown --output pilot-report.md`
  - optional auth smoke:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --identity ebru@catkapinda.com --password <sifre>`
  - optional legacy Streamlit bridge smoke:
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --legacy-url https://crmcatkapinda.com --legacy-cutover-mode banner`
    - `python v2/scripts/pilot_smoke.py --base-url https://<v2-frontend-domain> --legacy-url https://crmcatkapinda.com --legacy-cutover-mode redirect`
- This verifies:
  - frontend health
  - frontend readiness
  - status page
  - login page
  - backend health
  - backend readiness
  - backend pilot cutover phase (`ready_for_pilot` / `ready_for_cutover`)
  - optional machine-readable JSON pilot report
  - optional shareable Markdown pilot report
  - optionally login + `/auth/me` if identity/password are provided
  - if login smoke is enabled, protected v2 pages:
    - `/attendance`
    - `/personnel`
    - `/deductions`
    - `/reports`
  - if legacy bridge smoke is enabled, the old Streamlit app's banner/redirect bridge
  - JSON / Markdown smoke reports now also include:
    - pilot decision summary
    - primary blocker
    - recommended next step
  - `--preset pilot` automatically adds the legacy banner bridge check
  - `--preset cutover` automatically adds the legacy redirect bridge check
