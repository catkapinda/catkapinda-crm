"""Fatura servisi — restoranlara aylık kesilen faturalar.

Otomatik fatura tutarı restoran tarife modeli + puantajdan hesaplanır
(collections._compute_auto_invoice_map paylaşılır). restaurant_invoices
tablosu manuel kayıt/ödeme bilgilerini saklar.
"""
from datetime import datetime, timezone

from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.collections import (
    _compute_auto_invoice_map,
    _get_period_restaurants,
)


VAT_RATE = 0.20


def list_invoices(period: str) -> list[dict]:
    """Belirli bir ay için tüm restoranların faturalarını listele.

    1) collections._compute_auto_invoice_map ile pricing_model + puantajdan
       restoran bazlı otomatik tutar (KDV hariç + KDV dahil) hesaplanır
    2) restaurant_invoices tablosundan manuel kayıtlar join edilir
    3) Manuel kayıt varsa öncelik, yoksa otomatik sanal kayıt
    """
    # 1) Pricing model + puantajdan auto invoice
    auto_map = _compute_auto_invoice_map(period)
    period_rests = _get_period_restaurants(period)

    by_restaurant: dict[int, dict] = {}
    for r in period_rests:
        rid = int(r["id"])
        auto = auto_map.get(rid, {})
        by_restaurant[rid] = {
            "restaurant_id": rid,
            "rest_brand": r.get("brand"),
            "rest_branch": r.get("branch"),
            "courier_count": 0,  # kurye sayısı — eşikli modelden türetilir
            "fatura_total": float(auto.get("auto_invoice_excl_vat") or 0),
            "auto_basis": auto.get("auto_basis"),
            "auto_hours": float(auto.get("auto_hours") or 0),
            "auto_packages": int(auto.get("auto_packages") or 0),
        }

    # Kurye sayısı için daily_entries'ten distinct personnel say
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT restaurant_id,
                       COUNT(DISTINCT actual_personnel_id) AS n
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                  AND actual_personnel_id IS NOT NULL
                  AND restaurant_id IS NOT NULL
                GROUP BY restaurant_id
                """,
                (period,),
            )
            for r in cur.fetchall():
                rid = int(r["restaurant_id"])
                if rid in by_restaurant:
                    by_restaurant[rid]["courier_count"] = int(r["n"] or 0)

    # 2) restaurant_invoices tablosundan manuel kayıtları çek
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT ri.*, r.brand, r.branch, r.vat_rate
                FROM restaurant_invoices ri
                LEFT JOIN restaurants r ON r.id = ri.restaurant_id
                WHERE ri.period = %s
                ORDER BY r.brand NULLS LAST, r.branch NULLS LAST
                """,
                (period,),
            )
            manual_rows = cur.fetchall()

            # Tüm aktif restoranların bilgisi (brand/branch/vat_rate)
            cur.execute(
                """
                SELECT id, brand, branch, COALESCE(vat_rate, 20) AS vat_rate, active
                FROM restaurants
                """,
            )
            all_rest = {row["id"]: row for row in cur.fetchall()}

    manual_map = {row["restaurant_id"]: row for row in manual_rows}

    # 3) Birleştir — auto + manuel
    out: list[dict] = []
    seen_rids: set[int] = set()

    # Önce bordrodan gelen restoranlar
    for rid, agg in by_restaurant.items():
        seen_rids.add(rid)
        rest = all_rest.get(rid, {})
        manual = manual_map.get(rid)
        vat_rate = float(
            (manual and manual.get("vat_rate")) or rest.get("vat_rate") or 20
        ) / 100.0

        # Manuel kayıt varsa onun tutarları öncelik (override)
        if manual:
            excl_vat = float(manual.get("amount_excl_vat") or agg["fatura_total"])
            vat_amount = float(manual.get("vat_amount") or excl_vat * vat_rate)
            incl_vat = float(manual.get("amount_incl_vat") or excl_vat + vat_amount)
            status = manual.get("status") or "Beklemede"
            invoice_no = manual.get("invoice_no")
            paid_at = (
                manual["paid_at"].isoformat() if manual.get("paid_at") else None
            )
            paid_amount = float(manual.get("paid_amount") or 0)
            notes = manual.get("notes")
            invoice_id = manual.get("id")
            issued_at = (
                manual["issued_at"].isoformat() if manual.get("issued_at") else None
            )
        else:
            excl_vat = agg["fatura_total"]
            vat_amount = excl_vat * vat_rate
            incl_vat = excl_vat + vat_amount
            status = "Beklemede"
            invoice_no = None
            paid_at = None
            paid_amount = 0.0
            notes = None
            invoice_id = None
            issued_at = None

        out.append({
            "id": invoice_id,
            "restaurant_id": rid,
            "rest_brand": agg["rest_brand"] or rest.get("brand"),
            "rest_branch": agg["rest_branch"] or rest.get("branch"),
            "period": period,
            "invoice_no": invoice_no,
            "courier_count": agg["courier_count"],
            "amount_excl_vat": round(excl_vat, 2),
            "vat_rate": round(vat_rate * 100, 1),
            "vat_amount": round(vat_amount, 2),
            "amount_incl_vat": round(incl_vat, 2),
            "status": status,
            "issued_at": issued_at,
            "paid_at": paid_at,
            "paid_amount": paid_amount,
            "balance": round(incl_vat - paid_amount, 2),
            "notes": notes,
            "is_manual_only": False,
            "auto_basis": agg.get("auto_basis"),
            "auto_hours": agg.get("auto_hours", 0),
            "auto_packages": agg.get("auto_packages", 0),
        })

    # Manuel kayıtlardan bordroya girmemiş olanlar (örn ek fatura)
    for rid, manual in manual_map.items():
        if rid in seen_rids:
            continue
        rest = all_rest.get(rid, {})
        vat_rate = float(manual.get("vat_rate") or rest.get("vat_rate") or 20) / 100.0
        excl_vat = float(manual.get("amount_excl_vat") or 0)
        vat_amount = float(manual.get("vat_amount") or excl_vat * vat_rate)
        incl_vat = float(manual.get("amount_incl_vat") or excl_vat + vat_amount)
        paid_amount = float(manual.get("paid_amount") or 0)
        out.append({
            "id": manual.get("id"),
            "restaurant_id": rid,
            "rest_brand": rest.get("brand") or manual.get("brand"),
            "rest_branch": rest.get("branch") or manual.get("branch"),
            "period": period,
            "invoice_no": manual.get("invoice_no"),
            "courier_count": 0,
            "amount_excl_vat": round(excl_vat, 2),
            "vat_rate": round(vat_rate * 100, 1),
            "vat_amount": round(vat_amount, 2),
            "amount_incl_vat": round(incl_vat, 2),
            "status": manual.get("status") or "Beklemede",
            "issued_at": (
                manual["issued_at"].isoformat() if manual.get("issued_at") else None
            ),
            "paid_at": (
                manual["paid_at"].isoformat() if manual.get("paid_at") else None
            ),
            "paid_amount": paid_amount,
            "balance": round(incl_vat - paid_amount, 2),
            "notes": manual.get("notes"),
            "is_manual_only": True,
        })

    out.sort(key=lambda r: ((r.get("rest_brand") or "").lower(), (r.get("rest_branch") or "").lower()))
    return out


