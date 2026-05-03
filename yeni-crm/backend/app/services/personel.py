"""Personel servis — listeleme ve CRUD operasyonları."""
from psycopg.rows import dict_row

from app.core.database import get_connection


# Güncellenebilir kolonlar — beyaz liste
EDITABLE_COLUMNS: set[str] = {
    # Temel
    "full_name", "person_code", "role", "status", "phone", "current_plate",
    "assigned_restaurant_id", "start_date", "exit_date",
    # Hakediş & faturalandırma
    "monthly_fixed_cost",            # kuryeye ödenen aylık (sabit)
    "fixed_monthly_billing",         # restorana yansıyan sabit aylık (KDV hariç)
    # Kimlik & banka
    "tc_no", "iban", "tax_number", "tax_office",
    # Adres & acil durum
    "address", "emergency_contact_name", "emergency_contact_phone", "notes",
    # Araç
    "vehicle_type",
    "motor_purchase", "motor_purchase_sale_price",
    "motor_purchase_start_date", "motor_purchase_commitment_months",
    "motor_purchase_installment_count", "motor_purchase_monthly_amount",
    "motor_purchase_monthly_deduction",
    "motor_rental", "motor_rental_monthly_amount",
    # Muhasebe
    "accounting_type", "accountant_cost", "accounting_revenue",
    "accounting_effective_date",
    # Şirket açılışı
    "new_company_setup", "company_setup_cost", "company_setup_revenue",
    "company_setup_effective_date",
    "cost_model",
}


# Detaylı tek-kayıt için döndürülen kolonlar
DETAIL_COLUMNS = """
    id, person_code, full_name, role, status, phone, current_plate,
    assigned_restaurant_id, start_date, exit_date,
    monthly_fixed_cost, fixed_monthly_billing,
    vehicle_type,
    motor_purchase, motor_purchase_sale_price, motor_purchase_start_date,
    motor_purchase_commitment_months, motor_purchase_installment_count,
    motor_purchase_monthly_amount, motor_purchase_monthly_deduction,
    motor_rental, motor_rental_monthly_amount,
    accounting_type, accountant_cost, accounting_revenue,
    accounting_effective_date,
    new_company_setup, company_setup_cost, company_setup_revenue,
    company_setup_effective_date, cost_model,
    tc_no, iban, tax_number, tax_office,
    address, emergency_contact_name, emergency_contact_phone, notes
"""


def list_personnel(status: str | None = None) -> list[dict]:
    """Personel listesi getir."""
    sql = f"""
        SELECT {DETAIL_COLUMNS}
        FROM personnel
    """
    params: list = []
    if status:
        sql += " WHERE status = %s"
        params.append(status)
    sql += " ORDER BY person_code"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


