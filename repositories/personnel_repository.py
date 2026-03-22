from __future__ import annotations

from infrastructure.db_engine import CompatConnection, fetch_df


def fetch_personnel_management_df(conn: CompatConnection):
    return fetch_df(
        conn,
        """
        SELECT p.*, r.brand || ' - ' || r.branch AS restoran
        FROM personnel p
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        ORDER BY p.full_name
        """,
    )


def fetch_active_restaurant_options(conn: CompatConnection) -> dict[str, int]:
    rows = conn.execute("SELECT id, brand, branch FROM restaurants WHERE active=1 ORDER BY brand, branch").fetchall()
    return {f"{r['brand']} - {r['branch']}": r['id'] for r in rows}


def fetch_person_options_map(conn: CompatConnection, active_only: bool = True) -> dict[str, int]:
    sql = "SELECT id, full_name, role, status FROM personnel"
    if active_only:
        sql += " WHERE status='Aktif'"
    sql += " ORDER BY full_name"
    rows = conn.execute(sql).fetchall()
    return {f"{r['full_name']} ({r['role']})": r['id'] for r in rows}
