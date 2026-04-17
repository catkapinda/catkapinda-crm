from __future__ import annotations

from datetime import date, timedelta

import psycopg

from app.schemas.overview import (
    OverviewActivityItem,
    OverviewActionAlert,
    OverviewBrandSummaryEntry,
    OverviewDashboardResponse,
    OverviewDailyTrendPoint,
    OverviewFinanceHighlight,
    OverviewFinanceSummary,
    OverviewHeroSummary,
    OverviewHygieneEntry,
    OverviewHygieneSummary,
    OverviewJokerUsageEntry,
    OverviewModuleCard,
    OverviewOperationsSummary,
    OverviewRestaurantLoadEntry,
)
from app.services.attendance import build_attendance_dashboard
from app.services.deductions import build_deductions_dashboard
from app.services.personnel import build_personnel_dashboard
from app.services.reports import build_reports_dashboard
from app.services.restaurants import build_restaurants_dashboard


def _format_currency(value: float) -> str:
    return f"{float(value or 0):,.0f} TL"


def _format_number(value: float) -> str:
    return f"{float(value or 0):,.0f}"


def _build_finance_summary(
    conn: psycopg.Connection,
) -> OverviewFinanceSummary:
    reports_dashboard = build_reports_dashboard(conn, limit=24)
    summary = reports_dashboard.summary
    if summary is None:
        return OverviewFinanceSummary(
            selected_month=None,
            total_revenue=0.0,
            gross_profit=0.0,
            total_personnel_cost=0.0,
            side_income_net=0.0,
            top_restaurants=[],
            risk_restaurants=[],
        )

    top_restaurants = [
        OverviewFinanceHighlight(
            label=str(entry.restaurant or "-"),
            value=_format_currency(entry.gross_invoice),
        )
        for entry in reports_dashboard.top_restaurants[:5]
    ]

    risk_restaurants = [
        OverviewFinanceHighlight(
            label=str(entry.restaurant or "-"),
            value=_format_currency(entry.gross_invoice),
        )
        for entry in sorted(
            reports_dashboard.invoice_entries,
            key=lambda entry: float(entry.gross_invoice or 0),
        )[:5]
    ]

    return OverviewFinanceSummary(
        selected_month=summary.selected_month,
        total_revenue=float(summary.total_revenue or 0),
        gross_profit=float(summary.gross_profit or 0),
        total_personnel_cost=float(summary.total_personnel_cost or 0),
        side_income_net=float(summary.side_income_net or 0),
        top_restaurants=top_restaurants,
        risk_restaurants=risk_restaurants,
    )


def _build_hygiene_summary(conn: psycopg.Connection) -> OverviewHygieneSummary:
    personnel_rows = conn.execute(
        """
        SELECT
            COALESCE(person_code, '') AS person_code,
            COALESCE(full_name, '') AS full_name,
            COALESCE(role, '') AS role,
            COALESCE(phone, '') AS phone,
            start_date,
            assigned_restaurant_id,
            COALESCE(status, '') AS status,
            COALESCE(vehicle_type, '') AS vehicle_type,
            COALESCE(motor_rental, '') AS motor_rental,
            COALESCE(motor_purchase, '') AS motor_purchase,
            COALESCE(current_plate, '') AS current_plate
        FROM personnel
        ORDER BY full_name, person_code
        """
    ).fetchall()
    restaurant_rows = conn.execute(
        """
        SELECT
            COALESCE(brand, '') AS brand,
            COALESCE(branch, '') AS branch,
            COALESCE(contact_name, '') AS contact_name,
            COALESCE(target_headcount, 0) AS target_headcount,
            COALESCE(address, '') AS address
        FROM restaurants
        ORDER BY brand, branch
        """
    ).fetchall()

    personnel_samples: list[OverviewHygieneEntry] = []
    restaurant_samples: list[OverviewHygieneEntry] = []
    missing_personnel_cards = 0
    missing_restaurant_cards = 0

    for row in personnel_rows:
        row_data = dict(row)
        missing_fields: list[str] = []
        if not str(row_data.get("phone") or "").strip():
            missing_fields.append("Telefon")
        if not row_data.get("start_date"):
            missing_fields.append("İşe giriş")
        if str(row_data.get("status") or "").strip() == "Aktif" and int(row_data.get("assigned_restaurant_id") or 0) <= 0:
            missing_fields.append("Şube")
        if (
            str(row_data.get("vehicle_type") or "").strip() == "Çat Kapında"
            and (
                str(row_data.get("motor_rental") or "").strip() == "Evet"
                or str(row_data.get("motor_purchase") or "").strip() == "Evet"
            )
            and not str(row_data.get("current_plate") or "").strip()
        ):
            missing_fields.append("Plaka")
        if missing_fields:
            missing_personnel_cards += 1
            if len(personnel_samples) < 5:
                personnel_samples.append(
                    OverviewHygieneEntry(
                        title=str(row_data.get("full_name") or row_data.get("person_code") or "-"),
                        subtitle=", ".join(missing_fields),
                    )
                )

    for row in restaurant_rows:
        row_data = dict(row)
        missing_fields: list[str] = []
        if not str(row_data.get("contact_name") or "").strip():
            missing_fields.append("Kontak")
        if float(row_data.get("target_headcount") or 0) <= 0:
            missing_fields.append("Hedef kadro")
        if not str(row_data.get("address") or "").strip():
            missing_fields.append("Adres")
        if missing_fields:
            missing_restaurant_cards += 1
            if len(restaurant_samples) < 5:
                restaurant_samples.append(
                    OverviewHygieneEntry(
                        title=" - ".join(
                            part for part in [str(row_data.get("brand") or "").strip(), str(row_data.get("branch") or "").strip()] if part
                        )
                        or "-",
                        subtitle=", ".join(missing_fields),
                    )
                )

    return OverviewHygieneSummary(
        missing_personnel_cards=missing_personnel_cards,
        missing_restaurant_cards=missing_restaurant_cards,
        personnel_samples=personnel_samples,
        restaurant_samples=restaurant_samples,
    )


