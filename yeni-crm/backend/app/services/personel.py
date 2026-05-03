"""Personel servis — listeleme ve CRUD operasyonları."""
from psycopg.rows import dict_row

from app.core.database import get_connection


def list_personnel(status: str | None = None) -> list[dict]:
    """Personel listesi getir."""
    sql = """
        SELECT id, person_code, full_name, role, status, phone, current_plate,
               assigned_restaurant_id, start_date, exit_date
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
