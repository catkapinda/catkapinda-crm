from datetime import date

from app.repositories import equipment as equipment_repository
from app.repositories import personnel as personnel_repository
from app.repositories import purchases as purchases_repository
from app.repositories import restaurants as restaurants_repository


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


def test_plate_history_queries_use_schema_agnostic_active_and_dates():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()
    active_conn = RecordingConnection()

    personnel_repository.fetch_recent_plate_history_records(fetch_conn, limit=5)
    personnel_repository.count_active_plate_history_records(count_conn)
    personnel_repository.fetch_active_plate_history_record(active_conn, person_id=7)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    active_sql, active_params = active_conn.calls[0]
    assert "NULLIF(CAST(ph.start_date AS TEXT), '')" in fetch_sql
    assert "NULLIF(CAST(ph.end_date AS TEXT), '')" in fetch_sql
    assert "CAST(ph.active AS TEXT)" in fetch_sql
    assert fetch_params == (5,)
    assert "CAST(active AS TEXT)" in count_sql
    assert "NULLIF(CAST(start_date AS TEXT), '')" in active_sql
    assert "CAST(active AS TEXT)" in active_sql
    assert active_params == (7,)


def test_purchase_queries_normalize_text_dates_and_text_fields():
    summary_conn = RecordingConnection()
    list_conn = RecordingConnection()
    count_conn = RecordingConnection()

    purchases_repository.fetch_purchase_summary(summary_conn, reference_date=date(2026, 4, 18))
    purchases_repository.fetch_purchase_management_records(list_conn, limit=5)
    purchases_repository.count_purchase_management_records(count_conn)

    summary_sql, _ = summary_conn.calls[0]
    list_sql, list_params = list_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    assert "SUBSTR(COALESCE(CAST(purchase_date AS TEXT), ''), 1, 10)" in summary_sql
    assert "SUBSTR(CAST(%s::date AS TEXT), 1, 7)" in summary_sql
    assert "AS purchase_date" in list_sql
    assert "CAST(supplier AS TEXT)" in list_sql
    assert "CAST(invoice_no AS TEXT)" in list_sql
    assert list_params[-1] == 5
    assert "CAST(notes AS TEXT)" in count_sql


def test_restaurant_management_queries_cast_text_like_fields():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()

    restaurants_repository.fetch_restaurant_management_records(fetch_conn, limit=5)
    restaurants_repository.count_restaurant_management_records(count_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    assert "CAST(r.contact_phone AS TEXT)" in fetch_sql
    assert "CAST(r.tax_number AS TEXT)" in fetch_sql
    assert "CAST(r.address AS TEXT)" in fetch_sql
    assert "CAST(r.contact_phone AS TEXT)" in count_sql
    assert fetch_params[-1] == 5


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
