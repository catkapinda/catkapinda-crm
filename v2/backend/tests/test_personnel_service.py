from datetime import date

from app.schemas.personnel import PersonnelCreateRequest, PersonnelUpdateRequest
from app.services import personnel as personnel_service


class FakeConnection:
    def __init__(self):
        self.commit_count = 0

    def commit(self):
        self.commit_count += 1


def test_create_personnel_record_syncs_mobile_auth(monkeypatch):
    conn = FakeConnection()
    sync_calls: list[tuple[int, dict | None]] = []

    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(personnel_service, "insert_personnel_record", lambda *args, **kwargs: 42)
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda _conn, *, personnel_id, fallback_row=None: sync_calls.append((personnel_id, fallback_row)),
    )

    response = personnel_service.create_personnel_record(
        conn,
        payload=PersonnelCreateRequest(
            full_name="Tunç Test",
            role="Bölge Müdürü",
            phone="05321112233",
            start_date=date(2026, 4, 2),
        ),
    )

    assert response.person_id == 42
    assert response.message == "Personel kaydı oluşturuldu."
    assert sync_calls == [(42, None)]
    assert conn.commit_count == 1


def test_update_personnel_record_syncs_mobile_auth(monkeypatch):
    conn = FakeConnection()
    sync_calls: list[tuple[int, dict | None]] = []

    monkeypatch.setattr(
        personnel_service,
        "fetch_personnel_record_by_id",
        lambda *args, **kwargs: {"id": 15, "person_code": "CK-K01", "role": "Kurye"},
    )
    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(personnel_service, "update_personnel_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda _conn, *, personnel_id, fallback_row=None: sync_calls.append((personnel_id, fallback_row)),
    )

    response = personnel_service.update_personnel_record_entry(
        conn,
        person_id=15,
        payload=PersonnelUpdateRequest(
            full_name="Tunç Test",
            role="Joker",
            phone="05321112233",
        ),
    )

    assert response.message == "Personel kaydı güncellendi."
    assert sync_calls == [(15, None)]
    assert conn.commit_count == 1


def test_toggle_personnel_record_status_syncs_mobile_auth(monkeypatch):
    conn = FakeConnection()
    sync_calls: list[tuple[int, dict | None]] = []

    monkeypatch.setattr(
        personnel_service,
        "fetch_personnel_record_by_id",
        lambda *args, **kwargs: {"id": 16, "status": "Aktif"},
    )
    monkeypatch.setattr(personnel_service, "update_personnel_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda _conn, *, personnel_id, fallback_row=None: sync_calls.append((personnel_id, fallback_row)),
    )

    response = personnel_service.toggle_personnel_record_status(conn, person_id=16)

    assert response.message == "Personel pasife alındı."
    assert sync_calls == [(16, None)]
    assert conn.commit_count == 1


def test_delete_personnel_record_syncs_mobile_auth_with_passive_fallback(monkeypatch):
    conn = FakeConnection()
    sync_calls: list[tuple[int, dict | None]] = []
    existing_row = {
        "id": 17,
        "full_name": "Mert Test",
        "role": "Joker",
        "status": "Aktif",
        "phone": "05321112233",
    }

    monkeypatch.setattr(personnel_service, "fetch_personnel_record_by_id", lambda *args, **kwargs: existing_row)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_daily_entries", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_deductions", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_role_history", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_vehicle_history", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_plate_history", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_equipment_issues", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "count_personnel_linked_box_returns", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "delete_personnel_and_dependencies", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda _conn, *, personnel_id, fallback_row=None: sync_calls.append((personnel_id, fallback_row)),
    )

    response = personnel_service.delete_personnel_record_entry(conn, person_id=17)

    assert response.message == "Personel kaydı kalıcı olarak silindi."
    assert sync_calls == [(17, {**existing_row, "status": "Pasif"})]
    assert conn.commit_count == 1
