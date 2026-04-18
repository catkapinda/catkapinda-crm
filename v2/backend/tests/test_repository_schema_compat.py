from app.repositories import equipment as equipment_repository
from app.repositories import personnel as personnel_repository


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class RecordingConnection:
    def __init__(self):
        self.calls: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeCursor()


def test_fetch_personnel_restaurants_uses_schema_agnostic_active_filter():
    conn = RecordingConnection()

    personnel_repository.fetch_personnel_restaurants(conn)

    sql, _ = conn.calls[0]
    assert "CAST(active AS TEXT)" in sql
    assert "IN ('1', 't', 'true')" in sql


def test_fetch_recent_role_history_records_normalizes_text_dates():
    conn = RecordingConnection()

    personnel_repository.fetch_recent_role_history_records(conn, limit=5)

    sql, params = conn.calls[0]
    assert "NULLIF(CAST(prh.effective_date AS TEXT), '')" in sql
    assert "SUBSTR(CAST(prh.changed_at AS TEXT), 1, 10)" in sql
    assert params == (5,)


def test_fetch_recent_vehicle_history_records_normalizes_text_dates():
    conn = RecordingConnection()

    personnel_repository.fetch_recent_vehicle_history_records(conn, limit=5)

    sql, params = conn.calls[0]
    assert "NULLIF(CAST(pvh.effective_date AS TEXT), '')" in sql
    assert "SUBSTR(CAST(pvh.changed_at AS TEXT), 1, 10)" in sql
    assert params == (5,)


def test_fetch_equipment_issue_management_records_casts_optional_filters():
    conn = RecordingConnection()

    equipment_repository.fetch_equipment_issue_management_records(conn, limit=5)

    sql, params = conn.calls[0]
    assert "%s::bigint IS NULL OR i.personnel_id = %s::bigint" in sql
    assert "%s::text IS NULL OR i.item_name = %s::text" in sql
    assert "%s::text IS NULL" in sql
    assert params[-1] == 5


def test_count_equipment_issue_management_records_casts_optional_filters():
    conn = RecordingConnection()

    equipment_repository.count_equipment_issue_management_records(conn)

    sql, _ = conn.calls[0]
    assert "%s::bigint IS NULL OR i.personnel_id = %s::bigint" in sql
    assert "%s::text IS NULL OR i.item_name = %s::text" in sql
    assert "%s::text IS NULL" in sql


def test_box_return_queries_cast_optional_filters():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()

    equipment_repository.fetch_box_return_management_records(fetch_conn, limit=5)
    equipment_repository.count_box_return_management_records(count_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    assert "%s::bigint IS NULL OR b.personnel_id = %s::bigint" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert fetch_params[-1] == 5
    assert "%s::bigint IS NULL OR b.personnel_id = %s::bigint" in count_sql
    assert "%s::text IS NULL" in count_sql
