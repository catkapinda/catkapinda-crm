from __future__ import annotations

from datetime import date

import psycopg

from app.repositories.attendance import (
    fetch_attendance_summary,
    fetch_recent_attendance_entries,
)
from app.schemas.attendance import (
    AttendanceDashboardResponse,
    AttendanceEntrySummary,
    AttendanceModuleStatus,
    AttendanceSummary,
)

ENTRY_MODE_ALIASES = {
    "Haftalik Buyume": "Haftalik Izin",
    "Haftalık Büyüme": "Haftalik Izin",
}


def _normalize_entry_mode(value: str) -> str:
    normalized = str(value or "").strip()
    return ENTRY_MODE_ALIASES.get(normalized, normalized or "Restoran Kuryesi")


def build_attendance_status() -> AttendanceModuleStatus:
    return AttendanceModuleStatus(
        module="attendance",
        status="active",
        next_slice="daily-entry-dashboard",
    )


def build_attendance_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    limit: int,
) -> AttendanceDashboardResponse:
    summary_values = fetch_attendance_summary(conn, reference_date=reference_date)
    recent_entry_rows = fetch_recent_attendance_entries(conn, limit=limit)
    return AttendanceDashboardResponse(
        module="attendance",
        status="active",
        summary=AttendanceSummary(
            total_entries=summary_values["total_count"],
            today_entries=summary_values["today_count"],
            month_entries=summary_values["month_count"],
            active_restaurants=summary_values["active_restaurants"],
        ),
        recent_entries=[
            AttendanceEntrySummary(
                id=int(row["id"]),
                entry_date=row["entry_date"],
                restaurant=str(row["restaurant"] or ""),
                employee_name=str(row["employee_name"] or "-"),
                entry_mode=_normalize_entry_mode(str(row["entry_mode"] or "")),
                absence_reason=str(row["absence_reason"] or ""),
                coverage_type=str(row["coverage_type"] or ""),
                worked_hours=float(row["worked_hours"] or 0),
                package_count=float(row["package_count"] or 0),
                monthly_invoice_amount=float(row["monthly_invoice_amount"] or 0),
                notes=str(row["notes"] or ""),
            )
            for row in recent_entry_rows
        ],
    )
