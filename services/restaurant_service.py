from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repositories.restaurant_repository import (
    count_restaurant_linked_daily_entries,
    count_restaurant_linked_deductions,
    count_restaurant_linked_personnel,
    delete_restaurant_record,
    fetch_restaurant_management_df,
    insert_restaurant_record,
    update_restaurant_record,
    update_restaurant_status,
)


@dataclass
class RestaurantWorkspacePayload:
    df: Any


def load_restaurant_workspace_payload(conn, *, ensure_dataframe_columns_fn: Callable[[Any, dict[str, Any]], Any]) -> RestaurantWorkspacePayload:
    df = fetch_restaurant_management_df(conn)
    df = ensure_dataframe_columns_fn(
        df,
        {
            "company_title": "",
            "address": "",
            "contact_name": "",
            "contact_phone": "",
            "contact_email": "",
            "tax_office": "",
            "tax_number": "",
        },
    )
    return RestaurantWorkspacePayload(df=df)


def create_restaurant_and_commit(conn, *, restaurant_values: dict[str, Any]) -> str:
    try:
        insert_restaurant_record(conn, restaurant_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Restoran başarıyla eklendi."


def update_restaurant_and_commit(conn, *, restaurant_id: int, restaurant_values: dict[str, Any]) -> str:
    try:
        update_restaurant_record(conn, restaurant_id, restaurant_values)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Restoran kartı başarıyla güncellendi."


def toggle_restaurant_status_and_commit(conn, *, restaurant_id: int, current_active: int) -> str:
    next_active = 0 if int(current_active or 0) == 1 else 1
    try:
        update_restaurant_status(conn, restaurant_id, next_active)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Restoran başarıyla pasife alındı." if next_active == 0 else "Restoran başarıyla aktifleştirildi."


def delete_restaurant_with_guards(conn, *, restaurant_id: int) -> str:
    linked_people = count_restaurant_linked_personnel(conn, restaurant_id)
    linked_entries = count_restaurant_linked_daily_entries(conn, restaurant_id)
    linked_deductions = count_restaurant_linked_deductions(conn, restaurant_id)
    if linked_people or linked_entries or linked_deductions:
        raise ValueError("Bu restorana bağlı personel, puantaj veya kesinti kaydı var. Önce pasife alman daha doğru olur.")

    try:
        delete_restaurant_record(conn, restaurant_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return "Restoran kaydı kalıcı olarak silindi."
