from fastapi.testclient import TestClient

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.core.security import AuthenticatedUser
from app.core.config import settings
from app.main import create_app


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
            "dashboard.view",
            "announcements.view",
            "attendance.view",
            "deduction.view",
            "equipment.view",
            "personnel.list",
            "personnel.plate",
            "purchase.view",
            "payroll.view",
            "restaurant.view",
            "reporting.view",
            "sales.view",
        ],
        expires_at="2099-01-01T00:00:00",
        token="token",
    )


def _build_app() -> TestClient:
    app = create_app(enable_bootstrap=False)
    app.dependency_overrides[get_current_user] = _fake_admin_user
    app.dependency_overrides[get_db] = lambda: object()
    return TestClient(app)


def test_overview_dashboard_route_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.overview.build_overview_dashboard",
        lambda conn, reference_date: {
            "module": "overview",
            "status": "active",
            "hero": {
                "active_restaurants": 12,
                "active_personnel": 85,
                "month_attendance_entries": 640,
                "month_deduction_entries": 92,
            },
            "finance": {
                "selected_month": "2026-04",
                "total_revenue": 240000.0,
                "gross_profit": 87000.0,
                "total_personnel_cost": 131000.0,
                "side_income_net": 12000.0,
                "top_restaurants": [
                    {"label": "Burger@ - Kavacık", "value": "120.000 TL"},
                ],
                "risk_restaurants": [
                    {"label": "Kod Deneme - Rapor 20260416", "value": "8.000 TL"},
                ],
            },
            "hygiene": {
                "missing_personnel_cards": 2,
                "missing_restaurant_cards": 1,
                "personnel_samples": [
                    {"title": "Beytullah Belen", "subtitle": "Telefon, Şube"},
                ],
                "restaurant_samples": [
                    {"title": "Burger@ - Kavacık", "subtitle": "Adres"},
                ],
            },
            "operations": {
                "missing_attendance_count": 3,
                "under_target_count": 2,
                "joker_usage_count": 1,
                "critical_signal_count": 6,
                "profitable_restaurant_count": 5,
                "risky_restaurant_count": 2,
                "shared_operation_total": 14000.0,
                "action_alerts": [
                    {
                        "tone": "critical",
                        "badge": "Bugün",
                        "title": "Burger@ - Kavacık",
                        "detail": "Bugün puantaj bekleniyor. Günlük kayıt henüz girilmedi.",
                    }
                ],
                "brand_summary": [
                    {
                        "brand": "Burger@",
                        "restaurant_count": 4,
                        "total_packages": 820.0,
                        "total_hours": 312.0,
                        "gross_invoice": 120000.0,
                        "operation_gap": 34000.0,
                        "status": "Sağlam",
                    }
                ],
                "daily_trend": [
                    {
                        "entry_date": "2026-04-10",
                        "total_packages": 120.0,
                        "total_hours": 42.0,
                    }
                ],
                "top_restaurants": [
                    {
                        "restaurant": "Burger@ - Kavacık",
                        "total_packages": 320.0,
                        "total_hours": 84.0,
                    }
                ],
                "joker_restaurants": [
                    {
                        "restaurant": "Burger@ - Kavacık",
                        "joker_count": 2,
                        "total_packages": 48.0,
                    }
                ],
            },
            "modules": [
                {
                    "key": "attendance",
                    "title": "Puantaj",
                    "description": "Günlük vardiya ve saat takibi",
                    "href": "/attendance",
                    "primary_label": "Bu Ay",
                    "primary_value": "640",
                    "secondary_label": "Bugün",
                    "secondary_value": "18",
                }
            ],
            "recent_activity": [
                {
                    "module_key": "attendance",
                    "module_label": "Puantaj",
                    "title": "Burger@ - Kavacık",
                    "subtitle": "Beytullah Belen vardiyası kaydedildi",
                    "meta": "6 saat • 10 paket",
                    "entry_date": "2026-04-11",
                    "href": "/attendance",
                }
            ],
        },
    )
    client = _build_app()

    response = client.get("/api/overview/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["hero"]["active_restaurants"] == 12
    assert payload["finance"]["gross_profit"] == 87000.0
    assert payload["hygiene"]["missing_personnel_cards"] == 2
    assert payload["operations"]["under_target_count"] == 2
    assert payload["operations"]["top_restaurants"][0]["restaurant"] == "Burger@ - Kavacık"
    assert payload["operations"]["joker_restaurants"][0]["joker_count"] == 2
    assert payload["operations"]["shared_operation_total"] == 14000.0
    assert payload["modules"][0]["href"] == "/attendance"
    assert payload["modules"][0]["description"] == "Günlük vardiya ve saat takibi"
    assert payload["modules"][0]["secondary_label"] == "Bugün"
    assert payload["recent_activity"][0]["title"] == "Burger@ - Kavacık"


def test_root_route_guides_to_health_and_docs():
    client = _build_app()

    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["health"] == "/api/health"
    assert payload["docs"] == "/docs"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_root_route_sets_hsts_header_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    client = _build_app()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains; preload"


def test_payroll_routes_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.payroll.build_payroll_dashboard",
        lambda conn, selected_month, role_filter, restaurant_filter, limit: {
            "module": "payroll",
            "status": "active",
            "month_options": ["2026-04"],
            "selected_month": "2026-04",
            "role_options": ["Tümü", "Kurye"],
            "restaurant_options": ["Tümü", "Burger@ - Kavacık"],
            "selected_role": "Tümü",
            "selected_restaurant": "Tümü",
            "summary": {
                "selected_month": "2026-04",
                "personnel_count": 1,
                "total_hours": 9.0,
                "total_packages": 24.0,
                "gross_payroll": 32000.0,
                "total_deductions": 1500.0,
                "net_payment": 30500.0,
            },
            "entries": [
                {
                    "personnel_id": 1,
                    "personnel": "Mert Kurtuluş",
                    "role": "Kurye",
                    "status": "Aktif",
                    "total_hours": 9.0,
                    "total_packages": 24.0,
                    "gross_pay": 32000.0,
                    "total_deductions": 1500.0,
                    "net_payment": 30500.0,
                    "restaurant_count": 1,
                    "cost_model": "Sabit Aylık",
                }
            ],
            "cost_model_breakdown": [
                {
                    "cost_model": "Sabit Aylık",
                    "personnel_count": 1,
                    "total_hours": 9.0,
                    "total_packages": 24.0,
                    "net_payment": 30500.0,
                }
            ],
            "role_breakdown": [
                {
                    "role": "Kurye",
                    "personnel_count": 1,
                    "total_hours": 9.0,
                    "total_packages": 24.0,
                    "net_payment": 30500.0,
                }
            ],
            "top_personnel": [
                {
                    "personnel_id": 1,
                    "personnel": "Mert Kurtuluş",
                    "role": "Kurye",
                    "total_hours": 9.0,
                    "total_packages": 24.0,
                    "total_deductions": 1500.0,
                    "net_payment": 30500.0,
                    "restaurant_count": 1,
                    "cost_model": "Sabit Aylık",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.payroll.build_payroll_document_file",
        lambda conn, selected_month, personnel_id: ("hakedis_Mert_Kurtulus_2026-04.pdf", b"%PDF-1.4 test"),
    )

    client = _build_app()

    dashboard_response = client.get("/api/payroll/dashboard")
    document_response = client.get("/api/payroll/document?month=2026-04&personnel_id=1")

    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["summary"]["net_payment"] == 30500.0
    assert dashboard_payload["entries"][0]["personnel"] == "Mert Kurtuluş"
    assert dashboard_payload["role_breakdown"][0]["role"] == "Kurye"

    assert document_response.status_code == 200
    assert document_response.headers["content-type"] == "application/pdf"
    assert "hakedis_Mert_Kurtulus_2026-04.pdf" in document_response.headers["content-disposition"]
    assert document_response.content.startswith(b"%PDF")


def test_attendance_routes_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.attendance.build_attendance_dashboard",
        lambda conn, reference_date, limit: {
            "module": "attendance",
            "status": "active",
            "summary": {
                "total_entries": 441,
                "today_entries": 8,
                "month_entries": 312,
                "active_restaurants": 19,
            },
            "recent_entries": [
                {
                    "id": 1,
                    "entry_date": "2026-04-11",
                    "restaurant": "Burger@ - Kavacik",
                    "employee_name": "Beytullah Belen",
                    "entry_mode": "Restoran Kuryesi",
                    "absence_reason": "",
                    "coverage_type": "",
                    "worked_hours": 6.0,
                    "package_count": 10.0,
                    "monthly_invoice_amount": 0.0,
                    "notes": "",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.build_attendance_form_options",
        lambda conn, restaurant_id=None, include_all_active=False: {
            "restaurants": [
                {
                    "id": 10,
                    "label": "Burger@ - Kavacik",
                    "pricing_model": "hourly_plus_package",
                    "fixed_monthly_fee": 0.0,
                }
            ],
            "people": [
                {
                    "id": 20,
                    "label": "Beytullah Belen (Kurye)",
                    "role": "Kurye",
                }
            ],
            "entry_modes": ["Restoran Kuryesi", "Joker", "Destek", "Haftalik Izin"],
            "absence_reasons": ["Izinli", "Raporlu"],
            "bulk_statuses": ["Normal", "Joker", "İzin"],
            "selected_restaurant_id": restaurant_id,
            "selected_pricing_model": "hourly_plus_package",
            "selected_fixed_monthly_fee": 0.0,
        },
    )
    monkeypatch.setattr(
        "app.api.routes.attendance.build_attendance_management",
        lambda conn, limit, restaurant_id=None, search=None, date_from=None, date_to=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 1,
                    "entry_date": "2026-04-11",
                    "restaurant_id": 10,
                    "restaurant": "Burger@ - Kavacik",
                    "entry_mode": "Restoran Kuryesi",
                    "primary_person_id": 20,
                    "primary_person_label": "Beytullah Belen (Kurye)",
                    "replacement_person_id": None,
                    "replacement_person_label": "",
                    "absence_reason": "",
                    "coverage_type": "",
                    "worked_hours": 6.0,
                    "package_count": 10.0,
                    "monthly_invoice_amount": 0.0,
                    "notes": "",
                }
            ],
        },
    )
    client = _build_app()

    dashboard = client.get("/api/attendance/dashboard")
    form_options = client.get("/api/attendance/form-options")
    entries = client.get("/api/attendance/entries")

    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["total_entries"] == 441
    assert form_options.status_code == 200
    assert form_options.json()["restaurants"][0]["label"] == "Burger@ - Kavacik"
    assert entries.status_code == 200
    assert entries.json()["entries"][0]["primary_person_label"] == "Beytullah Belen (Kurye)"


def test_announcements_routes_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.announcements.build_announcements_dashboard",
        lambda: {
            "module": "announcements",
            "status": "active",
            "kicker": "Güncellemeler ve Duyurular",
            "title": "Sistemdeki son iyileştirmeler ve takip notları",
            "description": "Operasyon ekibinin son yayınlanan geliştirmeleri tek ekranda görmesi için hazırlanır.",
            "metrics": [
                {"label": "Giriş Deneyimi", "value": "Yenilendi"},
            ],
            "snapshots": [
                {
                    "title": "Operasyon ve Form Akışları",
                    "items": [
                        {"label": "Personel Yönetimi", "value": "Başarı mesajı güçlendi."},
                    ],
                }
            ],
            "checklist_title": "İlk Kontrol Sırası",
            "checklist_items": [
                {
                    "title": "1. Giriş ve durum ekranını aç",
                    "detail": "Yayın sonrası omurgayı buradan hızlı kontrol et.",
                }
            ],
            "notes_title": "Notlar",
            "notes_body": "Gerekirse yayın sonrası sert yenileme yapılır.",
            "footer_note": "Bu alan yeni notlarla genişletilebilir.",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.announcements.build_announcements_status",
        lambda: {
            "module": "announcements",
            "status": "active",
            "next_slice": "release-notes-board",
        },
    )
    client = _build_app()

    status_response = client.get("/api/announcements/status")
    dashboard_response = client.get("/api/announcements/dashboard")

    assert status_response.status_code == 200
    assert status_response.json()["module"] == "announcements"
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["metrics"][0]["value"] == "Yenilendi"
    assert dashboard_response.json()["checklist_items"][0]["title"] == "1. Giriş ve durum ekranını aç"


def test_personnel_plate_workspace_route_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.build_personnel_plate_workspace",
        lambda conn, limit: {
            "summary": {
                "total_history_records": 7,
                "active_plate_assignments": 3,
                "active_catkapinda_vehicle_personnel": 5,
                "active_missing_plate_personnel": 2,
            },
            "people": [
                {
                    "id": 18,
                    "person_code": "CK-K18",
                    "full_name": "Plakalı Kurye",
                    "role": "Kurye",
                    "status": "Aktif",
                    "restaurant_label": "Burger@ - Kavacık",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 ABC 18",
                    "plate_history_count": 2,
                }
            ],
            "history": [
                {
                    "id": 91,
                    "personnel_id": 18,
                    "person_code": "CK-K18",
                    "full_name": "Plakalı Kurye",
                    "role": "Kurye",
                    "restaurant_label": "Burger@ - Kavacık",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 ABC 18",
                    "plate": "34 ABC 18",
                    "start_date": "2026-04-10",
                    "end_date": None,
                    "reason": "Yeni zimmet",
                    "active": True,
                }
            ],
        },
    )
    client = _build_app()

    response = client.get("/api/personnel/plate-workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["active_plate_assignments"] == 3
    assert payload["people"][0]["current_plate"] == "34 ABC 18"


def test_personnel_role_workspace_route_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.build_personnel_role_workspace",
        lambda conn, limit: {
            "summary": {
                "total_history_records": 9,
                "active_personnel": 5,
                "distinct_roles": 4,
                "fixed_cost_cards": 3,
            },
            "people": [
                {
                    "id": 27,
                    "person_code": "CK-J27",
                    "full_name": "Rol Görünümü",
                    "role": "Joker",
                    "status": "Aktif",
                    "restaurant_label": "Burger@ - Kavacık",
                    "cost_model": "fixed_joker",
                    "monthly_fixed_cost": 22000,
                    "role_history_count": 3,
                }
            ],
            "history": [
                {
                    "id": 103,
                    "personnel_id": 27,
                    "person_code": "CK-J27",
                    "full_name": "Rol Görünümü",
                    "status": "Aktif",
                    "restaurant_label": "Burger@ - Kavacık",
                    "role": "Joker",
                    "cost_model": "fixed_joker",
                    "monthly_fixed_cost": 22000,
                    "effective_date": "2026-04-17",
                    "notes": "Rol geçişi",
                }
            ],
        },
    )
    client = _build_app()

    response = client.get("/api/personnel/role-workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["distinct_roles"] == 4
    assert payload["people"][0]["role_history_count"] == 3


def test_personnel_vehicle_workspace_route_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.personnel.build_personnel_vehicle_workspace",
        lambda conn, limit: {
            "summary": {
                "total_history_records": 8,
                "active_catkapinda_vehicle_personnel": 5,
                "rental_cards": 2,
                "sale_cards": 1,
            },
            "people": [
                {
                    "id": 31,
                    "person_code": "CK-K31",
                    "full_name": "Motor Görünümü",
                    "role": "Kurye",
                    "status": "Aktif",
                    "restaurant_label": "Burger@ - Kavacık",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 MTR 31",
                    "motor_rental_monthly_amount": 13000,
                    "motor_purchase_start_date": None,
                    "motor_purchase_commitment_months": 0,
                    "motor_purchase_sale_price": 0,
                    "motor_purchase_monthly_deduction": 0,
                    "vehicle_history_count": 2,
                }
            ],
            "history": [
                {
                    "id": 118,
                    "personnel_id": 31,
                    "person_code": "CK-K31",
                    "full_name": "Motor Görünümü",
                    "role": "Kurye",
                    "status": "Aktif",
                    "restaurant_label": "Burger@ - Kavacık",
                    "vehicle_mode": "Çat Kapında Motor Kirası",
                    "current_plate": "34 MTR 31",
                    "motor_rental_monthly_amount": 13000,
                    "motor_purchase_start_date": None,
                    "motor_purchase_commitment_months": 0,
                    "motor_purchase_sale_price": 0,
                    "motor_purchase_monthly_deduction": 0,
                    "effective_date": "2026-04-17",
                    "notes": "Motor geçişi",
                }
            ],
        },
    )
    client = _build_app()

    response = client.get("/api/personnel/vehicle-workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["rental_cards"] == 2
    assert payload["people"][0]["vehicle_history_count"] == 2


def test_deductions_routes_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.deductions.build_deductions_dashboard",
        lambda conn, reference_date, limit: {
            "module": "deductions",
            "status": "active",
            "summary": {
                "total_entries": 33,
                "this_month_entries": 9,
                "manual_entries": 6,
                "auto_entries": 3,
            },
            "recent_entries": [
                {
                    "id": 11,
                    "personnel_id": 5,
                    "personnel_label": "Tunç Test",
                    "deduction_date": "2026-04-11",
                    "deduction_type": "Avans",
                    "type_caption": "Avans",
                    "amount": 1500.0,
                    "notes": "",
                    "auto_source_key": "",
                    "is_auto_record": False,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.deductions.build_deductions_form_options",
        lambda conn, personnel_id=None: {
            "personnel": [{"id": 5, "label": "Tunç Test"}],
            "deduction_types": ["Avans", "HGS"],
            "type_captions": {"Avans": "Avans", "HGS": "HGS"},
            "selected_personnel_id": personnel_id,
        },
    )
    monkeypatch.setattr(
        "app.api.routes.deductions.build_deductions_management",
        lambda conn, limit, personnel_id=None, deduction_type=None, search=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 11,
                    "personnel_id": 5,
                    "personnel_label": "Tunç Test",
                    "deduction_date": "2026-04-11",
                    "deduction_type": "Avans",
                    "type_caption": "Avans",
                    "amount": 1500.0,
                    "notes": "",
                    "auto_source_key": "",
                    "is_auto_record": False,
                }
            ],
        },
    )
    client = _build_app()

    dashboard = client.get("/api/deductions/dashboard")
    form_options = client.get("/api/deductions/form-options")
    records = client.get("/api/deductions/records")

    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["manual_entries"] == 6
    assert form_options.status_code == 200
    assert form_options.json()["deduction_types"] == ["Avans", "HGS"]
    assert records.status_code == 200
    assert records.json()["entries"][0]["type_caption"] == "Avans"


def test_restaurants_sales_and_purchases_routes_smoke(monkeypatch):
    seen_sales_filters: dict[str, object] = {}

    monkeypatch.setattr(
        "app.api.routes.restaurants.build_restaurants_dashboard",
        lambda conn, limit: {
            "module": "restaurants",
            "status": "active",
            "summary": {
                "total_restaurants": 24,
                "active_restaurants": 21,
                "passive_restaurants": 3,
                "fixed_monthly_restaurants": 2,
            },
            "recent_entries": [
                {
                    "id": 7,
                    "brand": "Burger@",
                    "branch": "Kavacik",
                    "pricing_model": "hourly_plus_package",
                    "pricing_model_label": "Saat + Paket",
                    "hourly_rate": 279.0,
                    "package_rate": 32.0,
                    "package_threshold": 390,
                    "package_rate_low": 0.0,
                    "package_rate_high": 0.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "target_headcount": 8,
                    "start_date": None,
                    "end_date": None,
                    "extra_headcount_request": 0,
                    "extra_headcount_request_date": None,
                    "reduce_headcount_request": 0,
                    "reduce_headcount_request_date": None,
                    "contact_name": "Orkun Gunduz",
                    "contact_phone": "",
                    "contact_email": "",
                    "company_title": "",
                    "address": "",
                    "tax_office": "",
                    "tax_number": "",
                    "active": True,
                    "notes": "",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.build_restaurants_form_options",
        lambda pricing_model=None: {
            "pricing_models": [{"value": "hourly_plus_package", "label": "Saat + Paket"}],
            "status_options": ["Aktif", "Pasif"],
            "selected_pricing_model": pricing_model or "hourly_plus_package",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.restaurants.build_restaurants_management",
        lambda conn, limit, pricing_model=None, active=None, search=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 7,
                    "brand": "Burger@",
                    "branch": "Kavacik",
                    "pricing_model": "hourly_plus_package",
                    "pricing_model_label": "Saat + Paket",
                    "hourly_rate": 279.0,
                    "package_rate": 32.0,
                    "package_threshold": 390,
                    "package_rate_low": 0.0,
                    "package_rate_high": 0.0,
                    "fixed_monthly_fee": 0.0,
                    "vat_rate": 20.0,
                    "target_headcount": 8,
                    "start_date": None,
                    "end_date": None,
                    "extra_headcount_request": 0,
                    "extra_headcount_request_date": None,
                    "reduce_headcount_request": 0,
                    "reduce_headcount_request_date": None,
                    "contact_name": "Orkun Gunduz",
                    "contact_phone": "",
                    "contact_email": "",
                    "company_title": "",
                    "address": "",
                    "tax_office": "",
                    "tax_number": "",
                    "active": True,
                    "notes": "",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.build_sales_dashboard",
        lambda conn, limit: {
            "module": "sales",
            "status": "active",
            "summary": {
                "total_entries": 16,
                "open_follow_up": 4,
                "proposal_stage": 6,
                "won_count": 2,
            },
            "recent_entries": [
                {
                    "id": 3,
                    "restaurant_name": "Donerci Celal Usta",
                    "city": "Istanbul",
                    "district": "Maltepe",
                    "address": "",
                    "contact_name": "Erdal Altinkaynak",
                    "contact_phone": "05325719142",
                    "contact_email": "",
                    "requested_courier_count": 2,
                    "lead_source": "Referans",
                    "proposed_quote": 273.0,
                    "pricing_model": "threshold_package",
                    "pricing_model_label": "Eşikli Paket",
                    "pricing_model_hint": "",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 44.25,
                    "fixed_monthly_fee": 0.0,
                    "status": "Teklif Iletildi",
                    "next_follow_up_date": None,
                    "assigned_owner": "Ebru Aslan",
                    "notes": "",
                    "created_at": "2026-04-11T10:00:00",
                    "updated_at": "2026-04-11T10:00:00",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.build_sales_form_options",
        lambda pricing_model=None: {
            "pricing_models": [{"value": "threshold_package", "label": "Eşikli Paket"}],
            "source_options": ["Telefon", "Referans"],
            "status_options": ["Teklif Iletildi", "Olumsuz"],
            "selected_pricing_model": pricing_model or "threshold_package",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.sales.build_sales_management",
        lambda conn, limit, status=None, lead_source=None, search=None: seen_sales_filters.update(
            {
                "limit": limit,
                "status": status,
                "lead_source": lead_source,
                "search": search,
            }
        )
        or {
            "total_entries": 1,
            "entries": [
                {
                    "id": 3,
                    "restaurant_name": "Donerci Celal Usta",
                    "city": "Istanbul",
                    "district": "Maltepe",
                    "address": "",
                    "contact_name": "Erdal Altinkaynak",
                    "contact_phone": "05325719142",
                    "contact_email": "",
                    "requested_courier_count": 2,
                    "lead_source": "Referans",
                    "proposed_quote": 273.0,
                    "pricing_model": "threshold_package",
                    "pricing_model_label": "Eşikli Paket",
                    "pricing_model_hint": "",
                    "hourly_rate": 273.0,
                    "package_rate": 0.0,
                    "package_threshold": 390,
                    "package_rate_low": 33.75,
                    "package_rate_high": 44.25,
                    "fixed_monthly_fee": 0.0,
                    "status": "Teklif Iletildi",
                    "next_follow_up_date": None,
                    "assigned_owner": "Ebru Aslan",
                    "notes": "",
                    "created_at": "2026-04-11T10:00:00",
                    "updated_at": "2026-04-11T10:00:00",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.purchases.build_purchases_dashboard",
        lambda conn, reference_date, limit: {
            "module": "purchases",
            "status": "active",
            "summary": {
                "total_entries": 10,
                "this_month_entries": 3,
                "this_month_total_invoice": 18500.0,
                "distinct_suppliers": 2,
            },
            "recent_entries": [
                {
                    "id": 21,
                    "purchase_date": "2026-04-10",
                    "item_name": "Kask",
                    "quantity": 5,
                    "total_invoice_amount": 7500.0,
                    "unit_cost": 1500.0,
                    "supplier": "Moto Tedarik",
                    "invoice_no": "INV-21",
                    "notes": "",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.purchases.build_purchases_form_options",
        lambda item_name=None: {
            "item_options": ["Kask", "Box"],
            "selected_item": item_name or "Kask",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.purchases.build_purchases_management",
        lambda conn, limit, item_name=None, search=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 21,
                    "purchase_date": "2026-04-10",
                    "item_name": "Kask",
                    "quantity": 5,
                    "total_invoice_amount": 7500.0,
                    "unit_cost": 1500.0,
                    "supplier": "Moto Tedarik",
                    "invoice_no": "INV-21",
                    "notes": "",
                }
            ],
        },
    )
    client = _build_app()

    restaurants_dashboard = client.get("/api/restaurants/dashboard")
    restaurants_options = client.get("/api/restaurants/form-options")
    restaurants_records = client.get("/api/restaurants/records")
    sales_dashboard = client.get("/api/sales/dashboard")
    sales_options = client.get("/api/sales/form-options")
    sales_records = client.get("/api/sales/records?lead_source=Referans")
    purchases_dashboard = client.get("/api/purchases/dashboard")
    purchases_options = client.get("/api/purchases/form-options")
    purchases_records = client.get("/api/purchases/records")

    assert restaurants_dashboard.status_code == 200
    assert restaurants_dashboard.json()["summary"]["active_restaurants"] == 21
    assert restaurants_options.status_code == 200
    assert restaurants_options.json()["pricing_models"][0]["label"] == "Saat + Paket"
    assert restaurants_records.status_code == 200
    assert restaurants_records.json()["entries"][0]["branch"] == "Kavacik"
    assert sales_dashboard.status_code == 200
    assert sales_dashboard.json()["summary"]["proposal_stage"] == 6
    assert sales_options.status_code == 200
    assert sales_options.json()["source_options"] == ["Telefon", "Referans"]
    assert sales_records.status_code == 200
    assert sales_records.json()["entries"][0]["restaurant_name"] == "Donerci Celal Usta"
    assert seen_sales_filters["lead_source"] == "Referans"
    assert purchases_dashboard.status_code == 200
    assert purchases_dashboard.json()["summary"]["distinct_suppliers"] == 2
    assert purchases_options.status_code == 200
    assert purchases_options.json()["item_options"] == ["Kask", "Box"]
    assert purchases_records.status_code == 200
    assert purchases_records.json()["entries"][0]["supplier"] == "Moto Tedarik"


def test_equipment_and_reports_routes_smoke(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.equipment.build_equipment_dashboard",
        lambda conn, reference_date, limit: {
            "module": "equipment",
            "status": "active",
            "summary": {
                "total_issues": 7,
                "this_month_issues": 2,
                "installment_rows": 3,
                "total_box_returns": 1,
                "total_box_payout": 450.0,
                "distinct_items": 4,
            },
            "recent_issues": [
                {
                    "id": 1,
                    "personnel_id": 9,
                    "personnel_label": "Ahmet Dursun",
                    "issue_date": "2026-04-11",
                    "item_name": "Kask",
                    "quantity": 1,
                    "unit_cost": 700.0,
                    "unit_sale_price": 900.0,
                    "vat_rate": 20.0,
                    "total_cost": 700.0,
                    "total_sale": 900.0,
                    "gross_profit": 200.0,
                    "installment_count": 3,
                    "sale_type": "Pesin",
                    "notes": "",
                    "auto_source_key": "",
                    "is_auto_record": False,
                }
            ],
            "recent_box_returns": [
                {
                    "id": 2,
                    "personnel_id": 9,
                    "personnel_label": "Ahmet Dursun",
                    "return_date": "2026-04-10",
                    "quantity": 1,
                    "condition_status": "Saglam",
                    "payout_amount": 450.0,
                    "waived": False,
                    "notes": "",
                }
            ],
            "installment_entries": [
                {
                    "deduction_date": "2026-04-15",
                    "personnel_label": "Ahmet Dursun",
                    "deduction_type": "Kask",
                    "amount": 300.0,
                    "notes": "",
                    "auto_source_key": "eq-1",
                }
            ],
            "sales_profit": [
                {
                    "item_name": "Kask",
                    "sold_qty": 1,
                    "total_cost": 700.0,
                    "total_sale": 900.0,
                    "gross_profit": 200.0,
                }
            ],
            "purchase_summary": [
                {
                    "item_name": "Kask",
                    "purchased_qty": 5,
                    "purchased_total": 3500.0,
                    "weighted_unit_cost": 700.0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.build_equipment_form_options",
        lambda conn: {
            "personnel": [{"id": 9, "label": "Ahmet Dursun"}],
            "issue_items": ["Kask", "Box"],
            "sale_type_options": ["Pesin", "Taksit"],
            "return_condition_options": ["Saglam", "Hasarli"],
            "installment_count_options": [1, 2, 3],
            "item_defaults": {
                "Kask": {
                    "default_unit_cost": 700.0,
                    "default_sale_price": 900.0,
                    "default_installment_count": 3,
                    "default_vat_rate": 20.0,
                }
            },
            "selected_personnel_id": None,
            "selected_item": "Kask",
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.build_equipment_issue_management",
        lambda conn, limit, personnel_id=None, item_name=None, search=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 1,
                    "personnel_id": 9,
                    "personnel_label": "Ahmet Dursun",
                    "issue_date": "2026-04-11",
                    "item_name": "Kask",
                    "quantity": 1,
                    "unit_cost": 700.0,
                    "unit_sale_price": 900.0,
                    "vat_rate": 20.0,
                    "total_cost": 700.0,
                    "total_sale": 900.0,
                    "gross_profit": 200.0,
                    "installment_count": 3,
                    "sale_type": "Pesin",
                    "notes": "",
                    "auto_source_key": "",
                    "is_auto_record": False,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.equipment.build_box_return_management",
        lambda conn, limit, personnel_id=None, search=None: {
            "total_entries": 1,
            "entries": [
                {
                    "id": 2,
                    "personnel_id": 9,
                    "personnel_label": "Ahmet Dursun",
                    "return_date": "2026-04-10",
                    "quantity": 1,
                    "condition_status": "Saglam",
                    "payout_amount": 450.0,
                    "waived": False,
                    "notes": "",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.reports.build_reports_dashboard",
        lambda conn, selected_month=None, limit=100: {
            "module": "reports",
            "status": "active",
            "month_options": ["2026-04"],
            "selected_month": selected_month or "2026-04",
            "summary": {
                "selected_month": "2026-04",
                "restaurant_count": 18,
                "courier_count": 92,
                "total_hours": 1820.0,
                "total_packages": 6110.0,
                "total_revenue": 1850000.0,
                "total_personnel_cost": 1320000.0,
                "gross_profit": 530000.0,
                "side_income_net": 42000.0,
            },
            "invoice_entries": [
                {
                    "restaurant": "Burger@ - Kavacik",
                    "pricing_model": "Saat + Paket",
                    "total_hours": 410.0,
                    "total_packages": 1330.0,
                    "net_invoice": 210000.0,
                    "gross_invoice": 252000.0,
                }
            ],
            "cost_entries": [
                {
                    "personnel": "Beytullah Belen",
                    "role": "Kurye",
                    "total_hours": 218.0,
                    "total_packages": 263.0,
                    "total_deductions": 0.0,
                    "net_cost": 59760.0,
                    "cost_model": "Saat + Paket",
                }
            ],
            "profit_entries": [
                {
                    "restaurant": "Burger@ - Kavacik",
                    "pricing_model": "Saat + Paket",
                    "total_hours": 410.0,
                    "total_packages": 1330.0,
                    "net_invoice": 210000.0,
                    "gross_invoice": 252000.0,
                    "direct_personnel_cost": 148000.0,
                    "shared_overhead_cost": 18000.0,
                    "total_personnel_cost": 166000.0,
                    "gross_profit": 86000.0,
                    "profit_margin_percent": 34.1,
                }
            ],
            "model_breakdown": [
                {
                    "pricing_model": "Saat + Paket",
                    "restaurant_count": 8,
                    "total_hours": 1400.0,
                    "total_packages": 5000.0,
                    "gross_invoice": 1100000.0,
                }
            ],
            "top_restaurants": [
                {
                    "restaurant": "Burger@ - Kavacik",
                    "pricing_model": "Saat + Paket",
                    "total_hours": 410.0,
                    "total_packages": 1330.0,
                    "gross_invoice": 252000.0,
                }
            ],
            "top_couriers": [
                {
                    "personnel": "Beytullah Belen",
                    "role": "Kurye",
                    "total_hours": 218.0,
                    "total_deductions": 0.0,
                    "net_cost": 59760.0,
                    "cost_model": "Saat + Paket",
                }
            ],
            "coverage": {
                "covered_restaurant_count": 18,
                "operational_restaurant_count": 21,
            },
            "shared_overhead_entries": [
                {
                    "personnel": "Merve Korkmaz",
                    "role": "Joker",
                    "gross_cost": 72000.0,
                    "total_deductions": 2000.0,
                    "net_cost": 70000.0,
                    "allocated_restaurant_count": 21,
                    "share_per_restaurant": 3333.33,
                }
            ],
            "distribution_entries": [
                {
                    "restaurant": "Burger@ - Kavacik",
                    "personnel": "Beytullah Belen",
                    "role": "Kurye",
                    "total_hours": 218.0,
                    "total_packages": 263.0,
                    "allocated_cost": 59760.0,
                    "allocation_source": "Değişken maliyet",
                }
            ],
            "side_income_entries": [
                {
                    "item": "UTTS Yakıt İndirimi",
                    "revenue": 18000.0,
                    "cost": 0.0,
                    "net_profit": 18000.0,
                },
                {
                    "item": "Partner Kart İndirimi",
                    "revenue": 24000.0,
                    "cost": 0.0,
                    "net_profit": 24000.0,
                },
            ],
            "side_income_snapshot": {
                "fuel_reflection_amount": 125000.0,
                "company_fuel_reflection_amount": 84000.0,
                "utts_fuel_discount_amount": 18000.0,
                "partner_card_discount_amount": 24000.0,
            },
        },
    )
    client = _build_app()

    equipment_dashboard = client.get("/api/equipment/dashboard")
    equipment_options = client.get("/api/equipment/form-options")
    issues = client.get("/api/equipment/issues")
    box_returns = client.get("/api/equipment/box-returns")
    reports_dashboard = client.get("/api/reports/dashboard")

    assert equipment_dashboard.status_code == 200
    assert equipment_dashboard.json()["summary"]["distinct_items"] == 4
    assert equipment_options.status_code == 200
    assert equipment_options.json()["item_defaults"]["Kask"]["default_sale_price"] == 900.0
    assert issues.status_code == 200
    assert issues.json()["entries"][0]["item_name"] == "Kask"
    assert box_returns.status_code == 200
    assert box_returns.json()["entries"][0]["condition_status"] == "Saglam"
    assert reports_dashboard.status_code == 200
    assert reports_dashboard.json()["summary"]["gross_profit"] == 530000.0
    assert reports_dashboard.json()["profit_entries"][0]["gross_profit"] == 86000.0
    assert reports_dashboard.json()["coverage"]["operational_restaurant_count"] == 21
    assert reports_dashboard.json()["shared_overhead_entries"][0]["role"] == "Joker"
    assert reports_dashboard.json()["side_income_snapshot"]["utts_fuel_discount_amount"] == 18000.0
