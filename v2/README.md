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