def get_invoice_summary(period: str) -> dict:
    """Aya ait özet — toplam, ödenen, bekleyen tutarlar + sayım."""
    invoices = list_invoices(period)

    n_total = len(invoices)
    n_paid = sum(1 for i in invoices if i["status"] == "Ödendi")
    n_partial = sum(1 for i in invoices if i["status"] == "Kısmi")
    n_pending = sum(1 for i in invoices if i["status"] == "Beklemede")

    sum_excl = sum(i["amount_excl_vat"] for i in invoices)
    sum_vat = sum(i["vat_amount"] for i in invoices)
    sum_incl = sum(i["amount_incl_vat"] for i in invoices)
    sum_paid = sum(i["paid_amount"] for i in invoices)
    sum_balance = sum(i["balance"] for i in invoices)

    return {
        "period": period,
        "count_total": n_total,
        "count_paid": n_paid,
        "count_partial": n_partial,
        "count_pending": n_pending,
        "sum_excl_vat": round(sum_excl, 2),
        "sum_vat": round(sum_vat, 2),
        "sum_incl_vat": round(sum_incl, 2),
        "sum_paid": round(sum_paid, 2),
        "sum_balance": round(sum_balance, 2),
        "collection_pct": round((sum_paid / sum_incl * 100) if sum_incl > 0 else 0, 1),
    }


def upsert_invoice(restaurant_id: int, period: str, fields: dict) -> dict | None:
    """Restoran-period kombinasyonu için fatura kaydı oluştur veya güncelle.

    fields: invoice_no, amount_excl_vat, vat_amount, amount_incl_vat,
            status, paid_at, paid_amount, notes
    """
    allowed = {
        "invoice_no", "amount_excl_vat", "vat_amount", "amount_incl_vat",
        "status", "paid_at", "paid_amount", "notes",
    }
    safe = {k: v for k, v in fields.items() if k in allowed}

    # Var mı?
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id FROM restaurant_invoices WHERE restaurant_id = %s AND period = %s",
                (restaurant_id, period),
            )
            existing = cur.fetchone()

            if existing:
                if not safe:
                    return _row_for(restaurant_id, period)
                cols = ", ".join(f"{k} = %s" for k in safe.keys())
                vals = list(safe.values()) + [existing["id"]]
                cur.execute(
                    f"UPDATE restaurant_invoices SET {cols} WHERE id = %s",
                    vals,
                )
            else:
                safe["restaurant_id"] = restaurant_id
                safe["period"] = period
                cols = ", ".join(safe.keys())
                placeholders = ", ".join(["%s"] * len(safe))
                cur.execute(
                    f"INSERT INTO restaurant_invoices ({cols}) VALUES ({placeholders})",
                    list(safe.values()),
                )
            conn.commit()

    return _row_for(restaurant_id, period)


def mark_paid(restaurant_id: int, period: str, amount: float | None = None) -> dict | None:
    """Faturayı ödendi işaretle. amount verilmezse toplam fatura tutarı kullanılır."""
    invoices = list_invoices(period)
    target = next(
        (i for i in invoices if i["restaurant_id"] == restaurant_id),
        None,
    )
    if not target:
        return None
    paid = float(amount) if amount is not None else float(target["amount_incl_vat"])
    incl = float(target["amount_incl_vat"])
    if paid <= 0:
        status = "Beklemede"
    elif paid >= incl:
        status = "Ödendi"
    else:
        status = "Kısmi"

    return upsert_invoice(restaurant_id, period, {
        "amount_excl_vat": target["amount_excl_vat"],
        "vat_amount": target["vat_amount"],
        "amount_incl_vat": target["amount_incl_vat"],
        "paid_amount": paid,
        "status": status,
        "paid_at": datetime.now(timezone.utc) if status != "Beklemede" else None,
    })


def _row_for(restaurant_id: int, period: str) -> dict | None:
    """Fatura listesinden tek bir restoran-period kombinasyonunu çek."""
    rows = list_invoices(period)
    for r in rows:
        if r["restaurant_id"] == restaurant_id:
            return r
    return None
