# V2 Migration Plan

## Why v2

The current Streamlit application is feature-rich, but the product now behaves
like a multi-role operations platform:
- office users manage attendance, deductions, payroll, and reporting
- mobile users need constrained, fast access
- sales and operations flow into each other
- repeated reruns and large forms make the UI feel slow

The v2 goal is to move to a conventional web stack:
- backend: FastAPI
- frontend: Next.js
- database: keep current PostgreSQL

## Delivery Principles

1. The Streamlit app stays live until each replacement slice is production-safe.
2. We migrate screen by screen, not with a big-bang rewrite.
3. The current PostgreSQL schema remains the source of truth at first.
4. Business rules move into backend services before UI redesigns depend on them.

## Phase 1: Foundation

Scope:
- backend app shell
- frontend app shell
- shared environment and deployment conventions
- health endpoint and typed settings

Output:
- deployable FastAPI service
- deployable Next.js shell
- shared navigation language matching the current product

## Phase 2: Authentication and Roles

Scope:
- email login
- phone/SMS login
- role-restricted sessions
- mobile operations access for bolge muduru users

Source modules:
- `infrastructure/auth_engine.py`
- `rules/permission_rules.py`
- `services/permission_service.py`

Notes:
- The v2 backend should own token/session logic.
- The v2 frontend should handle route guards and menu visibility.

## Phase 3: Attendance First

Scope:
- daily attendance entry
- attendance management grid
- bulk attendance import

Source modules:
- `services/attendance_service.py`
- `repositories/attendance_repository.py`
- `ui` + `app.py` attendance sections

Why first:
- highest daily usage
- currently the most obvious Streamlit performance bottleneck
- strongest need for partial page updates

## Phase 4: Personnel and Restaurant Management

Scope:
- personnel create/edit
- restaurant create/edit
- role-based constrained views

Source modules:
- `services/personnel_service.py`
- `repositories/personnel_repository.py`
- `services/restaurant_service.py`
- `repositories/restaurant_repository.py`

## Phase 5: Sales to Operations Handoff

Scope:
- sales leads
- proposal model capture
- conversion from lead to live restaurant

Source modules:
- `services/sales_service.py`
- `repositories/sales_repository.py`
- `ui/sales_sections.py`

## Phase 6: Finance and Reporting

Scope:
- deductions
- monthly payroll
- reports and profitability
- side-income tracking

Source modules:
- `services/deductions_service.py`
- `services/reporting_service.py`
- `engines/finance_engine.py`
- `rules/reporting_rules.py`

## Backend Mapping

Recommended backend modules:
- `app/api/routes/auth.py`
- `app/api/routes/attendance.py`
- `app/api/routes/personnel.py`
- `app/api/routes/restaurants.py`
- `app/api/routes/sales.py`
- `app/api/routes/reports.py`

Recommended service layers:
- `app/services/auth.py`
- `app/services/attendance.py`
- `app/services/personnel.py`
- `app/services/restaurants.py`
- `app/services/sales.py`
- `app/services/reports.py`

Recommended persistence layers:
- `app/repositories/*.py`

## Frontend Mapping

Recommended route groups:
- `/login`
- `/dashboard`
- `/attendance`
- `/personnel`
- `/restaurants`
- `/sales`
- `/reports`
- `/settings/profile`

## Immediate Next Slice

Build this next:
1. Auth shell
2. Attendance page shell
3. Attendance create form
4. Attendance list view

That slice gives the biggest UX gain with the lowest rewrite risk.