def _build_operations_summary(
    conn: psycopg.Connection,
    *,
    reference_date: date,
    selected_month: str | None,
) -> OverviewOperationsSummary:
    month_key = selected_month or reference_date.strftime("%Y-%m")
    missing_attendance_rows = conn.execute(
        """
        SELECT
            COALESCE(r.brand, '') AS brand,
            COALESCE(r.branch, '') AS branch
        FROM restaurants r
        WHERE COALESCE(r.active, TRUE) = TRUE
          AND NOT EXISTS (
            SELECT 1
            FROM daily_entries d
            WHERE d.restaurant_id = r.id
              AND d.entry_date = %s
          )
        ORDER BY r.brand, r.branch
        LIMIT 5
        """,
        (reference_date,),
    ).fetchall()
    under_target_rows = conn.execute(
        """
        SELECT
            COALESCE(r.brand, '') AS brand,
            COALESCE(r.branch, '') AS branch,
            COALESCE(r.target_headcount, 0) AS target_headcount,
            COALESCE(SUM(CASE WHEN p.status = 'Aktif' THEN 1 ELSE 0 END), 0) AS active_personnel
        FROM restaurants r
        LEFT JOIN personnel p ON p.assigned_restaurant_id = r.id
        WHERE COALESCE(r.active, TRUE) = TRUE
        GROUP BY r.id, r.brand, r.branch, r.target_headcount
        HAVING COALESCE(r.target_headcount, 0) > COALESCE(SUM(CASE WHEN p.status = 'Aktif' THEN 1 ELSE 0 END), 0)
        ORDER BY (COALESCE(r.target_headcount, 0) - COALESCE(SUM(CASE WHEN p.status = 'Aktif' THEN 1 ELSE 0 END), 0)) DESC, r.brand, r.branch
        LIMIT 5
        """
    ).fetchall()
    joker_usage_rows = conn.execute(
        """
        SELECT
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COUNT(*) AS joker_count,
            COALESCE(SUM(d.package_count), 0) AS package_count
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel ap ON ap.id = d.actual_personnel_id
        WHERE d.entry_date = %s
          AND (
            COALESCE(d.coverage_type, '') = 'Joker'
            OR COALESCE(ap.role, '') = 'Joker'
          )
        GROUP BY restaurant
        ORDER BY joker_count DESC, package_count DESC, restaurant
        LIMIT 5
        """,
        (reference_date,),
    ).fetchall()
    trend_start = reference_date - timedelta(days=13)
    daily_trend_rows = conn.execute(
        """
        SELECT
            entry_date,
            COALESCE(SUM(package_count), 0) AS total_packages,
            COALESCE(SUM(worked_hours), 0) AS total_hours
        FROM daily_entries
        WHERE entry_date BETWEEN %s AND %s
        GROUP BY entry_date
        ORDER BY entry_date
        """,
        (trend_start, reference_date),
    ).fetchall()
    top_restaurant_rows = conn.execute(
        """
        SELECT
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours
        FROM daily_entries d
        JOIN restaurants r ON r.id = d.restaurant_id
        WHERE substr(COALESCE(d.entry_date, ''), 1, 7) = %s
        GROUP BY restaurant
        ORDER BY total_packages DESC, total_hours DESC, restaurant
        LIMIT 6
        """,
        (month_key,),
    ).fetchall()
    restaurant_profit_rows = conn.execute(
        """
        SELECT
            r.id,
            COALESCE(r.brand || ' - ' || r.branch, '-') AS restaurant,
            COALESCE((
                SELECT SUM(d.monthly_invoice_amount)
                FROM daily_entries d
                WHERE d.restaurant_id = r.id
                  AND substr(COALESCE(d.entry_date, ''), 1, 7) = %s
            ), 0) AS gross_invoice,
            COALESCE((
                SELECT SUM(COALESCE(p.monthly_fixed_cost, 0))
                FROM personnel p
                WHERE p.assigned_restaurant_id = r.id
                  AND COALESCE(p.status, '') = 'Aktif'
            ), 0) AS personnel_cost
        FROM restaurants r
        WHERE COALESCE(r.active, TRUE) = TRUE
        ORDER BY restaurant
        """,
        (month_key,),
    ).fetchall()
    brand_rows = conn.execute(
        """
        WITH invoice AS (
            SELECT
                COALESCE(r.brand, '-') AS brand,
                COUNT(DISTINCT d.restaurant_id) AS restaurant_count,
                COALESCE(SUM(d.package_count), 0) AS total_packages,
                COALESCE(SUM(d.worked_hours), 0) AS total_hours,
                COALESCE(SUM(d.monthly_invoice_amount), 0) AS gross_invoice
            FROM daily_entries d
            JOIN restaurants r ON r.id = d.restaurant_id
            WHERE substr(COALESCE(d.entry_date, ''), 1, 7) = %s
            GROUP BY COALESCE(r.brand, '-')
        ),
        personnel_cost AS (
            SELECT
                COALESCE(r.brand, '-') AS brand,
                COALESCE(SUM(CASE WHEN p.status = 'Aktif' THEN COALESCE(p.monthly_fixed_cost, 0) ELSE 0 END), 0) AS personnel_cost
            FROM restaurants r
            LEFT JOIN personnel p ON p.assigned_restaurant_id = r.id
            WHERE COALESCE(r.active, TRUE) = TRUE
            GROUP BY COALESCE(r.brand, '-')
        )
        SELECT
            invoice.brand,
            invoice.restaurant_count,
            invoice.total_packages,
            invoice.total_hours,
            invoice.gross_invoice,
            COALESCE(personnel_cost.personnel_cost, 0) AS personnel_cost
        FROM invoice
        LEFT JOIN personnel_cost ON personnel_cost.brand = invoice.brand
        ORDER BY invoice.gross_invoice DESC, invoice.brand
        LIMIT 8
        """,
        (month_key,),
    ).fetchall()
    shared_operation_row = conn.execute(
        """
        SELECT
            COALESCE(SUM(COALESCE(monthly_fixed_cost, 0)), 0) AS shared_operation_total
        FROM personnel
        WHERE COALESCE(status, '') = 'Aktif'
          AND COALESCE(assigned_restaurant_id, 0) <= 0
        """
    ).fetchone()

    action_alerts: list[OverviewActionAlert] = []
    for row in missing_attendance_rows:
        action_alerts.append(
            OverviewActionAlert(
                tone="critical",
                badge="Bugün",
                title=" - ".join(part for part in [str(row["brand"] or "").strip(), str(row["branch"] or "").strip()] if part) or "-",
                detail="Bugün puantaj bekleniyor. Günlük kayıt henüz girilmedi.",
            )
        )
    for row in under_target_rows:
        gap = int(row["target_headcount"] or 0) - int(row["active_personnel"] or 0)
        action_alerts.append(
            OverviewActionAlert(
                tone="critical" if gap >= 2 else "warning",
                badge="Kadro",
                title=" - ".join(part for part in [str(row["brand"] or "").strip(), str(row["branch"] or "").strip()] if part) or "-",
                detail=f"Hedef kadronun altında. Açık kadro: {gap}.",
            )
        )
    for row in joker_usage_rows:
        action_alerts.append(
            OverviewActionAlert(
                tone="warning",
                badge="Joker",
                title=str(row["restaurant"] or "-"),
                detail=f"Bugün {int(row['joker_count'] or 0)} joker kullanıldı. Paket yükü: {_format_number(float(row['package_count'] or 0))}.",
            )
        )

    brand_summary: list[OverviewBrandSummaryEntry] = []
    for row in brand_rows:
        operation_gap = float(row["gross_invoice"] or 0) - float(row["personnel_cost"] or 0)
        if operation_gap < 0:
            status = "Riskte"
        elif operation_gap < 25000:
            status = "Dengede"
        else:
            status = "Sağlam"
        brand_summary.append(
            OverviewBrandSummaryEntry(
                brand=str(row["brand"] or "-"),
                restaurant_count=int(row["restaurant_count"] or 0),
                total_packages=float(row["total_packages"] or 0),
                total_hours=float(row["total_hours"] or 0),
                gross_invoice=float(row["gross_invoice"] or 0),
                operation_gap=operation_gap,
                status=status,
            )
        )

    profitable_restaurant_count = 0
    risky_restaurant_count = 0
    for row in restaurant_profit_rows:
        operation_gap = float(row["gross_invoice"] or 0) - float(row["personnel_cost"] or 0)
        if operation_gap >= 0:
            profitable_restaurant_count += 1
        else:
            risky_restaurant_count += 1

    critical_signal_count = (
        len(missing_attendance_rows)
        + len(under_target_rows)
        + len(joker_usage_rows)
    )

    shared_operation_total = 0.0
    if shared_operation_row is not None:
        shared_operation_total = float(shared_operation_row["shared_operation_total"] or 0)

    return OverviewOperationsSummary(
        missing_attendance_count=len(missing_attendance_rows),
        under_target_count=len(under_target_rows),
        joker_usage_count=len(joker_usage_rows),
        critical_signal_count=critical_signal_count,
        profitable_restaurant_count=profitable_restaurant_count,
        risky_restaurant_count=risky_restaurant_count,
        shared_operation_total=shared_operation_total,
        action_alerts=action_alerts[:8],
        brand_summary=brand_summary,
        daily_trend=[
            OverviewDailyTrendPoint(
                entry_date=row["entry_date"],
                total_packages=float(row["total_packages"] or 0),
                total_hours=float(row["total_hours"] or 0),
            )
            for row in daily_trend_rows
            if row["entry_date"]
        ],
        top_restaurants=[
            OverviewRestaurantLoadEntry(
                restaurant=str(row["restaurant"] or "-"),
                total_packages=float(row["total_packages"] or 0),
                total_hours=float(row["total_hours"] or 0),
            )
            for row in top_restaurant_rows
        ],
        joker_restaurants=[
            OverviewJokerUsageEntry(
                restaurant=str(row["restaurant"] or "-"),
                joker_count=int(row["joker_count"] or 0),
                total_packages=float(row["package_count"] or 0),
            )
            for row in joker_usage_rows
        ],
    )


