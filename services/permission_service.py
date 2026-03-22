from __future__ import annotations

from rules.permission_rules import ACTION_LABELS, MENU_TO_ACTION, ROLE_ACTIONS


class PermissionDeniedError(PermissionError):
    """Raised when the current role is not allowed to perform an action."""


def get_allowed_menu_items(role: str) -> list[str]:
    normalized_role = str(role or "").strip()
    allowed_actions = ROLE_ACTIONS.get(normalized_role, set())
    return [menu for menu, action in MENU_TO_ACTION.items() if action in allowed_actions]


def can_access_menu(role: str, menu: str) -> bool:
    action_key = MENU_TO_ACTION.get(str(menu or "").strip())
    if not action_key:
        return False
    return can_perform_action(role, action_key)


def can_perform_action(role: str, action_key: str) -> bool:
    normalized_role = str(role or "").strip()
    if not normalized_role:
        return False
    return str(action_key or "").strip() in ROLE_ACTIONS.get(normalized_role, set())


def get_permission_denied_message(action_key: str) -> str:
    label = ACTION_LABELS.get(str(action_key or "").strip(), "bu işlem")
    return f"{label.capitalize()} yetkiniz yok."


def require_action_access(role: str, action_key: str, *, message: str | None = None) -> None:
    if can_perform_action(role, action_key):
        return
    raise PermissionDeniedError(message or get_permission_denied_message(action_key))


def require_menu_access(role: str, menu: str) -> None:
    if can_access_menu(role, menu):
        return
    raise PermissionDeniedError("Bu sayfaya erişim yetkiniz yok.")
