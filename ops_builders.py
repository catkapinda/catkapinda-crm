from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def filter_deductions_by_source(raw_df: pd.DataFrame, source_filter: str) -> pd.DataFrame:
    filtered_raw_df = raw_df.copy()
    if filtered_raw_df.empty:
        return filtered_raw_df

    source_key_series = filtered_raw_df["auto_source_key"].fillna("").astype(str).str.strip()
    if source_filter == "Manuel Kayıtlar":
        return filtered_raw_df[source_key_series == ""].copy()
    return filtered_raw_df


def get_deduction_source_filter_caption(source_filter: str) -> str:
    captions = {
        "Manuel Kayıtlar": "Yalnızca manuel girilmiş kesintiler gösteriliyor.",
    }
    return captions.get(source_filter, "")


def build_auto_deduction_warning_text(
    auto_source_key: Any,
    *,
    describe_auto_source_key_fn: Callable[[Any], str],
) -> str:
    return (
        f"Bu kayıt {describe_auto_source_key_fn(auto_source_key)} akışından kalan eski otomatik kayıttır. "
        "Bu dönem için kesintileri manuel yönetin; gerekirse bu kaydı silip doğru tutarı yeniden girin."
    )


def build_deduction_grid_rows(deductions_display_df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "Tarih": row["Tarih"],
            "Personel": row["Personel"],
            "Tür": row["Kesinti Türü"],
            "Tutar": row["Tutar"],
            "Kaynak": row["Kaynak"],
            "Açıklama": row["Açıklama"] or "-",
        }
        for _, row in deductions_display_df.iterrows()
    ]


def build_bulk_deduction_option_map(
    manual_deductions_df: pd.DataFrame,
    *,
    fmt_try_fn: Callable[[Any], str],
) -> dict[str, int]:
    return {
        f"{row['deduction_date']} | {row['personel']} | {row['deduction_type']} | {fmt_try_fn(row['amount'])} | ID:{int(row['id'])}": int(row["id"])
        for _, row in manual_deductions_df.iterrows()
    }


def build_deduction_option_map(
    raw_df: pd.DataFrame,
    *,
    fmt_try_fn: Callable[[Any], str],
) -> dict[str, int]:
    return {
        f"{row['deduction_date']} | {row['personel']} | {row['deduction_type']} | {fmt_try_fn(row['amount'])} | ID:{int(row['id'])}": int(row["id"])
        for _, row in raw_df.iterrows()
    }


def build_purchase_grid_rows(purchases_display_df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "Tarih": row["Tarih"],
            "Ürün": row["Ürün"],
            "Adet": row["Adet"],
            "Toplam Fatura": row["Toplam Fatura"],
            "Birim Maliyet": row["Birim Maliyet"],
            "Tedarikçi": row["Tedarikçi"] or "-",
        }
        for _, row in purchases_display_df.iterrows()
    ]


def build_purchase_option_map(
    purchases_df: pd.DataFrame,
    *,
    fmt_try_fn: Callable[[Any], str],
) -> dict[str, int]:
    return {
        f"{row['purchase_date']} | {row['item_name']} | {fmt_try_fn(row['total_invoice_amount'])} | ID:{int(row['id'])}": int(row["id"])
        for _, row in purchases_df.iterrows()
    }