def build_overview_dashboard(
    conn: psycopg.Connection,
    *,
    reference_date: date,
) -> OverviewDashboardResponse:
    attendance_dashboard = build_attendance_dashboard(conn, reference_date=reference_date, limit=6)
    personnel_dashboard = build_personnel_dashboard(conn, limit=6)
    deductions_dashboard = build_deductions_dashboard(conn, reference_date=reference_date, limit=6)
    restaurants_dashboard = build_restaurants_dashboard(conn, limit=6)
    finance_summary = _build_finance_summary(conn)
    hygiene_summary = _build_hygiene_summary(conn)
    operations_summary = _build_operations_summary(
        conn,
        reference_date=reference_date,
        selected_month=finance_summary.selected_month,
    )

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
        finance=finance_summary,
        hygiene=hygiene_summary,
        operations=operations_summary,
        modules=[
            OverviewModuleCard(
                key="attendance",
                title="Puantaj",
                description="Günlük operasyon kayıtları, vardiya akışları ve saha girişleri.",
                href="/attendance",
                primary_label="Bugün",
                primary_value=str(attendance_dashboard.summary.today_entries),
                secondary_label="Bu Ay",
                secondary_value=str(attendance_dashboard.summary.month_entries),
            ),
            OverviewModuleCard(
                key="personnel",
                title="Personel",
                description="Aktif kadro, roller ve saha atamaları tek yerde yönetilir.",
                href="/personnel",
                primary_label="Aktif",
                primary_value=str(personnel_dashboard.summary.active_personnel),
                secondary_label="Toplam",
                secondary_value=str(personnel_dashboard.summary.total_personnel),
            ),
            OverviewModuleCard(
                key="deductions",
                title="Kesintiler",
                description="Manuel ve otomatik kesinti akışları, bordro etkisiyle birlikte izlenir.",
                href="/deductions",
                primary_label="Bu Ay",
                primary_value=str(deductions_dashboard.summary.this_month_entries),
                secondary_label="Toplam",
                secondary_value=str(deductions_dashboard.summary.total_entries),
            ),
            OverviewModuleCard(
                key="restaurants",
                title="Restoranlar",
                description="Şube, fiyat modeli ve hedef kadro yapısı merkezi olarak takip edilir.",
                href="/restaurants",
                primary_label="Aktif",
                primary_value=str(restaurants_dashboard.summary.active_restaurants),
                secondary_label="Sabit Aylık",
                secondary_value=str(restaurants_dashboard.summary.fixed_monthly_restaurants),
            ),
        ],
        recent_activity=recent_activity[:10],
    )
