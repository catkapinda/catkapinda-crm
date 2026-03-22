from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st


def fmt_try(v: float) -> str:
    try:
        num = float(v)
    except (TypeError, ValueError):
        return ""
    if abs(num - round(num)) < 0.005:
        s = f"{num:,.0f}"
    else:
        s = f"{num:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"):
        s = s[:-3]
    return f"{s}₺"


def fmt_number(v: float) -> str:
    try:
        num = float(v)
    except (TypeError, ValueError):
        return ""
    if abs(num - round(num)) < 0.005:
        s = f"{num:,.0f}"
    else:
        s = f"{num:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if s.endswith(",00"):
        s = s[:-3]
    return s


def display_mapped_value(value: Any, mapping: dict) -> str:
    if pd.isna(value):
        return ""
    if value in mapping:
        return mapping[value]
    return mapping.get(str(value), value)


def format_display_df(
    df: pd.DataFrame,
    currency_cols: list[str] | None = None,
    percent_cols: list[str] | None = None,
    number_cols: list[str] | None = None,
    rename_map: dict[str, str] | None = None,
    value_maps: dict[str, dict] | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    for col, mapping in (value_maps or {}).items():
        if col in out.columns:
            out[col] = out[col].apply(lambda x: display_mapped_value(x, mapping))
    if rename_map:
        out = out.rename(columns=rename_map)
    for col in currency_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: fmt_try(x) if pd.notna(x) else "")
    for col in percent_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"%{fmt_number(x)}" if pd.notna(x) else "")
    for col in number_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: fmt_number(x) if pd.notna(x) else "")
    return out


