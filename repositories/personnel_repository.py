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


def fetch_person_code_values(conn: CompatConnection, prefix: str, exclude_id: int | None = None) -> list[str]:
    sql = "SELECT person_code FROM personnel WHERE person_code LIKE ?"
    params: list[object] = [f"CK-{prefix}%"]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [str(row["person_code"] or "") for row in rows]