def get_personnel(personnel_id: int) -> dict | None:
    """Tek personel detayı."""
    sql = f"SELECT {DETAIL_COLUMNS} FROM personnel WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (personnel_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def update_personnel(personnel_id: int, fields: dict) -> dict | None:
    """Personel alanlarını güncelle. Sadece beyaz listedeki alanlar."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe:
        return get_personnel(personnel_id)

    set_parts = [f"{col} = %s" for col in safe.keys()]
    sql = f"""
        UPDATE personnel
        SET {', '.join(set_parts)}
        WHERE id = %s
        RETURNING id
    """
    params = list(safe.values()) + [personnel_id]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            updated = cur.fetchone()
            conn.commit()
    if not updated:
        return None
    return get_personnel(personnel_id)


def create_personnel(fields: dict) -> dict | None:
    """Yeni personel ekle."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    # En azından isim ve rol gerekli
    if not safe.get("full_name") or not safe.get("role"):
        raise ValueError("İsim ve rol zorunludur")

    cols = list(safe.keys())
    vals = list(safe.values())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"""
        INSERT INTO personnel ({', '.join(cols)})
        VALUES ({placeholders})
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vals)
            row = cur.fetchone()
            conn.commit()
    if not row:
        return None
    return get_personnel(row[0])


def page_insights(period: str) -> dict:
    """Personel sayfası için akıllı içgörüler — gerçek puantaj verisi üzerinden."""
    insights: dict = {
        "threshold_near": [],
        "capacity_gaps": [],
        "top_recovery": [],
        "pending_actions": 0,
    }

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Eşik aşımı yakın olanlar (eşikli restoranda 300-500 paket arası)
            cur.execute(
                """
                SELECT
                    p.id, p.full_name, p.person_code,
                    r.brand, r.branch,
                    r.package_threshold,
                    r.package_rate_low, r.package_rate_high,
                    COALESCE(SUM(d.package_count), 0) AS pkts
                FROM daily_entries d
                JOIN personnel p ON p.id = d.actual_personnel_id
                JOIN restaurants r ON r.id = d.restaurant_id
                WHERE LEFT(d.entry_date::text, 7) = %s
                  AND r.pricing_model = 'threshold_package'
                  AND COALESCE(p.status, 'Aktif') = 'Aktif'
                  AND COALESCE(d.worked_hours, 0) > 0
                GROUP BY p.id, p.full_name, p.person_code,
                         r.brand, r.branch, r.package_threshold,
                         r.package_rate_low, r.package_rate_high
                HAVING SUM(COALESCE(d.package_count, 0)) BETWEEN 300 AND 500
                ORDER BY pkts DESC
                LIMIT 5
                """,
                (period,),
            )
            insights["threshold_near"] = [
                {
                    "id": r["id"],
                    "full_name": r["full_name"],
                    "person_code": r["person_code"],
                    "brand": r["brand"],
                    "branch": r["branch"],
                    "packages": int(r["pkts"] or 0),
                    "threshold": int(r["package_threshold"] or 390),
                    "rate_low": float(r["package_rate_low"] or 0),
                    "rate_high": float(r["package_rate_high"] or 0),
                }
                for r in cur.fetchall()
            ]

            # 2. Eksik kapasite (target > actual)
            cur.execute(
                """
                SELECT
                    r.id, r.brand, r.branch, r.target_headcount,
                    COUNT(DISTINCT d.actual_personnel_id)
                        FILTER (WHERE COALESCE(d.worked_hours, 0) > 0) AS actual
                FROM restaurants r
                LEFT JOIN daily_entries d
                    ON d.restaurant_id = r.id
                   AND LEFT(d.entry_date::text, 7) = %s
                WHERE COALESCE(r.active, 1) = 1
                  AND COALESCE(r.target_headcount, 0) > 0
                GROUP BY r.id, r.brand, r.branch, r.target_headcount
                HAVING COUNT(DISTINCT d.actual_personnel_id)
                       FILTER (WHERE COALESCE(d.worked_hours, 0) > 0)
                       < r.target_headcount
                ORDER BY
                    (r.target_headcount -
                     COUNT(DISTINCT d.actual_personnel_id)
                       FILTER (WHERE COALESCE(d.worked_hours, 0) > 0)) DESC
                LIMIT 5
                """,
                (period,),
            )
            insights["capacity_gaps"] = [
                {
                    "id": r["id"],
                    "brand": r["brand"],
                    "branch": r["branch"],
                    "target": int(r["target_headcount"] or 0),
                    "actual": int(r["actual"] or 0),
                }
                for r in cur.fetchall()
            ]

    # 3. Top recovery — yönetim listesinden hesapla
    mgmt = management_summary(period=period)
    scored = []
    for m in mgmt:
        if m["salary"] <= 0:
            continue
        cover = m["cover_hours"] * 200 + m["cover_packages"] * 25
        pct = min(1.0, cover / m["salary"]) if m["salary"] else 0
        scored.append({**m, "recovery_pct": round(pct, 3)})
    scored.sort(key=lambda x: -x["recovery_pct"])
    insights["top_recovery"] = scored[:2]

    return insights


def top_performers(period: str, limit: int = 3) -> list[dict]:
    """Aya göre paket sayısı en yüksek personel (sahne için)."""
    sql = """
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            r.brand, r.branch,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COUNT(*) FILTER (WHERE d.worked_hours > 0) AS working_days
        FROM daily_entries d
        JOIN personnel p ON p.id = d.actual_personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE LEFT(d.entry_date::text, 7) = %s
          AND COALESCE(p.status, 'Aktif') = 'Aktif'
          AND COALESCE(d.worked_hours, 0) > 0
        GROUP BY p.id, p.full_name, p.person_code, p.role, r.brand, r.branch
        HAVING COALESCE(SUM(d.package_count), 0) > 0
        ORDER BY total_packages DESC, total_hours DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period, limit))
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "brand": r["brand"],
            "branch": r["branch"],
            "total_packages": int(r["total_packages"] or 0),
            "total_hours": float(r["total_hours"] or 0),
            "working_days": int(r["working_days"] or 0),
        })
    return out


def management_summary(period: str) -> list[dict]:
    """Yönetim & Yedek Operasyon — sabit maaşlı kişiler + ay içindeki cover."""
    sql = """
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            COALESCE(p.monthly_fixed_cost, 0) AS salary,
            COALESCE(SUM(d.worked_hours), 0) FILTER (WHERE d.worked_hours > 0) AS cover_hours,
            COALESCE(SUM(d.package_count), 0) FILTER (WHERE d.worked_hours > 0) AS cover_packages,
            COUNT(*) FILTER (WHERE d.worked_hours > 0) AS cover_days
        FROM personnel p
        LEFT JOIN daily_entries d
            ON d.actual_personnel_id = p.id
           AND LEFT(d.entry_date::text, 7) = %s
        WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
          AND (
              p.role IN ('Bölge Müdürü', 'Joker', 'Kaptan', 'Restoran Takım Şefi')
              OR COALESCE(p.monthly_fixed_cost, 0) > 0
          )
        GROUP BY p.id, p.full_name, p.person_code, p.role, p.monthly_fixed_cost
        ORDER BY salary DESC, cover_packages DESC
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "salary": float(r["salary"] or 0),
            "cover_hours": float(r["cover_hours"] or 0),
            "cover_packages": int(r["cover_packages"] or 0),
            "cover_days": int(r["cover_days"] or 0),
        })
    return out


def next_person_code(role: str) -> str:
    """Role göre bir sonraki uygun person_code'u öner.

    - Kurye → CK-K??
    - Joker → CK-J??
    - Bölge Müdürü → CK-BM??
    - Kaptan → CK-KP??
    - Restoran Takım Şefi → CK-S??
    """
    prefix_map = {
        "Kurye": "CK-K",
        "Joker": "CK-J",
        "Bölge Müdürü": "CK-BM",
        "Kaptan": "CK-KP",
        "Restoran Takım Şefi": "CK-S",
    }
    prefix = prefix_map.get(role, "CK-X")

    sql = """
        SELECT person_code FROM personnel
        WHERE person_code LIKE %s
        ORDER BY person_code DESC
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"{prefix}%",))
            row = cur.fetchone()

    if not row or not row[0]:
        return f"{prefix}01"

    # Mevcut son koddan sayısal kısmı al
    existing = row[0]
    try:
        num_part = existing[len(prefix):]
        next_num = int(num_part) + 1
        return f"{prefix}{next_num:02d}"
    except (ValueError, IndexError):
        return f"{prefix}01"