def section_intro(title: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="crm-section">
            <h3>{title}</h3>
            <p>{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_text_search(df: pd.DataFrame, columns: list[str], query: str) -> pd.DataFrame:
    if df is None or df.empty or not (query or "").strip():
        return df
    mask = pd.Series(False, index=df.index)
    for col in columns:
        if col in df.columns:
            mask = mask | df[col].fillna("").astype(str).str.contains(query.strip(), case=False, na=False)
    return df[mask].copy()


def render_record_snapshot(title: str, items: list[tuple[str, Any]]) -> None:
    rows = []
    for label, value in items:
        safe_label = html.escape(str(label))
        safe_value = html.escape(str(value if value not in [None, ""] else "-"))
        rows.append(f"<div class='ck-list-row'><span>{safe_label}</span><span class='ck-chip'>{safe_value}</span></div>")
    st.markdown(
        f"<div class='ck-panel'><div class='ck-panel-title'>{html.escape(title)}</div>{''.join(rows)}</div>",
        unsafe_allow_html=True,
    )


def resolve_dashboard_tone(value: Any, default: str = "info") -> str:
    normalized = str(value or "").strip().lower()
    if "aktif" in normalized:
        return "success"
    if "pasif" in normalized:
        return "warning"
    if any(token in normalized for token in ["kritik", "bekleniyor", "negatif", "zarar", "açık", "eksik"]):
        return "critical"
    if any(token in normalized for token in ["izleme", "dikkat", "altında", "finans"]):
        return "warning"
    if any(token in normalized for token in ["sağlam", "stabil", "tamam"]):
        return "success"
    if any(token in normalized for token in ["bilgi", "takip"]):
        return "info"
    return default


def render_dashboard_section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f"<div class='ck-dashboard-section-subtitle'>{html.escape(str(subtitle or ''))}</div>"
        if str(subtitle or "").strip()
        else ""
    )
    st.markdown(
        f"<div class='ck-panel-title'>{html.escape(title)}</div>{subtitle_html}",
        unsafe_allow_html=True,
    )


def render_dashboard_data_grid(
    title: str,
    subtitle: str | None,
    columns: list[str],
    rows: list[dict[str, Any]],
    empty_message: str,
    badge_columns: set[str] | None = None,
    muted_columns: set[str] | None = None,
) -> None:
    render_dashboard_section_header(title, subtitle)
    badge_columns = badge_columns or set()
    muted_columns = muted_columns or set()

    if not rows:
        st.info(empty_message)
        return

    head_html = "".join(
        f"<div class='ck-data-grid-head-item'>{html.escape(str(column))}</div>"
        for column in columns
    )

    row_html = []
    for row in rows:
        cell_html = []
        for column in columns:
            raw_value = row.get(column, "-")
            value_text = html.escape(str(raw_value if raw_value not in [None, ""] else "-"))
            if column in badge_columns:
                tone = resolve_dashboard_tone(raw_value)
                value_html = f"<span class='ck-data-pill ck-data-pill-{tone}'>{value_text}</span>"
            else:
                value_class = "ck-data-cell-value ck-data-cell-value-muted" if column in muted_columns else "ck-data-cell-value"
                value_html = f"<span class='{value_class}'>{value_text}</span>"
            cell_html.append(
                "<div class='ck-data-cell'>"
                f"<div class='ck-data-cell-label'>{html.escape(str(column))}</div>"
                f"{value_html}"
                "</div>"
            )
        row_html.append(f"<div class='ck-data-grid-row'>{''.join(cell_html)}</div>")

    st.markdown(
        (
            f"<div class='ck-data-grid-table' style='--ck-cols:{len(columns)};'>"
            f"<div class='ck-data-grid-head'>{head_html}</div>"
            f"{''.join(row_html)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def build_grid_rows(display_df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if display_df is None or display_df.empty:
        return []
    rows = []
    for _, row in display_df.iterrows():
        rows.append({column: row.get(column, "-") or "-" for column in columns})
    return rows


def render_executive_metrics(
    metrics: list[dict[str, Any]],
    title: str | None = None,
    subtitle: str | None = None,
) -> None:
    title_html = ""
    if title or subtitle:
        title_html = (
            "<div class='ck-exec-strip-head'>"
            f"<div><div class='ck-exec-strip-title'>{html.escape(str(title or ''))}</div>"
            f"<div class='ck-exec-strip-copy'>{html.escape(str(subtitle or ''))}</div></div>"
            "</div>"
        )

    cards_html = []
    for metric in metrics:
        label = html.escape(str(metric.get("label", "") or ""))
        value = html.escape(str(metric.get("value", "-") or "-"))
        note = html.escape(str(metric.get("note", "") or ""))
        tone = str(metric.get("tone", "neutral") or "neutral").strip().lower()
        tone_class = f" ck-exec-card-{tone}" if tone in {"positive", "warning", "critical"} else ""
        note_html = f"<div class='ck-exec-card-note'>{note}</div>" if note else ""
        cards_html.append(
            f"<div class='ck-exec-card{tone_class}'>"
            f"<div class='ck-exec-card-label'>{label}</div>"
            f"<div class='ck-exec-card-value'>{value}</div>"
            f"{note_html}"
            "</div>"
        )

    st.markdown(
        f"<div class='ck-exec-strip'>{title_html}<div class='ck-exec-strip-grid'>{''.join(cards_html)}</div></div>",
        unsafe_allow_html=True,
    )


def render_alert_stack(title: str, items: list[dict[str, Any]], border: bool = True) -> None:
    tone_label_map = {
        "critical": "Kritik",
        "warning": "Dikkat",
        "info": "Bilgi",
        "success": "Stabil",
    }

    with st.container(border=border):
        st.markdown(f"**{title}**")
        normalized_items = items or [
            {
                "tone": "success",
                "badge": "Stabil",
                "title": "Bugün için kritik aksiyon görünmüyor.",
                "detail": "Operasyon akışında öne çıkan bir alarm tespit edilmedi.",
            }
        ]

        for item in normalized_items:
            tone = str(item.get("tone", "info") or "info").strip().lower()
            tone_label = tone_label_map.get(tone, "Bilgi")
            badge_label = str(item.get("badge", "Bilgi") or "Bilgi").strip()
            title_text = str(item.get("title", "-") or "-").strip()
            detail_text = str(item.get("detail", "") or "").strip()

            with st.container(border=True):
                top_left, top_right = st.columns([1, 0.35])
                top_left.markdown(f"**{title_text}**")
                top_right.caption(f"{tone_label} | {badge_label}")
                if detail_text:
                    st.caption(detail_text)


def render_management_hero(kicker: str, title: str, subtitle: str, stats: list[tuple[str, Any]]) -> None:
    stat_cards_html = "".join(
        (
            "<div class='ck-hero-stat'>"
            f"<div class='ck-hero-value'>{html.escape(str(value))}</div>"
            f"<div class='ck-hero-label'>{html.escape(str(label))}</div>"
            "</div>"
        )
        for label, value in stats
    )
    hero_html = (
        "<div class='ck-hero'>"
        f"<div class='ck-hero-kicker'>{html.escape(kicker)}</div>"
        f"<div class='ck-hero-title'>{html.escape(title)}</div>"
        f"<div class='ck-hero-subtitle'>{html.escape(subtitle)}</div>"
        f"<div class='ck-hero-grid'>{stat_cards_html}</div>"
        "</div>"
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def render_tab_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="ck-tab-header">
            <div class="ck-tab-header-title">{html.escape(title)}</div>
            <div class="ck-tab-header-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workspace_loading_shell(menu_label: str) -> None:
    safe_menu_label = html.escape(str(menu_label or "çalışma alanı"))
    st.markdown(
        f"""
        <div class="ck-workspace-shell">
            <div class="ck-workspace-shell-kicker">Panel Hazırlanıyor</div>
            <div class="ck-workspace-shell-title">{safe_menu_label} açılıyor.</div>
            <div class="ck-workspace-shell-text">Oturum doğrulandı. İçerik ve operasyon verileri yükleniyor.</div>
            <div class="ck-workspace-shell-loader">
                <div class="ck-workspace-shell-loader-bar"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_card(title: str, subtitle: str, highlight: bool = False) -> None:
    class_name = "ck-action-card ck-action-card-highlight" if highlight else "ck-action-card"
    st.markdown(
        f"""
        <div class="{class_name}">
            <div class="ck-action-card-title">{html.escape(title)}</div>
            <div class="ck-action-card-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_field_label(label: str, required: bool = False) -> None:
    required_html = ' <span class="ck-required-star">*</span>' if required else ""
    st.markdown(
        f'<div class="ck-field-label">{html.escape(label)}{required_html}</div>',
        unsafe_allow_html=True,
    )
