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
            "attendance.bulk_create",
            "attendance.create",
            "attendance.update",
            "attendance.delete",
            "attendance.bulk_delete",
            "deduction.create",
            "deduction.update",
            "deduction.delete",
            "deduction.bulk_delete",
            "equipment.create",
            "equipment.bulk_update",
            "equipment.bulk_delete",
            "equipment.box_return",
            "personnel.create",
            "personnel.update",
            "personnel.list",
            "personnel.status_change",
            "personnel.plate",
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
    audit_calls = []
    monkeypatch.setattr(
        "app.api.routes.attendance.safe_record_audit_event",
        lambda conn, **kwargs: audit_calls.append(kwargs) or True,
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.create_attendance_entry",
        lambda conn, payload: {
            "entry_id": 101,
            "message": "Puantaj kaydi olusturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.create_attendance_entries_bulk",
        lambda conn, payload: {
            "entry_ids": [201, 202],
            "created_count": 2,
            "message": "2 toplu puantaj kaydi olusturuldu.",
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
    monkeypatch.setattr(
        "app.api.routes.attendance.delete_attendance_entries_by_filter",
        lambda conn, payload: {
            "deleted_count": 31,
            "date_from": payload.date_from,
            "date_to": payload.date_to,
            "restaurant_id": payload.restaurant_id,
            "search": payload.search or "",
            "message": "Filtredeki 31 puantaj kaydi silindi.",
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
    bulk_create_response = client.post(
        "/api/attendance/entries/bulk",
        json={
            "entry_date": "2026-04-11",
            "restaurant_id": 10,
            "include_all_active": True,
            "rows": [
                {
                    "person_id": 20,
                    "worked_hours": 8,
                    "package_count": 20,
                    "entry_status": "Normal",
                },
                {
                    "person_id": 21,
                    "worked_hours": 6,
                    "package_count": 14,
                    "entry_status": "Joker",
                    "notes": "Geç kaldı",
                },
            ],
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
    filtered_delete_response = client.request(
        "DELETE",
        "/api/attendance/entries/filter",
        json={
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "restaurant_id": 10,
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["entry_id"] == 101
    assert audit_calls[0]["action_type"] == "oluştur"
    assert audit_calls[0]["entity_type"] == "puantaj"
    assert bulk_create_response.status_code == 201
    assert bulk_create_response.json()["created_count"] == 2
    assert audit_calls[1]["action_type"] == "güncelle"
    assert audit_calls[2]["action_type"] == "toplu oluştur"
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Puantaj kaydi guncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["entry_id"] == 101
    assert bulk_delete_response.status_code == 200
    assert bulk_delete_response.json()["deleted_count"] == 2
    assert filtered_delete_response.status_code == 200
    assert filtered_delete_response.json()["deleted_count"] == 31


def test_personnel_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.create_personnel_record",
        lambda conn, payload, allow_vehicle_fields=True: {
            "person_id": 33,
            "person_code": "CK-K33",
            "message": "Personel oluşturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.update_personnel_record_entry",
        lambda conn, person_id, payload, allow_vehicle_fields=True: {
            "person_id": person_id,
            "person_code": "CK-K33",
            "message": "Personel güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.toggle_personnel_record_status",
        lambda conn, person_id: {
            "person_id": person_id,
            "status": "Pasif",
            "message": "Personel pasife alındı.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.delete_personnel_record_entry",
        lambda conn, person_id: {
            "person_id": person_id,
            "message": "Personel kalıcı olarak silindi.",
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
            "full_name": "Test Kurye Güncel",
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
    assert delete_response.json()["message"] == "Personel kalıcı olarak silindi."


def test_personnel_plate_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.create_personnel_plate_history_entry",
        lambda conn, payload: {
            "history_id": 44,
            "personnel_id": payload.personnel_id,
            "plate": payload.plate,
            "message": "Plaka geçmişi güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.personnel.build_personnel_plate_workspace",
        lambda conn, limit: {
            "summary": {
                "total_history_records": 4,
                "active_plate_assignments": 2,
                "active_catkapinda_vehicle_personnel": 3,
                "active_missing_plate_personnel": 1,
            },
            "people": [
                {
                    "id": 9,
                    "person_code": "CK-K09",
                    "full_name": "Araçlı Kurye",
                    "role": "Kurye",
                    "status": "Aktif",
                    "restaurant_label": "Test - Şube",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 TEST 09",
                    "plate_history_count": 2,
                }
            ],
            "history": [
                {
                    "id": 44,
                    "personnel_id": 9,
                    "person_code": "CK-K09",
                    "full_name": "Araçlı Kurye",
                    "role": "Kurye",
                    "restaurant_label": "Test - Şube",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 TEST 09",
                    "plate": "34 TEST 09",
                    "start_date": "2026-04-17",
                    "end_date": None,
                    "reason": "Yeni zimmet",
                    "active": True,
                }
            ],
        },
    )
    client = _build_client()

    workspace_response = client.get("/api/personnel/plate-workspace")
    create_response = client.post(
        "/api/personnel/plate-history",
        json={
            "personnel_id": 9,
            "plate": "34 TEST 09",
            "reason": "Yeni zimmet",
            "start_date": "2026-04-17",
        },
    )

    assert workspace_response.status_code == 200
    assert workspace_response.json()["summary"]["total_history_records"] == 4
    assert create_response.status_code == 201
    assert create_response.json()["history_id"] == 44


def test_deductions_mutation_routes(monkeypatch):
    audit_calls = []
    monkeypatch.setattr(
        "app.api.routes.deductions.safe_record_audit_event",
        lambda conn, **kwargs: audit_calls.append(kwargs) or True,
    )
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
    monkeypatch.setattr(
        "app.api.routes.deductions.bulk_delete_deduction_entries",
        lambda conn, payload: {
            "deduction_ids": payload.deduction_ids,
            "deleted_count": len(payload.deduction_ids),
            "message": f"{len(payload.deduction_ids)} kesinti kaydi silindi.",
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
    bulk_delete_response = client.request(
        "DELETE",
        "/api/deductions/records",
        json={
            "deduction_ids": [44, 45],
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["deduction_id"] == 44
    assert audit_calls[0]["action_type"] == "oluştur"
    assert update_response.status_code == 200
    assert update_response.json()["message"] == "Kesinti kaydi guncellendi."
    assert audit_calls[1]["action_type"] == "güncelle"
    assert delete_response.status_code == 200
    assert delete_response.json()["deduction_id"] == 44
    assert audit_calls[2]["action_type"] == "sil"
    assert bulk_delete_response.status_code == 200
    assert bulk_delete_response.json()["deleted_count"] == 2
    assert audit_calls[3]["action_type"] == "toplu sil"


def test_restaurants_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.restaurants.create_restaurant_record",
        lambda conn, payload: {
            "restaurant_id": 77,
            "message": "Restoran oluşturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.update_restaurant_record_entry",
        lambda conn, restaurant_id, payload: {
            "restaurant_id": restaurant_id,
            "message": "Restoran güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.toggle_restaurant_record_status",
        lambda conn, restaurant_id: {
            "restaurant_id": restaurant_id,
            "active": False,
            "message": "Restoran pasife alındı.",
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
        "branch": "Kavacık",
        "pricing_model": "hourly_plus_package",
        "hourly_rate": 250,
        "package_rate": 20,
        "vat_rate": 20,
        "status": "Aktif",
    }
    update_payload = {
        "brand": "Burger@",
        "branch": "Kavacık Güncel",
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
    assert update_response.json()["message"] == "Restoran güncellendi."
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
            "message": "Satış fırsatı oluşturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.update_sales_record_entry",
        lambda conn, sales_id, payload: {
            "message": "Satış fırsatı güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.delete_sales_record_entry",
        lambda conn, sales_id: {
            "message": "Satış fırsatı silindi.",
        },
    )
    client = _build_client()

    create_payload = {
        "restaurant_name": "Donerci Celal Usta",
        "city": "İstanbul",
        "district": "Maltepe",
        "address": "Bağdat Caddesi No:1",
        "contact_name": "Erdal Altınkaynak",
        "contact_phone": "05325719142",
        "pricing_model": "hourly_plus_package",
        "status": "Teklif İletildi",
    }
    update_payload = {
        **create_payload,
        "district": "Kadıköy",
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
    assert update_response.json()["message"] == "Satış fırsatı güncellendi."
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Satış fırsatı silindi."


def test_equipment_mutation_routes(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.equipment.create_equipment_issue_entry",
        lambda conn, payload: {
            "equipment_issue_id": 61,
            "message": "Zimmet kaydı oluşturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.update_equipment_issue_entry",
        lambda conn, issue_id, payload: {
            "equipment_issue_id": issue_id,
            "message": "Zimmet kaydı güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.bulk_update_equipment_issue_entries",
        lambda conn, payload: {
            "updated_count": len(payload.issue_ids),
            "message": f"{len(payload.issue_ids)} zimmet kaydı güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.delete_equipment_issue_entry",
        lambda conn, issue_id: {
            "equipment_issue_id": issue_id,
            "message": "Zimmet kaydı silindi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.bulk_delete_equipment_issue_entries",
        lambda conn, payload: {
            "deleted_count": len(payload.issue_ids),
            "message": f"{len(payload.issue_ids)} zimmet kaydı ve bağlı taksitler silindi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.create_box_return_entry",
        lambda conn, payload: {
            "box_return_id": 71,
            "message": "Box geri alım kaydı oluşturuldu.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.update_box_return_entry",
        lambda conn, box_return_id, payload: {
            "box_return_id": box_return_id,
            "message": "Box geri alım kaydı güncellendi.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.delete_box_return_entry",
        lambda conn, box_return_id: {
            "box_return_id": box_return_id,
            "message": "Box geri alım kaydı silindi.",
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
    bulk_update_issue_response = client.post(
        "/api/equipment/issues/bulk-update",
        json={"issue_ids": [61, 62], "unit_cost": 2700, "note_append_text": "Nisan düzenlemesi"},
    )
    delete_issue_response = client.delete("/api/equipment/issues/61")
    bulk_delete_issue_response = client.post(
        "/api/equipment/issues/bulk-delete",
        json={"issue_ids": [61, 62]},
    )
    create_return_response = client.post("/api/equipment/box-returns", json=return_payload)
    update_return_response = client.put("/api/equipment/box-returns/71", json={**return_payload, "condition_status": "Hasarlı"})
    delete_return_response = client.delete("/api/equipment/box-returns/71")

    assert create_issue_response.status_code == 201
    assert create_issue_response.json()["equipment_issue_id"] == 61
    assert update_issue_response.status_code == 200
    assert update_issue_response.json()["message"] == "Zimmet kaydı güncellendi."
    assert bulk_update_issue_response.status_code == 200
    assert bulk_update_issue_response.json()["updated_count"] == 2
    assert delete_issue_response.status_code == 200
    assert delete_issue_response.json()["equipment_issue_id"] == 61
    assert bulk_delete_issue_response.status_code == 200
    assert bulk_delete_issue_response.json()["deleted_count"] == 2
    assert create_return_response.status_code == 201
    assert create_return_response.json()["box_return_id"] == 71
    assert update_return_response.status_code == 200
    assert update_return_response.json()["message"] == "Box geri alım kaydı güncellendi."
    assert delete_return_response.status_code == 200
    assert delete_return_response.json()["box_return_id"] == 71
