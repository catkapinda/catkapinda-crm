from app.core.security import resolve_allowed_actions


def test_sef_actions_match_streamlit_contract():
    actions = set(resolve_allowed_actions("sef"))

    assert "sales.view" in actions
    assert "sales.create" in actions
    assert "sales.update" in actions
    assert "personnel.status_change" in actions


def test_mobile_ops_can_delete_single_attendance_entry_only():
    actions = set(resolve_allowed_actions("mobile_ops"))

    assert "attendance.view" in actions
    assert "attendance.create" in actions
    assert "attendance.update" in actions
    assert "attendance.delete" in actions
    assert "attendance.bulk_delete" not in actions
