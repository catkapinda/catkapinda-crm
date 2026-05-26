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


def _get_period_restaurants(period: str) -> list[dict]:
    """Bir dönem için ilgili restoran kümesi.

    Bir restoran, şu durumlardan biri sağlanıyorsa o ay için listelenir:
      • active = 1 (şu an aktif)
      • o dönemde daily_entries kaydı var (puantaj girilmiş)
      • o dönem için restaurant_invoices kaydı var (manuel fatura/tahsilat)

    Bu sayede Chinese Express gibi sonradan pasife alınan restoranlar
    da aktif olduğu aylarda görünür.
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                WITH active_or_seen AS (
                    SELECT id, brand, branch,
                           COALESCE(pricing_model, '') AS pricing_model,
                           COALESCE(hourly_rate, 0)::float AS hourly_rate,
                           COALESCE(package_rate, 0)::float AS package_rate,
                           COALESCE(package_threshold, 0)::int AS package_threshold,
                           COALESCE(package_rate_low, 0)::float AS package_rate_low,
                           COALESCE(package_rate_high, 0)::float AS package_rate_high,
                           COALESCE(fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                           COALESCE(vat_rate, 20)::float AS vat_rate,
                           active
                    FROM restaurants
                    WHERE active = 1
                       OR id IN (
                            SELECT DISTINCT restaurant_id
                            FROM daily_entries
                            WHERE LEFT(entry_date::text, 7) = %s
                              AND restaurant_id IS NOT NULL
                       )
                       OR id IN (
                            SELECT DISTINCT restaurant_id
                            FROM restaurant_invoices
                            WHERE period = %s
                              AND restaurant_id IS NOT NULL
                       )
                )
                SELECT * FROM active_or_seen
                ORDER BY brand, branch
                """,
                (period, period),
            )
            return [dict(r) for r in cur.fetchall()]


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

    # Period-aware restoran havuzu (aktif + o ay aktif olanlar)
    rests = _get_period_restaurants(period)
    rest_by_id = {int(r["id"]): r for r in rests}

    if not rest_by_id:
        return out

    # Tarih-bazlı tarife: her entry için entry_date'de geçerli olan
    # restaurant_pricing_history satırı LATERAL JOIN ile alınır.
    # Migration koşulmadıysa veya bir sebepten patarsa, fallback olarak
    # restaurants tablosunun MEVCUT tarifeleriyle hesap yapılır.
    entries: list[dict] = []
    use_history_rates = True
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # İki kademeli fallback:
                #   1. restaurant_pricing_history (tarihsel doğru tarife)
                #   2. restaurants (current — history satırı yoksa)
                #   3. Hardcoded default (her ikisi de NULL ise)
                # Celal Usta gibi history satırı olmayan restoranlar için bu
                # önemli; eskiden COALESCE 0'a düşüyordu, fatura 0 çıkıyordu.
                cur.execute(
                    """
                    SELECT
                        de.restaurant_id,
                        de.actual_personnel_id,
                        COALESCE(de.worked_hours, 0)::float AS hours,
                        COALESCE(de.package_count, 0)::int AS packages,
                        h.effective_from,
                        COALESCE(h.pricing_model, r.pricing_model, '') AS pricing_model,
                        COALESCE(h.hourly_rate, r.hourly_rate, 0)::float AS hourly_rate,
                        COALESCE(h.package_rate, r.package_rate, 0)::float AS package_rate,
                        COALESCE(h.package_threshold, r.package_threshold, 0)::int AS package_threshold,
                        COALESCE(h.package_rate_low, r.package_rate_low, 0)::float AS package_rate_low,
                        COALESCE(h.package_rate_high, r.package_rate_high, 0)::float AS package_rate_high,
                        COALESCE(h.fixed_monthly_fee, r.fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                        COALESCE(h.vat_rate, r.vat_rate, 20)::float AS vat_rate
                    FROM daily_entries de
                    LEFT JOIN restaurants r ON r.id = de.restaurant_id
                    LEFT JOIN LATERAL (
                        SELECT *
                        FROM restaurant_pricing_history ph
                        WHERE ph.restaurant_id = de.restaurant_id
                          AND ph.effective_from <= de.entry_date::date
                        ORDER BY ph.effective_from DESC
                        LIMIT 1
                    ) h ON true
                    WHERE LEFT(de.entry_date::text, 7) = %s
                      AND de.restaurant_id = ANY(%s)
                    """,
                    (period, list(rest_by_id.keys())),
                )
                entries = [dict(r) for r in cur.fetchall()]
    except Exception as exc:  # pragma: no cover
        # Tablo yok / cast hatası / başka SQL sorunu → fallback
        import logging
        logging.getLogger(__name__).warning(
            "pricing_history query failed, fallback to restaurants table: %s",
            exc,
        )
        use_history_rates = False
        # Fallback: restaurants tablosundan mevcut tarifeleri çek + entries
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        de.restaurant_id,
                        de.actual_personnel_id,
                        COALESCE(de.worked_hours, 0)::float AS hours,
                        COALESCE(de.package_count, 0)::int AS packages,
                        NULL::date AS effective_from,
                        COALESCE(r.pricing_model, '') AS pricing_model,
                        COALESCE(r.hourly_rate, 0)::float AS hourly_rate,
                        COALESCE(r.package_rate, 0)::float AS package_rate,
                        COALESCE(r.package_threshold, 0)::int AS package_threshold,
                        COALESCE(r.package_rate_low, 0)::float AS package_rate_low,
                        COALESCE(r.package_rate_high, 0)::float AS package_rate_high,
                        COALESCE(r.fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                        COALESCE(r.vat_rate, 20)::float AS vat_rate
                    FROM daily_entries de
                    JOIN restaurants r ON r.id = de.restaurant_id
                    WHERE LEFT(de.entry_date::text, 7) = %s
                      AND de.restaurant_id = ANY(%s)
                    """,
                    (period, list(rest_by_id.keys())),
                )
                entries = [dict(r) for r in cur.fetchall()]
    # Sınıf değişkeni izlemek için (gelecek geliştirmeler):
    _ = use_history_rates

    # (restaurant_id, effective_from) bazında segmentlere böl — her segment
    # kendi tarife versiyonunu kullanır.
    segments: dict[tuple[int, Any], dict] = {}
    for e in entries:
        rid = int(e["restaurant_id"])
        eff = e.get("effective_from")
        # Eğer history satırı yoksa (eski entry), restaurants tablosunun
        # mevcut değerlerine fallback
        key = (rid, eff)
        seg = segments.get(key)
        if seg is None:
            seg = {
                "rates": {
                    "pricing_model": str(e["pricing_model"] or "").lower(),
                    "hourly_rate": float(e["hourly_rate"]),
                    "package_rate": float(e["package_rate"]),
                    "package_threshold": int(e["package_threshold"]),
                    "package_rate_low": float(e["package_rate_low"]),
                    "package_rate_high": float(e["package_rate_high"]),
                    "fixed_monthly_fee": float(e["fixed_monthly_fee"]),
                    "vat_rate": float(e["vat_rate"]),
                },
                "total_hours": 0.0,
                "total_packages": 0,
                "per_courier": {},
            }
            segments[key] = seg
        seg["total_hours"] += float(e["hours"] or 0)
        seg["total_packages"] += int(e["packages"] or 0)
        pid = e.get("actual_personnel_id")
        if pid is not None:
            seg["per_courier"][int(pid)] = (
                seg["per_courier"].get(int(pid), 0) + int(e["packages"] or 0)
            )

    # Restoran bazında agregasyon — segmentleri topla
    agg_by_rest: dict[int, dict] = {}
    for (rid, _eff), seg in segments.items():
        seg_excl, seg_basis = _compute_segment_billing(seg)
        agg = agg_by_rest.get(rid)
        if agg is None:
            agg = {
                "excl": 0.0,
                "hours": 0.0,
                "packages": 0,
                "vat_rate": seg["rates"]["vat_rate"],
                "basis": "auto",
            }
            agg_by_rest[rid] = agg
        agg["excl"] += seg_excl
        agg["hours"] += seg["total_hours"]
        agg["packages"] += seg["total_packages"]
        agg["vat_rate"] = seg["rates"]["vat_rate"]  # son segmentin KDV'si
        if seg_basis != "auto":
            agg["basis"] = seg_basis

    # Çıktıyı hazırla — entries olanlar
    for rid, agg in agg_by_rest.items():
        excl = round(agg["excl"], 2)
        vat_rate = agg["vat_rate"]
        vat_amt = round(excl * vat_rate / 100, 2)
        out[rid] = {
            "auto_invoice_excl_vat": excl,
            "auto_invoice_incl_vat": round(excl + vat_amt, 2),
            "auto_hours": round(agg["hours"], 2),
            "auto_packages": agg["packages"],
            "auto_vat_rate": vat_rate,
            "auto_basis": agg["basis"],
        }

    # Entries OLMAYAN ama sabit aylık ücretli restoranlar için:
    # son geçerli history satırından (yoksa restaurants tablosundan)
    # fixed_monthly_fee'yi al — SC Petshop gibi sabit ücretli.
    missing_rids = [rid for rid in rest_by_id if rid not in out]
    if missing_rids:
        period_start = f"{period}-01"
        rows: list[dict] = []
        try:
            with get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # 2 kademeli — önce history, yoksa restaurants
                    cur.execute(
                        """
                        SELECT
                            r.id AS restaurant_id,
                            COALESCE(h.pricing_model, r.pricing_model, '') AS pricing_model,
                            COALESCE(h.fixed_monthly_fee, r.fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                            COALESCE(h.hourly_rate, r.hourly_rate, 0)::float AS hourly_rate,
                            COALESCE(h.package_rate, r.package_rate, 0)::float AS package_rate,
                            COALESCE(h.package_rate_low, r.package_rate_low, 0)::float AS package_rate_low,
                            COALESCE(h.package_rate_high, r.package_rate_high, 0)::float AS package_rate_high,
                            COALESCE(h.vat_rate, r.vat_rate, 20)::float AS vat_rate
                        FROM restaurants r
                        LEFT JOIN LATERAL (
                            SELECT *
                            FROM restaurant_pricing_history ph
                            WHERE ph.restaurant_id = r.id
                              AND ph.effective_from <= %s::date
                            ORDER BY ph.effective_from DESC
                            LIMIT 1
                        ) h ON true
                        WHERE r.id = ANY(%s)
                        """,
                        (period_start, missing_rids),
                    )
                    rows = [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "pricing_history fallback query failed, using restaurants: %s",
                exc,
            )
            # Tablo yok ya da başka hata → restaurants tablosuna fallback
            with get_connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT
                            id AS restaurant_id,
                            COALESCE(pricing_model, '') AS pricing_model,
                            COALESCE(fixed_monthly_fee, 0)::float AS fixed_monthly_fee,
                            COALESCE(hourly_rate, 0)::float AS hourly_rate,
                            COALESCE(package_rate, 0)::float AS package_rate,
                            COALESCE(package_rate_low, 0)::float AS package_rate_low,
                            COALESCE(package_rate_high, 0)::float AS package_rate_high,
                            COALESCE(vat_rate, 20)::float AS vat_rate
                        FROM restaurants
                        WHERE id = ANY(%s)
                        """,
                        (missing_rids,),
                    )
                    rows = [dict(r) for r in cur.fetchall()]

        for r in rows:
            rid = int(r["restaurant_id"])
            model = str(r["pricing_model"] or "").lower()
            fixed_fee = float(r["fixed_monthly_fee"])
            hourly_rate = float(r["hourly_rate"])
            package_rate = float(r["package_rate"])
            rate_low = float(r["package_rate_low"])
            rate_high = float(r["package_rate_high"])
            vat_rate = float(r["vat_rate"])
            only_fixed_filled = (
                fixed_fee > 0
                and hourly_rate == 0
                and package_rate == 0
                and rate_low == 0
                and rate_high == 0
            )
            is_fixed_only = (
                "sabit" in model or "fixed" in model
                or "aylık" in model or "monthly" in model
                or only_fixed_filled
            )
            if is_fixed_only and fixed_fee > 0:
                vat_amt = round(fixed_fee * vat_rate / 100, 2)
                out[rid] = {
                    "auto_invoice_excl_vat": round(fixed_fee, 2),
                    "auto_invoice_incl_vat": round(fixed_fee + vat_amt, 2),
                    "auto_hours": 0,
                    "auto_packages": 0,
                    "auto_vat_rate": vat_rate,
                    "auto_basis": "fixed",
                }
    return out


def _compute_segment_billing(seg: dict) -> tuple[float, str]:
    """Bir tarife segmenti için (hours, packages, per_courier) → KDV hariç fatura.

    Mevcut pricing_model mantığı korunur (Fasuli karma eşikli, Quick China
    saat+paket, SC Petshop sabit, vb.) — sadece girdi olarak segmentin
    KENDİ tarifesi ve KENDİ entry toplamları kullanılır.
    """
    rates = seg["rates"]
    model = rates["pricing_model"]
    hourly_rate = rates["hourly_rate"]
    package_rate = rates["package_rate"]
    threshold = rates["package_threshold"]
    rate_low = rates["package_rate_low"]
    rate_high = rates["package_rate_high"]
    fixed_fee = rates["fixed_monthly_fee"]

    total_hours = seg["total_hours"]
    total_packages = seg["total_packages"]
    per_courier = seg["per_courier"]

    only_fixed_filled = (
        fixed_fee > 0
        and hourly_rate == 0
        and package_rate == 0
        and rate_low == 0
        and rate_high == 0
    )
    is_fixed_only = (
        "sabit" in model or "fixed" in model
        or "aylık" in model or "monthly" in model
        or only_fixed_filled
    )
    if is_fixed_only and fixed_fee > 0:
        # NOT: ay ortasında sabit→saatlik geçiş olursa bu segment yine
        # full fee yansıtır; geçmişte tek sabit kayıt varsa sorun olmaz.
        return (fixed_fee, "fixed")

    hours_part = total_hours * hourly_rate if hourly_rate > 0 else 0.0
    pkg_part = 0.0
    pkg_basis: str | None = None
    if threshold > 0 and rate_low > 0 and rate_high > 0:
        for pkg in per_courier.values():
            if pkg >= threshold:
                pkg_part += pkg * rate_high
            else:
                pkg_part += pkg * rate_low
        pkg_basis = "threshold"
    elif package_rate > 0:
        pkg_part = total_packages * package_rate
        pkg_basis = "package"

    excl = hours_part + pkg_part
    if hours_part > 0 and pkg_basis == "threshold":
        basis = "hourly+threshold"
    elif hours_part > 0 and pkg_basis == "package":
        basis = "hourly+package"
    elif pkg_basis == "threshold":
        basis = "threshold"
    elif pkg_basis == "package":
        basis = "package"
    elif hours_part > 0:
        basis = "hourly"
    elif fixed_fee > 0:
        excl = fixed_fee
        basis = "fixed"
    else:
        basis = "auto"

    return (excl, basis)


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

    # Restoran listesi — period-aware (aktif + o dönem aktif olanlar)
    if period:
        period_rests = _get_period_restaurants(period)
        restaurants_list = [
            {"id": r["id"], "brand": r["brand"], "branch": r["branch"]}
            for r in period_rests
        ]
    else:
        restaurants_list = None
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
            if restaurants_list is not None:
                restaurants = restaurants_list
            else:
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
    """Bir dönem için özet KPI'lar (+ debug: o ayın daily_entries özeti)."""
    items = list_collections(period=period)
    today = date.today()
    total_invoice = sum(float(x.get("invoice_amount") or 0) for x in items)
    total_collected = sum(float(x.get("collected_amount") or 0) for x in items)
    total_open = sum(float(x.get("remaining_amount") or 0) for x in items)
    overdue = [x for x in items if x.get("is_overdue")]
    overdue_amount = sum(float(x.get("remaining_amount") or 0) for x in overdue)
    collected_count = sum(1 for x in items if x.get("status") == "Tahsil Edildi")
    pending_count = sum(1 for x in items if x.get("status") in ("Bekliyor", "Kısmi Tahsilat"))

    # Debug: o ay için daily_entries toplamı (period filter sağlığını teyit)
    entries_total_hours = 0.0
    entries_total_packages = 0
    entries_restaurants = 0
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(worked_hours), 0)::float AS h,
                        COALESCE(SUM(package_count), 0)::int AS p,
                        COUNT(DISTINCT restaurant_id) AS n
                    FROM daily_entries
                    WHERE LEFT(entry_date::text, 7) = %s
                      AND restaurant_id IS NOT NULL
                    """,
                    (period,),
                )
                row = cur.fetchone() or {}
                entries_total_hours = float(row.get("h") or 0)
                entries_total_packages = int(row.get("p") or 0)
                entries_restaurants = int(row.get("n") or 0)
    except Exception:
        pass

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
        # Period sağlık göstergesi (her ay farklı olmalı)
        "entries_total_hours": round(entries_total_hours, 1),
        "entries_total_packages": entries_total_packages,
        "entries_restaurants": entries_restaurants,
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
