from __future__ import annotations

from datetime import date

import psycopg

from app.schemas.overview import (
    OverviewActivityItem,
    OverviewDashboardResponse,
    OverviewHeroSummary,
    OverviewModuleCard,
)
from app.services.attendance import build_attendance_dashboard
from app.services.deductions import build_deductions_dashboard
from app.services.personnel import build_personnel_dashboard
from app.services.restaurants import build_restaurants_dashboard


def build_overview_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> OverviewDashboardResponse:
    attendance_dashboard = build_attendance_dashboard(conn, reference_date=reference_date, limit=6)
    personnel_dashboard = build_personnel_dashboard(conn, limit=6)
    deductions_dashboard = build_deductions_dashboard(conn, reference_date=reference_date, limit=6)
    restaurants_dashboard = build_restaurants_dashboard(conn, limit=6)

    recent_activity: list[OverviewActivityItem] = []

    for entry in attendance_dashboard.recent_entries:
        recent_activity.append(
            OverviewActivityItem(
                module_key="attendance",
                module_label="Puantaj",
                title=entry.restaurant,
                subtitle=f"{entry.employee_name} | {entry.entry_mode}",
                meta=f"{entry.worked_hours:.1f} saat | {entry.package_count:.0f} paket",
                entry_date=entry.entry_date,
                href="/attendance",
            )
        )

    for entry in personnel_dashboard.recent_entries:
        recent_activity.append(
            OverviewActivityItem(
                module_key="personnel",
                module_label="Personel",
                title=entry.full_name,
                subtitle=f"{entry.role} | {entry.status}",
                meta=entry.restaurant_label or "-",
                entry_date=entry.start_date,
                href="/personnel",
            )
        )

    for entry in deductions_dashboard.recent_entries:
        recent_activity.append(
            OverviewActivityItem(
                module_key="deductions",
                module_label="Kesintiler",
                title=entry.personnel_label,
                subtitle=entry.deduction_type,
                meta=f"{entry.amount:,.0f} TL",
                entry_date=entry.deduction_date,
                href="/deductions",
            )
        )

    for entry in restaurants_dashboard.recent_entries:
        recent_activity.append(
            OverviewActivityItem(
                module_key="restaurants",
                module_label="Restoranlar",
                title=f"{entry.brand} - {entry.branch}",
                subtitle=entry.pricing_model_label,
                meta=f"Hedef kadro: {entry.target_headcount}",
                entry_date=entry.start_date,
                href="/restaurants",
            )
        )

    recent_activity.sort(
        key=lambda item: (item.entry_date is not None, item.entry_date or date.min),
        reverse=True,
    )

    return OverviewDashboardResponse(
        module="overview",
        status="active",
        hero=OverviewHeroSummary(
            active_restaurants=restaurants_dashboard.summary.active_restaurants,
            active_personnel=personnel_dashboard.summary.active_personnel,
            month_attendance_entries=attendance_dashboard.summary.month_entries,
            month_deduction_entries=deductions_dashboard.summary.this_month_entries,
        ),
        modules=[
            OverviewModuleCard(
                key="attendance",
                title="Puantaj",
                description="Gunluk operasyon kayitlari, vardiya akislari ve saha girisleri.",
                href="/attendance",
                primary_label="Bugun",
                primary_value=str(attendance_dashboard.summary.today_entries),
                secondary_label="Bu Ay",
                secondary_value=str(attendance_dashboard.summary.month_entries),
            ),
            OverviewModuleCard(
                key="personnel",
                title="Personel",
                description="Aktif kadro, roller ve saha atamalari tek yerde yonetilir.",
                href="/personnel",
                primary_label="Aktif",
                primary_value=str(personnel_dashboard.summary.active_personnel),
                secondary_label="Toplam",
                secondary_value=str(personnel_dashboard.summary.total_personnel),
            ),
            OverviewModuleCard(
                key="deductions",
                title="Kesintiler",
                description="Manual ve otomatik kesinti akislari, bordro etkisiyle birlikte izlenir.",
                href="/deductions",
                primary_label="Bu Ay",
                primary_value=str(deductions_dashboard.summary.this_month_entries),
                secondary_label="Toplam",
                secondary_value=str(deductions_dashboard.summary.total_entries),
            ),
            OverviewModuleCard(
                key="restaurants",
                title="Restoranlar",
                description="Sube, fiyat modeli ve hedef kadro yapisi merkezi olarak takip edilir.",
                href="/restaurants",
                primary_label="Aktif",
                primary_value=str(restaurants_dashboard.summary.active_restaurants),
                secondary_label="Sabit Aylik",
                secondary_value=str(restaurants_dashboard.summary.fixed_monthly_restaurants),
            ),
        ],
        recent_activity=recent_activity[:10],
    )
