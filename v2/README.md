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
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service crmcatkapinda --cutover-mode banner`
- sadece eski Streamlit redirect env'i icin:
  - `python v2/scripts/render_env_bundle.py --frontend-url https://<v2-frontend-domain> --api-url https://<v2-api-domain> --service crmcatkapinda --cutover-mode redirect`

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
