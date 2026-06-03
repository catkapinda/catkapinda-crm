"""Kesinti (deduction) servisi.

Kuryelerin aylık hakedişinden düşülen tutarlar:
- Sabit kesintiler (Motor kirası/satış, ÇK Muhasebe bedeli, Tevkifat) hakediş
  motoru tarafından otomatik hesaplanır.
- Manuel kesintiler (Yakıt, Avans, HGS, Cezalar, Bakım vs.) bu tablodan gelir.
- Zimmet taksitleri `courier_equipment_issues` üzerinden otomatik üretilir
  (deduction_type='Zimmet Taksiti').
"""
from psycopg.rows import dict_row

from app.core.database import get_connection


# Manuel kesinti tipleri (UI dropdown için)
DEDUCTION_TYPES = [
    "Yakıt",
    "Avans",
    "İdari Ceza",
    "Fatura Edilemeyen Tutar",
    "HGS",
    "Trafik Cezası",
    "Bakım",
    "Ağır Bakım",
    "Kaza",
    "Elcik",
    "Telefon Tutacağı",
    "Kask",
    "Motor Hasar",
]

EDITABLE_COLUMNS: set[str] = {
    "personnel_id",
    "deduction_type",
    "amount",
    "deduction_date",
    "notes",
    "equipment_issue_id",
}


def list_deductions(
    period: str | None = None,
    personnel_id: int | None = None,
    deduction_type: str | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Kesinti listesi — JOIN'lı (kurye adı + ekipman bilgisi)."""
    sql = """
        SELECT
            d.id,
            d.personnel_id,
            d.deduction_type,
            d.amount,
            d.deduction_date,
            d.notes,
            d.equipment_issue_id,
            d.auto_source_key,
            p.full_name AS personnel_name,
            p.person_code,
            p.role,
            e.item_name AS equipment_name,
            e.installment_count AS equipment_total_installments
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        LEFT JOIN courier_equipment_issues e ON e.id = d.equipment_issue_id
        WHERE 1=1
    """
    params: list = []
    if period:
        sql += " AND LEFT(d.deduction_date::text, 7) = %s"
        params.append(period)
    if personnel_id:
        sql += " AND d.personnel_id = %s"
        params.append(personnel_id)
    if deduction_type:
        sql += " AND d.deduction_type = %s"
        params.append(deduction_type)
    sql += " ORDER BY d.deduction_date DESC, d.id DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "personnel_id": r["personnel_id"],
            "deduction_type": r["deduction_type"],
            "amount": float(r["amount"] or 0),
            "deduction_date": r["deduction_date"],
            "notes": r["notes"],
            "equipment_issue_id": r["equipment_issue_id"],
            "personnel_name": r["personnel_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "equipment_name": r["equipment_name"],
            "equipment_total_installments": r["equipment_total_installments"],
        })
    return out


def create_deduction(fields: dict) -> dict | None:
    """Yeni kesinti kaydı oluştur."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe.get("personnel_id") or not safe.get("deduction_type"):
        raise ValueError("personnel_id ve deduction_type zorunludur")
    if not safe.get("deduction_date"):
        from datetime import date
        safe["deduction_date"] = date.today().isoformat()

    cols = list(safe.keys())
    vals = list(safe.values())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"""
        INSERT INTO deductions ({', '.join(cols)})
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
    items = list_deductions(personnel_id=safe.get("personnel_id"), limit=1000)
    return next((i for i in items if i["id"] == row[0]), None)


def update_deduction(deduction_id: int, fields: dict) -> dict | None:
    """Mevcut kesintiyi güncelle (manuel kesintiler için).

    Sadece EDITABLE_COLUMNS güncellenir. Otomatik üretilen kesintiler
    (zimmet taksiti — equipment_issue_id dolu) yine düzenlenebilir ama
    UI tarafında bu tip için düzenleme gösterilmez.
    """
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe:
        # Güncellenecek alan yok → mevcut kaydı döndür
        items = list_deductions(limit=5000)
        return next((i for i in items if i["id"] == deduction_id), None)

    set_clause = ", ".join(f"{k} = %s" for k in safe.keys())
    vals = list(safe.values())
    vals.append(deduction_id)
    sql = f"UPDATE deductions SET {set_clause} WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vals)
            updated = cur.rowcount > 0
            conn.commit()
    if not updated:
        return None
    items = list_deductions(limit=5000)
    return next((i for i in items if i["id"] == deduction_id), None)


def delete_deduction(deduction_id: int) -> bool:
    """Kesintiyi sil."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM deductions WHERE id = %s", (deduction_id,))
            ok = cur.rowcount > 0
            conn.commit()
    return ok


def deductions_summary_by_personnel(period: str) -> list[dict]:
    """Personel başına aylık toplam kesinti özeti."""
    sql = """
        SELECT
            d.personnel_id,
            p.full_name,
            p.person_code,
            p.role,
            COUNT(*) AS count,
            COALESCE(SUM(d.amount), 0) AS total
        FROM deductions d
        LEFT JOIN personnel p ON p.id = d.personnel_id
        WHERE LEFT(d.deduction_date::text, 7) = %s
        GROUP BY d.personnel_id, p.full_name, p.person_code, p.role
        ORDER BY total DESC
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    return [
        {
            "personnel_id": r["personnel_id"],
            "full_name": r["full_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "count": int(r["count"] or 0),
            "total": float(r["total"] or 0),
        }
        for r in rows
    ]


def deductions_summary_by_type(period: str) -> list[dict]:
    """Tip bazında aylık toplam (KPI hero için)."""
    sql = """
        SELECT
            deduction_type,
            COUNT(*) AS count,
            COALESCE(SUM(amount), 0) AS total
        FROM deductions
        WHERE LEFT(deduction_date::text, 7) = %s
        GROUP BY deduction_type
        ORDER BY total DESC
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    return [
        {
            "deduction_type": r["deduction_type"],
            "count": int(r["count"] or 0),
            "total": float(r["total"] or 0),
        }
        for r in rows
    ]
