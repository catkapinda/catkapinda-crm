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
            "attendance.bulk_delete",
            "deduction.create",
            "deduction.update",
            "deduction.delete",
            "equipment.create",
            "equipment.bulk_update",
            "equipment.bulk_delete",
            "equipment.box_return",
            "personnel.create",
            "personnel.update",
            "personnel.list",
            "personnel.status_change",
            "personnel.delete",
            "purchase.create",
            "purchase.update",
            "purchase.delete",
            "restaurant.create",
            "restaurant.update",
            "restaurant.status_change",
            "restaurant.delete",
            "sales.create",
            "sales.update",
            "sales.delete",
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
    monkeypatch.setattr(
        "app.api.routes.attendance.bulk_delete_attendance_entries",
        lambda conn, payload: {
            "entry_ids": payload.entry_ids,
            "deleted_count": len(payload.entry_ids),
            "message": f"{len(payload.entry_ids)} puantaj kaydi silindi.",
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
    bulk_delete_response = client.request(
        "DELETE",
        "/api/attendance/entries",
        json={
            "entry_ids": [101, 102],
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["entry_id"] == 101
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Puantaj kaydi guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["entry_id"] == 101
    assert bulk_delete_response.status_code == 200
    assert bulk_delete_response.json()["deleted_count"] == 2


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


def test_purchases_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.purchases.create_purchase_record",
        lambda conn, payload: {
            "purchase_id": 88,
            "message": "Satin alma kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.purchases.update_purchase_record_entry",
        lambda conn, purchase_id, payload: {
            "purchase_id": purchase_id,
            "message": "Satin alma kaydi guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.purchases.delete_purchase_record_entry",
        lambda conn, purchase_id: {
            "purchase_id": purchase_id,
            "message": "Satin alma kaydi silindi.",
        },
    )
    client = _build_client()

    create_response = client.post(
        "/api/purchases/records",
        json={
            "purchase_date": "2026-04-11",
            "item_name": "Box",
            "quantity": 4,
            "total_invoice_amount": 12800,
            "supplier": "Test Tedarikci",
            "invoice_no": "INV-001",
            "notes": "Test satin alma",
        },
    )
    update_response = client.put(
        "/api/purchases/records/88",
        json={
            "purchase_date": "2026-04-12",
            "item_name": "Punch",
            "quantity": 2,
            "total_invoice_amount": 4200,
            "supplier": "Guncel Tedarikci",
            "invoice_no": "INV-002",
            "notes": "Guncel satin alma",
        },
    )
    delete_response = client.delete("/api/purchases/records/88")

    assert create_response.status_code == 201
    assert create_response.json()["purchase_id"] == 88
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Satin alma kaydi guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["purchase_id"] == 88


def test_sales_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.sales.create_sales_record",
        lambda conn, payload: {
            "entry_id": 55,
            "message": "Satis firsati olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.update_sales_record_entry",
        lambda conn, sales_id, payload: {
            "message": "Satis firsati guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.delete_sales_record_entry",
        lambda conn, sales_id: {
            "message": "Satis firsati silindi.",
        },
    )
    client = _build_client()

    create_payload = {
        "restaurant_name": "Donerci Celal Usta",
        "city": "Istanbul",
        "district": "Maltepe",
        "address": "Bagdat Caddesi No:1",
        "contact_name": "Erdal Altinkaynak",
        "contact_phone": "05325719142",
        "pricing_model": "hourly_plus_package",
        "status": "Teklif Iletildi",
    }
    update_payload = {
        **create_payload,
        "district": "Kadikoy",
        "pricing_model": "fixed_monthly",
        "fixed_monthly_fee": 90000,
        "status": "Tekrar Aranacak",
    }

    create_response = client.post("/api/sales/records", json=create_payload)
    update_response = client.put("/api/sales/records/55", json=update_payload)
    delete_response = client.delete("/api/sales/records/55")

    assert create_response.status_code == 201
    assert create_response.json()["entry_id"] == 55
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Satis firsati guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Satis firsati silindi."


def test_equipment_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.equipment.create_equipment_issue_entry",
        lambda conn, payload: {
            "equipment_issue_id": 61,
            "message": "Zimmet kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.update_equipment_issue_entry",
        lambda conn, issue_id, payload: {
            "equipment_issue_id": issue_id,
            "message": "Zimmet kaydi guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.delete_equipment_issue_entry",
        lambda conn, issue_id: {
            "equipment_issue_id": issue_id,
            "message": "Zimmet kaydi silindi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.create_box_return_entry",
        lambda conn, payload: {
            "box_return_id": 71,
            "message": "Box iade kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.update_box_return_entry",
        lambda conn, box_return_id, payload: {
            "box_return_id": box_return_id,
            "message": "Box iade kaydi guncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.delete_box_return_entry",
        lambda conn, box_return_id: {
            "box_return_id": box_return_id,
            "message": "Box iade kaydi silindi.",
        },
    )
    client = _build_client()

    issue_payload = {
        "personnel_id": 5,
        "issue_date": "2026-04-11",
        "item_name": "Box",
        "quantity": 1,
        "unit_cost": 2500,
        "unit_sale_price": 3200,
        "installment_count": 2,
        "sale_type": "Satış",
        "notes": "Test zimmet",
    }
    return_payload = {
        "personnel_id": 5,
        "return_date": "2026-04-12",
        "quantity": 1,
        "condition_status": "Temiz",
        "payout_amount": 0,
        "notes": "Test iade",
    }

    create_issue_response = client.post("/api/equipment/issues", json=issue_payload)
    update_issue_response = client.put("/api/equipment/issues/61", json={**issue_payload, "quantity": 2})
    delete_issue_response = client.delete("/api/equipment/issues/61")
    create_return_response = client.post("/api/equipment/box-returns", json=return_payload)
    update_return_response = client.put("/api/equipment/box-returns/71", json={**return_payload, "condition_status": "Hasarlı"})
    delete_return_response = client.delete("/api/equipment/box-returns/71")

    assert create_issue_response.status_code == 201
    assert create_issue_response.json()["equipment_issue_id"] == 61
    assert update_issue_response.status_code == 200
    assert update_issue_response.json()["message"] == "Zimmet kaydi guncellendi."
    assert delete_issue_response.status_code == 200
    assert delete_issue_response.json()["equipment_issue_id"] == 61
    assert create_return_response.status_code == 201
    assert create_return_response.json()["box_return_id"] == 71
    assert update_return_response.status_code == 200
    assert update_return_response.json()["message"] == "Box iade kaydi guncellendi."
    assert delete_return_response.status_code == 200
    assert delete_return_response.json()["box_return_id"] == 71
