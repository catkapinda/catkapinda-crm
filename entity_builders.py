from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def ensure_dataframe_columns(df: pd.DataFrame, defaults: dict[str, Any]) -> pd.DataFrame:
    work = df.copy()
    for column_name, default_value in defaults.items():
        if column_name not in work.columns:
            work[column_name] = default_value
    return work


def build_restaurant_hero_stats(
    df: pd.DataFrame,
    *,
    safe_int_fn: Callable[[Any, int], int],
) -> list[tuple[str, Any]]:
    if df is None or df.empty:
        return [
            ("Toplam Şube", 0),
            ("Aktif Şube", 0),
            ("Saatlik + Paket", 0),
            ("Eşikli Paket", 0),
            ("Sadece Saatlik", 0),
            ("Sabit Aylık", 0),
        ]

    active_count = int(df["active"].apply(lambda value: safe_int_fn(value, 0)).sum())
    return [
        ("Toplam Şube", len(df)),
        ("Aktif Şube", active_count),
        ("Saatlik + Paket", int((df["pricing_model"] == "hourly_plus_package").sum())),
        ("Eşikli Paket", int((df["pricing_model"] == "threshold_package").sum())),
        ("Sadece Saatlik", int((df["pricing_model"] == "hourly_only").sum())),
        ("Sabit Aylık", int((df["pricing_model"] == "fixed_monthly").sum())),
    ]


def build_restaurant_list_rows(
    filtered_df: pd.DataFrame,
    *,
    pricing_model_labels: dict[str, str],
    active_status_labels: dict[Any, str],
    fmt_number_fn: Callable[[Any], str],
) -> list[dict[str, Any]]:
    return [
        {
            "Şube": f"{row['brand']} - {row['branch']}",
            "Fiyat Modeli": pricing_model_labels.get(row["pricing_model"], row["pricing_model"]),
            "Kadro": fmt_number_fn(row["target_headcount"]),
            "Yetkili": row["contact_name"] or "-",
            "Durum": active_status_labels.get(row["active"], row["active"]),
        }
        for _, row in filtered_df.iterrows()
    ]


def build_restaurant_snapshot_items(
    selected_row: Any,
    *,
    pricing_model_labels: dict[str, str],
    active_status_labels: dict[Any, str],
    safe_int_fn: Callable[[Any, int], int],
) -> list[tuple[str, Any]]:
    return [
        ("Marka", selected_row["brand"] or "-"),
        ("Şube", selected_row["branch"] or "-"),
        ("Fiyat Modeli", pricing_model_labels.get(selected_row["pricing_model"], selected_row["pricing_model"])),
        ("Durum", active_status_labels.get(selected_row["active"], selected_row["active"])),
        ("Hedef Kadro", safe_int_fn(selected_row["target_headcount"], 0)),
        ("Yetkili", selected_row["contact_name"] or "-"),
        ("Ünvan", selected_row["company_title"] or "-"),
    ]


def build_personnel_hero_stats(
    df: pd.DataFrame,
    *,
    management_role_options: list[str],
) -> list[tuple[str, Any]]:
    if df is None or df.empty:
        return [
            ("Toplam Personel", 0),
            ("Aktif Personel", 0),
            ("Kurye", 0),
            ("Joker + Yönetim", 0),
        ]

    active_count = int((df["status"] == "Aktif").sum())
    courier_count = int((df["role"] == "Kurye").sum())
    management_count = int(df["role"].isin(["Joker", *management_role_options]).sum())
    return [
        ("Toplam Personel", len(df)),
        ("Aktif Personel", active_count),
        ("Kurye", courier_count),
        ("Joker + Yönetim", management_count),
    ]


def build_personnel_list_rows(filtered_df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "Personel": row["full_name"] or "-",
            "Rol": row["role"] or "-",
            "Ana Restoran": row["restoran"] or "-",
            "Motor": row["vehicle_type"] or "-",
            "Durum": row["status"] or "-",
        }
        for _, row in filtered_df.iterrows()
    ]


def build_personnel_preview_options(df: pd.DataFrame) -> dict[str, int]:
    return {
        f"{row['full_name']} | {row['role']} | Kod: {row['person_code'] or '-'}": int(row["id"])
        for _, row in df.iterrows()
    }


def build_personnel_recent_snapshot_items(
    row: Any,
    *,
    motor_rental_summary_fn: Callable[[Any], str],
    motor_purchase_summary_fn: Callable[[Any], str],
) -> list[tuple[str, Any]]:
    return [
        ("Ad Soyad", row["full_name"] or "-"),
        ("Kod", row["person_code"] or "-"),
        ("Rol", row["role"] or "-"),
        ("Durum", row["status"] or "-"),
        ("Ana Restoran", row["restoran"] or "-"),
        ("Motor Kirası", motor_rental_summary_fn(row)),
        ("Çat Kapında Motor Satışı", motor_purchase_summary_fn(row)),
        ("Acil Durum Kişisi", row["emergency_contact_name"] or "-"),
    ]


def build_personnel_preview_snapshot_items(
    row: Any,
    *,
    motor_rental_summary_fn: Callable[[Any], str],
    motor_purchase_summary_fn: Callable[[Any], str],
) -> list[tuple[str, Any]]:
    return [
        ("Kod", row["person_code"] or "-"),
        ("Rol", row["role"] or "-"),
        ("Durum", row["status"] or "-"),
        ("Ana Restoran", row["restoran"] or "-"),
        ("Plaka", row["current_plate"] or "-"),
        ("Motor Kirası", motor_rental_summary_fn(row)),
        ("Çat Kapında Motor Satışı", motor_purchase_summary_fn(row)),
        ("Acil Durum Kişisi", row["emergency_contact_name"] or "-"),
    ]
