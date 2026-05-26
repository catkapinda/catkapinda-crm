"""Restoran tahsilat takibi servisi.

restaurant_invoices tablosu üzerinden çalışır. V2'deki restaurant_collections
mantığı: ay bazlı tahsilat durumu (Bekleyen / Kısmi / Tahsil Edildi / Geciken),
beklenen tutar, tahsil edilen tutar, vade ve son temas tarihi.

Fatura tutarı otomatik hesaplanır (daily_entries × restoran tarifesi).
Kullanıcı bir kayıt oluşturup invoice_amount manuel girerse, manuel tutar
döner; aksi halde puantajdan türetilen tahmini tutar gösterilir.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.restaurant_reports import get_restaurant_reports


STATUS_OPTIONS: list[str] = [
    "Bekliyor",
    "Kısmi Tahsilat",
    "Tahsil Edildi",
    "Geciken",
    "İptal",
]

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _normalize_period(value: str | None) -> str:
    p = (value or "").strip()
    if not _PERIOD_RE.match(p):
        raise ValueError("Dönem YYYY-AA formatında olmalı (örn. 2026-04).")
    return p


def _compute_auto_invoice_map(period: str) -> dict[int, dict]:
    """Restoran tarife modeline + puantaj verilerine göre beklenen fatura.

    Pricing model'lerine göre hesap:
      - 'Sabit'/'Aylık Sabit'/fixed → fixed_monthly_fee
      - 'Saatlik'/'Hourly' → SUM(worked_hours) × hourly_rate
      - 'Paketli'/'Package' → SUM(package_count) × package_rate
      - 'Eşikli'/'Threshold' → kurye başına eşik altı/üstü
        farklı tarifeyle hesap
      - 'Karma'/'Mixed' → saat × hourly + paket × package
      - Tanımsız → mevcut alanlara göre auto-tahmin

    Returns:
        { restaurant_id: {
            'auto_invoice_excl_vat': float,   # KDV hariç
            'auto_invoice_incl_vat': float,   # KDV dahil
            'auto_hours': float,
            'auto_packages': int,
            'auto_vat_rate': float,
            'auto_basis': str,   # 'fixed' | 'hourly' | 'package' | 'mixed' | 'threshold'
        } }
    """
    out: dict[int, dict] = {}

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Restoran tarifeleri
            cur.execute(
                """
                SELECT
                    id, brand, branch,
                    COALESCE(pricing_model, '') AS pricing_model,
                    COALESCE(hourly_rate, 0)::float AS hourly_rate,
                    COALESCE(package_rate, 0)::float AS package_rate,
                    COALESCE(package_threshold, 0)::int AS package_threshold,
                    COALESCE(package_rate_low, 0)::float AS package_rate_low,
                    COALESCE(package_rate_high, 0)::float AS package_rate_high,
                    COALESCE(fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                    COALESCE(vat_rate, 20)::float AS vat_rate
                FROM restaurants
                WHERE active = 1
                """
            )
            rests = [dict(r) for r in cur.fetchall()]

            # Puantaj toplamı (restoran×ay): saat + paket
            cur.execute(
                """
                SELECT
                    restaurant_id,
                    COALESCE(SUM(worked_hours), 0)::float AS total_hours,
                    COALESCE(SUM(package_count), 0)::int AS total_packages
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                GROUP BY restaurant_id
                """,
                (period,),
            )
            entries_by_rest = {
                int(r["restaurant_id"]): {
                    "total_hours": float(r["total_hours"] or 0),
                    "total_packages": int(r["total_packages"] or 0),
                }
                for r in cur.fetchall()
            }

            # Eşikli modelde her kurye için ayrı paket toplamı gerekli
            # (eşik kurye bazında uygulanır)
            cur.execute(
                """
                SELECT
                    restaurant_id,
                    actual_personnel_id AS personnel_id,
                    COALESCE(SUM(package_count), 0)::int AS pkg
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                  AND actual_personnel_id IS NOT NULL
                GROUP BY restaurant_id, actual_personnel_id
                """,
                (period,),
            )
            per_courier: dict[int, list[int]] = {}
            for r in cur.fetchall():
                per_courier.setdefault(int(r["restaurant_id"]), []).append(int(r["pkg"]))

    for r in rests:
        rid = int(r["id"])
        model = str(r.get("pricing_model") or "").lower()
        hourly_rate = float(r["hourly_rate"])
        package_rate = float(r["package_rate"])
        threshold = int(r["package_threshold"])
        rate_low = float(r["package_rate_low"])
        rate_high = float(r["package_rate_high"])
        fixed_fee = float(r["fixed_monthly_fee"])
        vat_rate = float(r["vat_rate"])

        entry = entries_by_rest.get(rid, {})
        total_hours = float(entry.get("total_hours") or 0)
        total_packages = int(entry.get("total_packages") or 0)
        courier_pkgs = per_courier.get(rid, [])

        # ─── Model belirleme ──────────────────────────────────────────
        is_fixed = ("sabit" in model or "fixed" in model or "aylık" in model
                    or "monthly" in model)
        is_threshold = ("eşik" in model or "esik" in model or "threshold" in model
                        or (threshold > 0 and rate_low > 0 and rate_high > 0))
        is_hourly = ("saat" in model or "hour" in model)
        is_package = ("paket" in model or "package" in model)
        is_mixed = ("karma" in model or "mixed" in model)

        # Auto-fallback: eğer model boş ise, dolu alanlara göre seç
        if not (is_fixed or is_threshold or is_hourly or is_package or is_mixed):
            if fixed_fee > 0 and hourly_rate == 0 and package_rate == 0:
                is_fixed = True
            elif threshold > 0 and rate_low > 0:
                is_threshold = True
            elif hourly_rate > 0 and package_rate > 0:
                is_mixed = True
            elif hourly_rate > 0:
                is_hourly = True
            elif package_rate > 0:
                is_package = True

        # ─── Hesap ────────────────────────────────────────────────────
        excl = 0.0
        basis = "auto"
        if is_fixed and fixed_fee > 0:
            excl = fixed_fee
            basis = "fixed"
        elif is_threshold and rate_low > 0:
            # Her kurye için: eşik altı × low + eşik üstü × high
            total = 0.0
            for pkg in courier_pkgs:
                if pkg <= threshold:
                    total += pkg * rate_low
                else:
                    total += threshold * rate_low + (pkg - threshold) * rate_high
            excl = total
            basis = "threshold"
        elif is_mixed:
            excl = total_hours * hourly_rate + total_packages * package_rate
            basis = "mixed"
        elif is_hourly:
            excl = total_hours * hourly_rate
            basis = "hourly"
        elif is_package:
            excl = total_packages * package_rate
            basis = "package"
        else:
            # Fallback: en yüksek kombinasyon
            if fixed_fee > 0:
                excl = fixed_fee
                basis = "fixed"

        vat_amt = round(excl * vat_rate / 100, 2)
        incl = round(excl + vat_amt, 2)

        out[rid] = {
            "auto_invoice_excl_vat": round(excl, 2),
            "auto_invoice_incl_vat": incl,
            "auto_hours": round(total_hours, 2),
            "auto_packages": total_packages,
            "auto_vat_rate": vat_rate,
            "auto_basis": basis,
        }
    return out


def list_collections(
    *,
    period: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Tahsilat listesi — bir dönem için her aktif restoran için bir satır.

    Manuel kayıt yoksa: puantajdan otomatik hesaplanan tutar gösterilir
    (sanal 'Bekliyor' kaydı). Manuel kayıt varsa, kullanıcının girdiği
    invoice_amount geçerlidir (override).
    """
    period = _normalize_period(period) if period else None

    # Restoran listesi (aktif)
    rest_sql = """
        SELECT id, brand, branch
        FROM restaurants
        WHERE active = 1
        ORDER BY brand, branch
    """
    # Mevcut tahsilat kayıtları
    coll_sql = """
        SELECT
            id, restaurant_id, period AS collection_month,
            invoice_no,
            COALESCE(amount_incl_vat, amount_excl_vat, 0)::float AS invoice_amount,
            COALESCE(amount_excl_vat, 0)::float AS invoice_amount_excl_vat,
            COALESCE(paid_amount, 0)::float AS collected_amount,
            status, paid_at, due_date::text AS due_date,
            last_contact_date::text AS last_contact_date,
            COALESCE(responsible_name, '') AS responsible_name,
            COALESCE(notes, '') AS note,
            issued_at, paid_at
        FROM restaurant_invoices
        WHERE 1=1
    """
    coll_params: list[Any] = []
    if period:
        coll_sql += " AND period = %s"
        coll_params.append(period)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(rest_sql)
            restaurants = [dict(r) for r in cur.fetchall()]
            cur.execute(coll_sql, coll_params)
            collections = [dict(r) for r in cur.fetchall()]

    # Otomatik hesap (puantajdan)
    auto_map = _compute_auto_invoice_map(period) if period else {}

    # restaurant_id → collection map
    by_rest: dict[int, dict] = {}
    for c in collections:
        by_rest[int(c["restaurant_id"])] = c

    today = date.today()
    items: list[dict] = []
    for r in restaurants:
        rid = int(r["id"])
        auto = auto_map.get(rid, {})
        auto_incl = float(auto.get("auto_invoice_incl_vat") or 0)
        auto_excl = float(auto.get("auto_invoice_excl_vat") or 0)
        auto_vat_rate = float(auto.get("auto_vat_rate") or 20)
        auto_basis = str(auto.get("auto_basis") or "auto")
        auto_hours = float(auto.get("auto_hours") or 0)
        auto_packages = int(auto.get("auto_packages") or 0)
        existing = by_rest.get(rid)
        if existing:
            row = dict(existing)
            row["brand"] = r["brand"]
            row["branch"] = r["branch"]
            # Eğer manuel kayıt 0 ise auto'yu göster, ama 'auto' bayrağı koy
            inv = float(row.get("invoice_amount") or 0)
            if inv <= 0 and auto_incl > 0:
                row["invoice_amount"] = auto_incl
                row["invoice_amount_excl_vat"] = auto_excl
                row["is_auto_invoice"] = True
            else:
                row["is_auto_invoice"] = False
            col = float(row.get("collected_amount") or 0)
            row["remaining_amount"] = max(0.0, float(row["invoice_amount"]) - col)
            row["auto_invoice_amount"] = auto_incl
            row["auto_invoice_excl_vat"] = auto_excl
            row["auto_vat_rate"] = auto_vat_rate
            row["auto_basis"] = auto_basis
            row["auto_hours"] = auto_hours
            row["auto_packages"] = auto_packages
            row.setdefault("vat_rate", auto_vat_rate)
            # Geciken hesabı: due_date geçti + status Tahsil Edildi değil
            try:
                if row.get("due_date") and row["status"] != "Tahsil Edildi":
                    if date.fromisoformat(row["due_date"]) < today and row["remaining_amount"] > 0:
                        row["is_overdue"] = True
                    else:
                        row["is_overdue"] = False
                else:
                    row["is_overdue"] = False
            except Exception:
                row["is_overdue"] = False
        else:
            # Sanal kayıt — henüz tahsilat girilmemiş; puantajdan otomatik
            row = {
                "id": None,
                "restaurant_id": rid,
                "collection_month": period,
                "brand": r["brand"],
                "branch": r["branch"],
                "status": "Bekliyor",
                "invoice_amount": auto_incl,
                "invoice_amount_excl_vat": auto_excl,
                "vat_rate": auto_vat_rate,
                "collected_amount": 0,
                "remaining_amount": auto_incl,
                "due_date": None,
                "last_contact_date": None,
                "responsible_name": "",
                "note": "",
                "is_overdue": False,
                "paid_at": None,
                "is_auto_invoice": auto_incl > 0,
                "auto_invoice_amount": auto_incl,
                "auto_invoice_excl_vat": auto_excl,
                "auto_vat_rate": auto_vat_rate,
                "auto_basis": auto_basis,
                "auto_hours": auto_hours,
                "auto_packages": auto_packages,
            }
        items.append(row)

    # Filtre
    if status:
        items = [x for x in items if (x.get("status") or "") == status]
    if search and search.strip():
        q = search.strip().lower()
        items = [
            x for x in items
            if q in (x.get("brand") or "").lower()
            or q in (x.get("branch") or "").lower()
            or q in (x.get("responsible_name") or "").lower()
            or q in (x.get("note") or "").lower()
        ]

    return items


def summary(period: str) -> dict:
    """Bir dönem için özet KPI'lar."""
    items = list_collections(period=period)
    today = date.today()
    total_invoice = sum(float(x.get("invoice_amount") or 0) for x in items)
    total_collected = sum(float(x.get("collected_amount") or 0) for x in items)
    total_open = sum(float(x.get("remaining_amount") or 0) for x in items)
    overdue = [x for x in items if x.get("is_overdue")]
    overdue_amount = sum(float(x.get("remaining_amount") or 0) for x in overdue)
    collected_count = sum(1 for x in items if x.get("status") == "Tahsil Edildi")
    pending_count = sum(1 for x in items if x.get("status") in ("Bekliyor", "Kısmi Tahsilat"))
    return {
        "period": period,
        "total_invoice": total_invoice,
        "total_collected": total_collected,
        "total_open": total_open,
        "overdue_amount": overdue_amount,
        "overdue_count": len(overdue),
        "collected_count": collected_count,
        "pending_count": pending_count,
        "restaurant_count": len(items),
        "today": today.isoformat(),
    }


def upsert_collection(payload: dict) -> dict:
    """Bir restoran×dönem için tahsilatı oluştur veya güncelle.

    Otomatik status: collected_amount >= invoice_amount → 'Tahsil Edildi'
                     collected_amount > 0 → 'Kısmi Tahsilat'
                     yoksa kullanıcının verdiği status.
    """
    rid = int(payload.get("restaurant_id") or 0)
    if not rid:
        raise ValueError("Restoran seçilmeli.")
    period = _normalize_period(payload.get("collection_month") or payload.get("period"))

    invoice_amount = float(payload.get("invoice_amount") or 0)
    collected_amount = float(payload.get("collected_amount") or 0)
    if invoice_amount < 0 or collected_amount < 0:
        raise ValueError("Tutarlar negatif olamaz.")
    if collected_amount > invoice_amount and invoice_amount > 0:
        collected_amount = invoice_amount  # cap

    status = (payload.get("status") or "Bekliyor").strip() or "Bekliyor"
    if status not in STATUS_OPTIONS:
        raise ValueError(f"Geçersiz durum: {status}")

    # Otomatik status hesabı (override edilebilir ama 'Tahsil Edildi' tetikler)
    if invoice_amount > 0 and collected_amount >= invoice_amount:
        status = "Tahsil Edildi"
    elif collected_amount > 0 and status == "Bekliyor":
        status = "Kısmi Tahsilat"

    due_date = (payload.get("due_date") or None) or None
    last_contact = (payload.get("last_contact_date") or None) or None
    payment_date = (payload.get("payment_date") or None) or None
    responsible = (payload.get("responsible_name") or "").strip()
    note = (payload.get("note") or payload.get("notes") or "").strip()

    # paid_at: payment_date varsa veya status Tahsil Edildi
    paid_at = payment_date if payment_date else None
    if status == "Tahsil Edildi" and not paid_at:
        paid_at = date.today().isoformat()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO restaurant_invoices
                    (restaurant_id, period, invoice_no, amount_excl_vat,
                     vat_amount, amount_incl_vat, status,
                     paid_at, paid_amount, notes,
                     due_date, last_contact_date, responsible_name)
                VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (restaurant_id, period) DO UPDATE SET
                    invoice_no = COALESCE(EXCLUDED.invoice_no, restaurant_invoices.invoice_no),
                    amount_excl_vat = EXCLUDED.amount_excl_vat,
                    amount_incl_vat = EXCLUDED.amount_incl_vat,
                    status = EXCLUDED.status,
                    paid_at = EXCLUDED.paid_at,
                    paid_amount = EXCLUDED.paid_amount,
                    notes = EXCLUDED.notes,
                    due_date = EXCLUDED.due_date,
                    last_contact_date = EXCLUDED.last_contact_date,
                    responsible_name = EXCLUDED.responsible_name
                RETURNING id
                """,
                (
                    rid, period,
                    (payload.get("invoice_no") or None),
                    invoice_amount,
                    invoice_amount,  # amount_incl_vat = aynı (KDV ayrı tutmuyoruz)
                    status,
                    paid_at,
                    collected_amount,
                    note,
                    due_date,
                    last_contact,
                    responsible,
                ),
            )
            new_id = cur.fetchone()["id"]
            conn.commit()
    # Updated row döndür
    items = list_collections(period=period)
    for x in items:
        if int(x.get("restaurant_id") or 0) == rid:
            return x
    return {"id": new_id, "restaurant_id": rid, "period": period, "status": status}


def delete_collection(collection_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM restaurant_invoices WHERE id = %s",
                (collection_id,),
            )
            if cur.rowcount == 0:
                raise LookupError("Tahsilat kaydı bulunamadı.")
            conn.commit()
