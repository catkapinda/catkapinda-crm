from datetime import date

from app.repositories import attendance as attendance_repository
from app.repositories import audit as audit_repository
from app.repositories import deductions as deductions_repository
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
    def __init__(self, rows=None):
        self.calls: list[tuple[str, tuple | None]] = []
        self._rows = rows or []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeCursor(self._rows)


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
    assert "%s::text IS NULL OR COALESCE(CAST(item_name AS TEXT), '') = %s::text" in list_sql
    assert "%s::text IS NULL" in list_sql
    assert "CAST(supplier AS TEXT)" in list_sql
    assert "CAST(invoice_no AS TEXT)" in list_sql
    assert list_params[-1] == 5
    assert "%s::text IS NULL OR COALESCE(CAST(item_name AS TEXT), '') = %s::text" in count_sql
    assert "CAST(notes AS TEXT)" in count_sql


def test_restaurant_management_queries_cast_text_like_fields():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()

    restaurants_repository.fetch_restaurant_management_records(fetch_conn, limit=5)
    restaurants_repository.count_restaurant_management_records(count_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    assert "%s::text IS NULL OR COALESCE(CAST(r.pricing_model AS TEXT), '') = %s::text" in fetch_sql
    assert "%s::boolean IS NULL OR COALESCE(LOWER(CAST(r.active AS TEXT)), 'true') IN ('1', 't', 'true') = %s::boolean" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert "CAST(r.contact_phone AS TEXT)" in fetch_sql
    assert "CAST(r.tax_number AS TEXT)" in fetch_sql
    assert "CAST(r.address AS TEXT)" in fetch_sql
    assert "%s::text IS NULL OR COALESCE(CAST(r.pricing_model AS TEXT), '') = %s::text" in count_sql
    assert "CAST(r.contact_phone AS TEXT)" in count_sql
    assert fetch_params[-1] == 5


def test_personnel_management_queries_cast_optional_filters():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()
    code_conn = RecordingConnection()

    personnel_repository.fetch_personnel_management_records(fetch_conn, limit=5)
    personnel_repository.count_personnel_management_records(count_conn)
    personnel_repository.fetch_person_code_values(code_conn, "K")

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    code_sql, code_params = code_conn.calls[0]
    assert "%s::bigint IS NULL OR p.assigned_restaurant_id = %s::bigint" in fetch_sql
    assert "%s::text IS NULL OR COALESCE(CAST(p.role AS TEXT), '') = %s::text" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert "%s::bigint IS NULL OR p.assigned_restaurant_id = %s::bigint" in count_sql
    assert "%s::text IS NULL OR COALESCE(CAST(p.role AS TEXT), '') = %s::text" in count_sql
    assert "%s::bigint IS NULL OR id <> %s::bigint" in code_sql
    assert code_params[1:] == (None, None)


def test_plate_history_writes_numeric_active_values():
    close_conn = RecordingConnection()
    insert_conn = RecordingConnection(rows=[{"id": 1}])

    personnel_repository.close_active_plate_history_records(close_conn, 7, end_date="2026-04-18")
    personnel_repository.insert_plate_history_record(
        insert_conn,
        personnel_id=7,
        plate="34ABC123",
        start_date="2026-04-18",
        end_date=None,
        reason="test",
        active=True,
    )

    _, close_params = close_conn.calls[0]
    _, insert_params = insert_conn.calls[0]
    assert close_params[0] == 0
    assert insert_params[-1] == 1


def test_restaurant_writes_numeric_active_values():
    insert_conn = RecordingConnection(rows=[{"id": 1}])
    update_conn = RecordingConnection()
    toggle_conn = RecordingConnection()
    values = {
        "brand": "Brand",
        "branch": "Branch",
        "pricing_model": "hourly_plus_package",
        "hourly_rate": 1,
        "package_rate": 1,
        "package_threshold": 390,
        "package_rate_low": 1,
        "package_rate_high": 1,
        "fixed_monthly_fee": 0,
        "vat_rate": 20,
        "target_headcount": 1,
        "start_date": None,
        "end_date": None,
        "extra_headcount_request": 0,
        "extra_headcount_request_date": None,
        "reduce_headcount_request": 0,
        "reduce_headcount_request_date": None,
        "contact_name": "",
        "contact_phone": "",
        "contact_email": "",
        "company_title": "",
        "address": "",
        "tax_office": "",
        "tax_number": "",
        "active": True,
        "notes": "",
    }

    restaurants_repository.insert_restaurant_record(insert_conn, values)
    restaurants_repository.update_restaurant_record(update_conn, 9, values)
    restaurants_repository.update_restaurant_status(toggle_conn, 9, active=False)

    _, insert_params = insert_conn.calls[0]
    _, update_params = update_conn.calls[0]
    _, toggle_params = toggle_conn.calls[0]
    assert insert_params[-2] == 1
    assert update_params[-3] == 1
    assert toggle_params[0] == 0


def test_audit_queries_cast_json_and_optional_filters():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()
    options_conn = RecordingConnection()

    audit_repository.fetch_audit_management_records(fetch_conn, limit=5)
    audit_repository.count_audit_management_records(count_conn)
    audit_repository.fetch_audit_filter_options(options_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    action_sql, _ = options_conn.calls[0]
    assert "CAST(details_json AS TEXT)" in fetch_sql
    assert "%s::text IS NULL OR COALESCE(CAST(action_type AS TEXT), '') = %s::text" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert fetch_params[-1] == 5
    assert "CAST(details_json AS TEXT)" in count_sql
    assert "%s::text IS NULL OR COALESCE(CAST(actor_full_name AS TEXT), '') = %s::text" in count_sql
    assert "CAST(action_type AS TEXT)" in action_sql


def test_deduction_management_queries_cast_optional_filters():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()

    deductions_repository.fetch_deduction_management_records(fetch_conn, limit=5)
    deductions_repository.count_deduction_management_records(count_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    assert "%s::bigint IS NULL OR d.personnel_id = %s::bigint" in fetch_sql
    assert "%s::text IS NULL OR COALESCE(CAST(d.deduction_type AS TEXT), '') = %s::text" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert fetch_params[-1] == 5
    assert "%s::bigint IS NULL OR d.personnel_id = %s::bigint" in count_sql
    assert "%s::text IS NULL OR COALESCE(CAST(d.deduction_type AS TEXT), '') = %s::text" in count_sql


def test_attendance_management_queries_cast_optional_filters():
    fetch_conn = RecordingConnection()
    count_conn = RecordingConnection()
    ids_conn = RecordingConnection()

    attendance_repository.fetch_attendance_management_entries(fetch_conn, limit=5)
    attendance_repository.count_attendance_management_entries(count_conn)
    attendance_repository.fetch_attendance_management_entry_ids(ids_conn)

    fetch_sql, fetch_params = fetch_conn.calls[0]
    count_sql, _ = count_conn.calls[0]
    ids_sql, _ = ids_conn.calls[0]
    assert "%s::bigint IS NULL OR d.restaurant_id = %s::bigint" in fetch_sql
    assert "%s::text IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) >= %s::text" in fetch_sql
    assert "%s::text IS NULL OR substr(COALESCE(d.entry_date, ''), 1, 10) <= %s::text" in fetch_sql
    assert "%s::text IS NULL" in fetch_sql
    assert fetch_params[-1] == 5
    assert "%s::bigint IS NULL OR d.restaurant_id = %s::bigint" in count_sql
    assert "%s::bigint IS NULL OR d.restaurant_id = %s::bigint" in ids_sql


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
