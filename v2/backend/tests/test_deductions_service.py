from datetime import date

from app.services.deductions import _build_management_entry


def test_unknown_deduction_type_does_not_show_maintenance_caption():
    entry = _build_management_entry(
        {
            "id": 1,
            "personnel_id": 10,
            "personnel_label": "Kurye",
            "deduction_date": date(2026, 4, 10),
            "deduction_type": "Zimmet Taksiti",
            "amount": 1300,
            "notes": "",
            "auto_source_key": "",
        }
    )

    assert entry.deduction_type == "Zimmet Taksiti"
    assert entry.type_caption == ""
