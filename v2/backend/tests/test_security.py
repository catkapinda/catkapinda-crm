from app.core.security import resolve_allowed_actions


def test_sef_actions_match_streamlit_contract():
    actions = set(resolve_allowed_actions("sef"))

    assert "sales.view" in actions
    assert "sales.create" in actions
    assert "sales.update" in actions
    assert "personnel.status_change" in actions
