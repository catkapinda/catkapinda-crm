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
- Keep the current Streamlit app live during pilot rollout; v2 is intended to run in parallel first.
