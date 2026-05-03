"""Talep servisi — Avans / Motor Değişikliği / Muhasebe Değişimi.

Kuryeler ya da yönetim adına talep oluşturulur, sonra onaylanır/reddedilir.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection


REQUEST_TYPES = {
    "Avans",
    "Motor Değişikliği",
    "Muhasebe Değişimi",
}

STATUSES = {"Beklemede", "Onaylandı", "Reddedildi"}


def list_requests(
    status: str | None = None,
    request_type: str | None = None,
    personnel_id: int | None = None,
) -> list[dict]:
    """Talepleri listele — opsiyonel filtreler."""
    sql = """
        SELECT
            r.id,
            r.personnel_id,
            r.request_type,
            r.amount,
            r.reason,
            r.status,
            r.decision_notes,
            r.requested_at,
            r.decided_at,
            r.decided_by,
            p.full_name AS personnel_name,
            p.person_code,
            p.role AS personnel_role,
            p.assigned_restaurant_id,
            rest.brand AS rest_brand,
            rest.branch AS rest_branch
        FROM courier_requests r
        LEFT JOIN personnel p ON p.id = r.personnel_id
        LEFT JOIN restaurants rest ON rest.id = p.assigned_restaurant_id
        WHERE 1 = 1
    """
    params: list = []
    if status:
        sql += " AND r.status = %s"
        params.append(status)
    if request_type:
        sql += " AND r.request_type = %s"
        params.append(request_type)
    if personnel_id is not None:
        sql += " AND r.personnel_id = %s"
        params.append(personnel_id)
    sql += " ORDER BY r.requested_at DESC NULLS LAST, r.id DESC"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [_serialize(r) for r in rows]


def get_request(request_id: int) -> dict | None:
    rows = list_requests()
    for r in rows:
        if r["id"] == request_id:
            return r
    return None


def create_request(fields: dict) -> dict | None:
    """Yeni talep oluştur. fields: personnel_id, request_type, amount?, reason?"""
    personnel_id = fields.get("personnel_id")
    request_type = (fields.get("request_type") or "").strip()
    if not personnel_id:
        raise ValueError("personnel_id zorunludur")
    if request_type not in REQUEST_TYPES:
        raise ValueError(
            f"request_type geçersiz: {request_type}. "
            f"Beklenen: {', '.join(sorted(REQUEST_TYPES))}"
        )

    amount = float(fields.get("amount") or 0)
    reason = (fields.get("reason") or "").strip() or None

    sql = """
        INSERT INTO courier_requests (personnel_id, request_type, amount, reason, status)
        VALUES (%s, %s, %s, %s, 'Beklemede')
        RETURNING id
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (personnel_id, request_type, amount, reason))
            row = cur.fetchone()
            conn.commit()
    if not row:
        return None
    return get_request(row[0])


def decide_request(
    request_id: int,
    status: str,
    decided_by: str | None = None,
    decision_notes: str | None = None,
) -> dict | None:
    """Talebi onayla / reddet."""
    if status not in {"Onaylandı", "Reddedildi"}:
        raise ValueError(f"Geçersiz karar: {status}")
    sql = """
        UPDATE courier_requests
        SET status = %s,
            decided_by = %s,
            decision_notes = %s,
            decided_at = now()
        WHERE id = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (status, decided_by, decision_notes, request_id))
            conn.commit()
    return get_request(request_id)


def delete_request(request_id: int) -> bool:
    sql = "DELETE FROM courier_requests WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (request_id,))
            ok = cur.rowcount > 0
            conn.commit()
    return ok


def request_counts() -> dict:
    """Status başına sayım — sidebar badge için."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT status, COUNT(*) AS n
                FROM courier_requests
                GROUP BY status
            """)
            rows = cur.fetchall()
    out = {"Beklemede": 0, "Onaylandı": 0, "Reddedildi": 0, "total": 0}
    for r in rows:
        s = r["status"]
        n = int(r["n"] or 0)
        out["total"] += n
        if s in out:
            out[s] = n
    return out


def _serialize(r: dict) -> dict:
    """Datetime'ları ISO string'e çevir."""
    return {
        "id": r["id"],
        "personnel_id": r["personnel_id"],
        "personnel_name": r.get("personnel_name"),
        "person_code": r.get("person_code"),
        "personnel_role": r.get("personnel_role"),
        "rest_brand": r.get("rest_brand"),
        "rest_branch": r.get("rest_branch"),
        "request_type": r["request_type"],
        "amount": float(r["amount"] or 0),
        "reason": r.get("reason"),
        "status": r["status"],
        "decision_notes": r.get("decision_notes"),
        "requested_at": r["requested_at"].isoformat() if r.get("requested_at") else None,
        "decided_at": r["decided_at"].isoformat() if r.get("decided_at") else None,
        "decided_by": r.get("decided_by"),
    }
