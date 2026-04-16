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


def test_create_personnel_record_creates_plate_history_baseline(monkeypatch):
    conn = FakeConnection()
    history_calls: list[dict] = []

    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(personnel_service, "insert_personnel_record", lambda *args, **kwargs: 52)
    monkeypatch.setattr(personnel_service, "sync_mobile_auth_user_for_personnel", lambda *args, **kwargs: None)
    monkeypatch.setattr(personnel_service, "count_plate_history_records_for_personnel", lambda *args, **kwargs: 0)
    monkeypatch.setattr(personnel_service, "fetch_active_plate_history_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "insert_plate_history_record",
        lambda _conn, **kwargs: history_calls.append(kwargs) or 17,
    )

    response = personnel_service.create_personnel_record(
        conn,
        payload=PersonnelCreateRequest(
            full_name="Plakalı Kurye",
            role="Kurye",
            current_plate="34 ABC 123",
            start_date=date(2026, 4, 17),
        ),
    )

    assert response.person_id == 52
    assert history_calls[0]["plate"] == "34 ABC 123"
    assert history_calls[0]["reason"] == "Sistem: Başlangıç plakası"


def test_update_personnel_record_writes_plate_history_on_plate_change(monkeypatch):
    conn = FakeConnection()
    history_calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        personnel_service,
        "fetch_personnel_record_by_id",
        lambda *args, **kwargs: {
            "id": 15,
            "person_code": "CK-K15",
            "role": "Kurye",
            "current_plate": "34 OLD 15",
        },
    )
    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(personnel_service, "update_personnel_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(personnel_service, "sync_mobile_auth_user_for_personnel", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "close_active_plate_history_records",
        lambda _conn, person_id, *, end_date: history_calls.append(("close", {"person_id": person_id, "end_date": end_date})),
    )
    monkeypatch.setattr(personnel_service, "fetch_active_plate_history_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        personnel_service,
        "insert_plate_history_record",
        lambda _conn, **kwargs: history_calls.append(("insert", kwargs)) or 18,
    )

    response = personnel_service.update_personnel_record_entry(
        conn,
        person_id=15,
        payload=PersonnelUpdateRequest(
            full_name="Plaka Değişti",
            role="Kurye",
            current_plate="34 NEW 99",
        ),
    )

    assert response.person_id == 15
    assert history_calls[0][0] == "close"
    assert history_calls[1][0] == "insert"
    assert history_calls[1][1]["plate"] == "34 NEW 99"


def test_create_personnel_record_ignores_plate_fields_without_permission(monkeypatch):
    conn = FakeConnection()
    inserted_payloads: list[dict] = []

    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        personnel_service,
        "insert_personnel_record",
        lambda _conn, values: inserted_payloads.append(values) or 52,
    )
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda *args, **kwargs: None,
    )

    response = personnel_service.create_personnel_record(
        conn,
        payload=PersonnelCreateRequest(
            full_name="Plaka Kapalı",
            role="Kurye",
            vehicle_mode="Çat Kapında Motor Kirası",
            current_plate="34 ABC 123",
        ),
        allow_vehicle_fields=False,
    )

    assert response.person_id == 52
    assert inserted_payloads[0]["vehicle_type"] == "Kendi Motoru"
    assert inserted_payloads[0]["motor_rental"] == "Hayır"
    assert inserted_payloads[0]["motor_purchase"] == "Hayır"
    assert inserted_payloads[0]["current_plate"] == ""


def test_update_personnel_record_preserves_plate_fields_without_permission(monkeypatch):
    conn = FakeConnection()
    updated_payloads: list[dict] = []

    monkeypatch.setattr(
        personnel_service,
        "fetch_personnel_record_by_id",
        lambda *args, **kwargs: {
            "id": 15,
            "person_code": "CK-K01",
            "role": "Kurye",
            "vehicle_type": "Çat Kapında",
            "motor_rental": "Evet",
            "motor_purchase": "Hayır",
            "current_plate": "34 XYZ 34",
        },
    )
    monkeypatch.setattr(personnel_service, "fetch_person_code_values", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        personnel_service,
        "update_personnel_record",
        lambda _conn, _person_id, values: updated_payloads.append(values),
    )
    monkeypatch.setattr(
        personnel_service,
        "sync_mobile_auth_user_for_personnel",
        lambda *args, **kwargs: None,
    )

    response = personnel_service.update_personnel_record_entry(
        conn,
        person_id=15,
        payload=PersonnelUpdateRequest(
            full_name="Tunç Test",
            role="Joker",
            phone="05321112233",
            vehicle_mode="Kendi Motoru",
            current_plate="34 NEW 99",
        ),
        allow_vehicle_fields=False,
    )

    assert response.message == "Personel kaydı güncellendi."
    assert updated_payloads[0]["vehicle_type"] == "Çat Kapında"
    assert updated_payloads[0]["motor_rental"] == "Evet"
    assert updated_payloads[0]["motor_purchase"] == "Hayır"
    assert updated_payloads[0]["current_plate"] == "34 XYZ 34"


def test_build_personnel_detail_masks_plate_fields_without_permission(monkeypatch):
    monkeypatch.setattr(
        personnel_service,
        "fetch_personnel_record_by_id",
        lambda *args, **kwargs: {
            "id": 21,
            "person_code": "CK-K21",
            "full_name": "Gizli Plaka",
            "role": "Kurye",
            "status": "Aktif",
            "phone": "05320000000",
            "restaurant_id": 3,
            "restaurant_label": "Test - Şube",
            "vehicle_type": "Çat Kapında",
            "motor_rental": "Evet",
            "motor_purchase": "Hayır",
            "current_plate": "34 PLT 34",
            "start_date": None,
            "monthly_fixed_cost": 0,
            "notes": "",
        },
    )

    response = personnel_service.build_personnel_detail(
        FakeConnection(),
        person_id=21,
        include_vehicle_fields=False,
    )

    assert response.entry.vehicle_mode == ""
    assert response.entry.current_plate == ""


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
