"""Ekipman & Zimmet servisi.

Tablolar:
- `courier_equipment_issues` — kurye-ekipman zimmet kayıtları (taksitli satış)
- `deductions` (deduction_type='Zimmet Taksiti') — taksit kesintileri

Atama yapılınca otomatik olarak `installment_count` adet `Zimmet Taksiti`
kaydı oluşturulur.
"""
from datetime import date

from psycopg.rows import dict_row

from app.core.database import get_connection


# Zimmet edilebilir ekipman kataloğu
EQUIPMENT_CATALOG = [
    {"name": "Korumalı Mont", "category": "Giyim", "default_price": 4500},
    {"name": "Yağmurluk", "category": "Giyim", "default_price": 1200},
    {"name": "Tshirt", "category": "Giyim", "default_price": 350},
    {"name": "Polar", "category": "Giyim", "default_price": 1500},
    {"name": "Yelek", "category": "Giyim", "default_price": 1800},
    {"name": "Göğüs Çantası", "category": "Aksesuar", "default_price": 1600},
    {"name": "Box", "category": "Donanım", "default_price": 3200},
    {"name": "Punch", "category": "Donanım", "default_price": 2000},
]


EDITABLE_COLUMNS: set[str] = {
    "personnel_id",
    "item_name",
    "quantity",
    "unit_cost",
    "unit_sale_price",
    "vat_rate",
    "sale_type",
    "installment_count",
    "issue_date",
    "notes",
}


def list_assignments(
    personnel_id: int | None = None,
    period: str | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Tüm zimmet atamaları (kurye adı JOIN'lı)."""
    sql = """
        SELECT
            e.id,
            e.personnel_id,
            e.item_name,
            e.quantity,
            e.unit_cost,
            e.unit_sale_price,
            e.vat_rate,
            e.sale_type,
            e.installment_count,
            e.issue_date,
            e.notes,
            p.full_name AS personnel_name,
            p.person_code,
            p.role,
            (SELECT COUNT(*) FROM deductions d
                WHERE d.equipment_issue_id = e.id) AS taksit_kesilen
        FROM courier_equipment_issues e
        LEFT JOIN personnel p ON p.id = e.personnel_id
        WHERE 1=1
    """
    params: list = []
    if personnel_id:
        sql += " AND e.personnel_id = %s"
        params.append(personnel_id)
    if period:
        sql += " AND LEFT(e.issue_date::text, 7) = %s"
        params.append(period)
    sql += " ORDER BY e.issue_date DESC, e.id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    out: list[dict] = []
    for r in rows:
        total = float(r["unit_sale_price"] or 0) * int(r["quantity"] or 1)
        installment = int(r["installment_count"] or 1) or 1
        per_installment = total / installment
        out.append({
            "id": r["id"],
            "personnel_id": r["personnel_id"],
            "item_name": r["item_name"],
            "quantity": int(r["quantity"] or 0),
            "unit_cost": float(r["unit_cost"] or 0),
            "unit_sale_price": float(r["unit_sale_price"] or 0),
            "vat_rate": float(r["vat_rate"] or 0),
            "sale_type": r["sale_type"],
            "installment_count": installment,
            "issue_date": r["issue_date"],
            "notes": r["notes"],
            "personnel_name": r["personnel_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "total_amount": round(total, 2),
            "per_installment": round(per_installment, 2),
            "taksit_kesilen": int(r["taksit_kesilen"] or 0),
        })
    return out


def create_assignment(fields: dict) -> dict | None:
    """Yeni zimmet ataması + ay ay taksit kesintilerini otomatik oluştur."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe.get("personnel_id") or not safe.get("item_name"):
        raise ValueError("personnel_id ve item_name zorunludur")
    if not safe.get("quantity"):
        safe["quantity"] = 1
    if not safe.get("installment_count"):
        safe["installment_count"] = 1
    if not safe.get("sale_type"):
        safe["sale_type"] = "Satış"
    if not safe.get("issue_date"):
        safe["issue_date"] = date.today().isoformat()

    cols = list(safe.keys())
    vals = list(safe.values())
    placeholders = ", ".join(["%s"] * len(cols))
    sql_insert = f"""
        INSERT INTO courier_equipment_issues ({', '.join(cols)})
        VALUES ({placeholders})
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_insert, vals)
            row = cur.fetchone()
            if not row:
                return None
            issue_id = row[0]

            # Otomatik taksit kesintilerini oluştur
            qty = int(safe.get("quantity") or 1)
            unit_price = float(safe.get("unit_sale_price") or 0)
            total = qty * unit_price
            inst = int(safe.get("installment_count") or 1) or 1
            per = round(total / inst, 2)

            issue_date_str = safe.get("issue_date")
            if isinstance(issue_date_str, str):
                y, m, d = (int(x) for x in issue_date_str.split("-"))
            else:
                today = date.today()
                y, m, d = today.year, today.month, today.day

            for i in range(inst):
                # i. ay sonunda kes
                target_m = m + i
                target_y = y + (target_m - 1) // 12
                target_m = ((target_m - 1) % 12) + 1
                # ay sonu (basit: 28)
                target_date = f"{target_y:04d}-{target_m:02d}-28"
                cur.execute(
                    """
                    INSERT INTO deductions
                        (personnel_id, deduction_type, amount,
                         deduction_date, notes, equipment_issue_id)
                    VALUES (%s, 'Zimmet Taksiti', %s, %s, %s, %s)
                    """,
                    (
                        safe["personnel_id"],
                        per,
                        target_date,
                        f"{safe['item_name']} {i+1}/{inst}",
                        issue_id,
                    ),
                )
            conn.commit()

    items = list_assignments(personnel_id=safe.get("personnel_id"), limit=1000)
    return next((it for it in items if it["id"] == issue_id), None)
