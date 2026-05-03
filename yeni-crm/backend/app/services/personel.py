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
