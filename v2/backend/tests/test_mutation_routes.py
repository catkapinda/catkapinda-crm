from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.main import create_app


class FakeConnection:
    def rollback(self) -> None:
        return None


def _fake_admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=1,
        identity="admin@catkapinda.com",
        email="admin@catkapinda.com",
        phone="05000000000",
        full_name="Admin Kullanici",
        role="admin",
        role_display="Admin",
        must_change_password=False,
        allowed_actions=[
            "attendance.create",
            "attendance.update",
            "attendance.delete",
            "deduction.create",
            "deduction.update",
            "deduction.delete",
            "personnel.create",
            "personnel.update",
            "personnel.list",
            "personnel.status_change",
            "personnel.delete",
            "restaurant.create",
            "restaurant.update",
            "restaurant.status_change",
            "restaurant.delete",
        ],
        expires_at="2099-01-01T00:00:00",
        token="token",
    )


def _build_client() -> TestClient:
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_current_user] = _fake_admin_user
    app.dependency_overrides[get_db] = lambda: FakeConnection()
    return TestClient(app)


def test_attendance_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.attendance.create_attendance_entry",
        lambda conn, payload: {
            "entry_id": 101,
            "message": "Puantaj kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.update_attendance_entry_record",
        lambda conn, entry_id, payload: {
            "entry_id": entry_id,
            "message": "Puantaj kaydi guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.delete_attendance_entry_record",
        lambda conn, entry_id: {
            "entry_id": entry_id,
            "message": "Puantaj kaydi silindi.",
        },
    )
    client = _build_client()

    create_response = client.post(
        "/api/attendance/entries",
        json={
            "entry_date": "2026-04-11",
            "restaurant_id": 10,
            "entry_mode": "Restoran Kuryesi",
            "primary_person_id": 20,
            "worked_hours": 6,
            "package_count": 10,
            "notes": "Test kaydi",
        },
    )
    update_response = client.put(
        "/api/attendance/entries/101",
        json={
            "entry_date": "2026-04-11",
            "restaurant_id": 10,
            "entry_mode": "Joker",
            "primary_person_id": 20,
            "replacement_person_id": 21,
            "worked_hours": 7,
            "package_count": 12,
            "notes": "Guncel kayit",
        },
    )
    delete_response = client.delete("/api/attendance/entries/101")

    assert create_response.status_code == 201
    assert create_response.json()["entry_id"] == 101
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Puantaj kaydi guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["entry_id"] == 101


def test_personnel_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.create_personnel_record",
        lambda conn, payload: {
            "person_id": 33,
            "person_code": "CK-K33",
            "message": "Personel olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.update_personnel_record_entry",
        lambda conn, person_id, payload: {
            "person_id": person_id,
            "person_code": "CK-K33",
            "message": "Personel guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.toggle_personnel_record_status",
        lambda conn, person_id: {
            "person_id": person_id,
            "status": "Pasif",
            "message": "Personel pasife alindi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.delete_personnel_record_entry",
        lambda conn, person_id: {
            "person_id": person_id,
            "message": "Personel kalici olarak silindi.",
        },
    )
    client = _build_client()

    create_response = client.post(
        "/api/personnel/records",
        json={
            "full_name": "Test Kurye",
            "role": "Kurye",
            "phone": "05000000001",
            "assigned_restaurant_id": 10,
            "status": "Aktif",
            "vehicle_mode": "Kendi Motoru",
        },
    )
    update_response = client.put(
        "/api/personnel/records/33",
        json={
            "full_name": "Test Kurye Guncel",
            "role": "Kurye",
            "phone": "05000000002",
            "assigned_restaurant_id": 11,
            "status": "Aktif",
            "vehicle_mode": "Çat Kapında",
        },
    )
    toggle_response = client.post("/api/personnel/records/33/toggle-status")
    delete_response = client.delete("/api/personnel/records/33")

    assert create_response.status_code == 201
    assert create_response.json()["person_code"] == "CK-K33"
    assert update_response.status_code == 200
    assert update_response.json()["person_id"] == 33
    assert toggle_response.status_code == 200
    assert toggle_response.json()["status"] == "Pasif"
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Personel kalici olarak silindi."


def test_deductions_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.deductions.create_deduction_entry",
        lambda conn, payload: {
            "deduction_id": 44,
            "message": "Kesinti kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.deductions.update_deduction_entry",
        lambda conn, deduction_id, payload: {
            "deduction_id": deduction_id,
            "message": "Kesinti kaydi guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.deductions.delete_deduction_entry",
        lambda conn, deduction_id: {
            "deduction_id": deduction_id,
            "message": "Kesinti kaydi silindi.",
        },
    )
    client = _build_client()

    create_response = client.post(
        "/api/deductions/records",
        json={
            "personnel_id": 5,
            "deduction_date": "2026-04-11",
            "deduction_type": "Avans",
            "amount": 1500,
            "notes": "Test kesintisi",
        },
    )
    update_response = client.put(
        "/api/deductions/records/44",
        json={
            "personnel_id": 5,
            "deduction_date": "2026-04-12",
            "deduction_type": "HGS",
            "amount": 1750,
            "notes": "Guncel kesinti",
        },
    )
    delete_response = client.delete("/api/deductions/records/44")

    assert create_response.status_code == 201
    assert create_response.json()["deduction_id"] == 44
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Kesinti kaydi guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["deduction_id"] == 44


def test_restaurants_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.restaurants.create_restaurant_record",
        lambda conn, payload: {
            "restaurant_id": 77,
            "message": "Restoran olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.update_restaurant_record_entry",
        lambda conn, restaurant_id, payload: {
            "restaurant_id": restaurant_id,
            "message": "Restoran guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.toggle_restaurant_record_status",
        lambda conn, restaurant_id: {
            "restaurant_id": restaurant_id,
            "active": False,
            "message": "Restoran pasife alindi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.delete_restaurant_record_entry",
        lambda conn, restaurant_id: {
            "restaurant_id": restaurant_id,
            "message": "Restoran silindi.",
        },
    )
    client = _build_client()

    create_payload = {
        "brand": "Burger@",
        "branch": "Kavacik",
        "pricing_model": "hourly_plus_package",
        "hourly_rate": 250,
        "package_rate": 20,
        "vat_rate": 20,
        "status": "Aktif",
    }
    update_payload = {
        "brand": "Burger@",
        "branch": "Kavacik Guncel",
        "pricing_model": "fixed_monthly",
        "fixed_monthly_fee": 80000,
        "vat_rate": 20,
        "status": "Aktif",
    }

    create_response = client.post("/api/restaurants/records", json=create_payload)
    update_response = client.put("/api/restaurants/records/77", json=update_payload)
    toggle_response = client.post("/api/restaurants/records/77/toggle-status")
    delete_response = client.delete("/api/restaurants/records/77")

    assert create_response.status_code == 201
    assert create_response.json()["restaurant_id"] == 77
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Restoran guncellendi."
    assert toggle_response.status_code == 200
    assert toggle_response.json()["active"] is False
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Restoran silindi."
