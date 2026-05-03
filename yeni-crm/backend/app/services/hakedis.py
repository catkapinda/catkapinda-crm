"""Hakediş & faturalandırma motoru.

Bu modül `yeni-crm/docs/hakedis-kurallari.md` dosyasındaki kuralları uygular.
İlk sürüm: restorana fatura kırılımı (kurye bazında).
Sonraki sürümler: kurye hakediş PDF'si + destek vardiyası özel kuralları.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.restaurants import get_restaurant


def restaurant_monthly_breakdown(restaurant_id: int, period: str) -> dict:
    """Restoranın o aydaki kurye bazında detayı + fatura tutarı.

    Anlaşma tipine göre her kurye için ayrı hesap yapılır.
    Sonunda toplam (KDV hariç + KDV dahil + KDV tutarı) hesaplanır.
    """
    rest = get_restaurant(restaurant_id)
    if not rest:
        return {"restaurant": None, "couriers": [], "totals": {}}

    pricing = (rest.get("pricing_model") or "").strip()
    hourly_rate = float(rest.get("hourly_rate") or 0)
    package_rate = float(rest.get("package_rate") or 0)
    package_threshold = int(rest.get("package_threshold") or 390)
    package_rate_low = float(rest.get("package_rate_low") or 0)
    package_rate_high = float(rest.get("package_rate_high") or 0)
    fixed_monthly_fee = float(rest.get("fixed_monthly_fee") or 0)
    vat_rate = float(rest.get("vat_rate") or 0)

    # O ayın puantajları, kurye bilgisi JOIN'lı
    sql = """
        SELECT
            d.id,
            d.entry_date,
            d.actual_personnel_id,
            d.worked_hours,
            d.package_count,
            d.coverage_type,
            d.absence_reason,
            d.status,
            p.full_name,
            p.person_code,
            p.role,
            p.assigned_restaurant_id,
            p.monthly_fixed_cost
        FROM daily_entries d
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        WHERE d.restaurant_id = %s
          AND LEFT(d.entry_date::text, 7) = %s
        ORDER BY p.full_name NULLS LAST, d.entry_date
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (restaurant_id, period))
            entries = cur.fetchall()

    # Kurye bazında grupla — personel atanmamış kayıtları ayrı bir bucket'ta
    by_courier: dict[int, dict] = {}
    unassigned_count = 0
    unassigned_absences = 0

    for e in entries:
        cid = e["actual_personnel_id"]
        absent = bool(
            e["absence_reason"] and str(e["absence_reason"]).strip()
        )
        coverage = (e.get("coverage_type") or "").strip()

        # personnel_id null kayıtları fatura hesabı dışında
        if cid is None:
            unassigned_count += 1
            if absent:
                unassigned_absences += 1
            continue

        if cid not in by_courier:
            by_courier[cid] = {
                "personnel_id": cid,
                "full_name": e.get("full_name"),
                "person_code": e.get("person_code"),
                "role": e.get("role"),
                "is_support": (
                    e.get("assigned_restaurant_id") is not None
                    and e.get("assigned_restaurant_id") != restaurant_id
                ) or coverage == "Destek",
                "monthly_fixed_cost": float(e.get("monthly_fixed_cost") or 0),
                "entries": 0,
                "working_days": 0,
                "absences": 0,
                "total_hours": 0.0,
                "total_packages": 0,
                "billing_excl_vat": 0.0,
                "billing_incl_vat": 0.0,
                "billing_breakdown": [],
            }

        c = by_courier[cid]
        c["entries"] += 1
        if absent:
            c["absences"] += 1
        else:
            c["working_days"] += 1
            c["total_hours"] += float(e.get("worked_hours") or 0)
            c["total_packages"] += int(e.get("package_count") or 0)

    # Anlaşma tipine göre hesap
    if pricing == "fixed_monthly":
        _compute_fixed_monthly(by_courier, fixed_monthly_fee)
    else:
        for cid, c in by_courier.items():
            if pricing == "hourly_only":
                _compute_hourly_only(c, hourly_rate)
            elif pricing == "hourly_plus_package":
                _compute_hourly_plus_package(c, hourly_rate, package_rate)
            elif pricing == "threshold_package":
                _compute_threshold_package(
                    c, hourly_rate, package_threshold,
                    package_rate_low, package_rate_high,
                )

    # KDV hesabı
    for c in by_courier.values():
        c["billing_excl_vat"] = round(c["billing_excl_vat"], 2)
        c["billing_incl_vat"] = round(
            c["billing_excl_vat"] * (1 + vat_rate / 100), 2
        )

    # Sıralama: ana kuryeler önce (working_days çoğa az), sonra destekler, sonra inaktifler
    couriers = sorted(
        by_courier.values(),
        key=lambda x: (
            x["is_support"],  # False (ana) önce
            -x["billing_excl_vat"],
            -x["working_days"],
        ),
    )

    total_excl = sum(c["billing_excl_vat"] for c in couriers)
    total_incl = sum(c["billing_incl_vat"] for c in couriers)

    return {
        "restaurant": rest,
        "period": period,
        "couriers": couriers,
        "unassigned_entries": unassigned_count,
        "unassigned_absences": unassigned_absences,
        "totals": {
            "courier_count": len(couriers),
            "support_count": sum(1 for c in couriers if c["is_support"]),
            "total_entries": sum(c["entries"] for c in couriers) + unassigned_count,
            "total_working_days": sum(c["working_days"] for c in couriers),
            "total_absences": (
                sum(c["absences"] for c in couriers) + unassigned_absences
            ),
            "total_hours": round(sum(c["total_hours"] for c in couriers), 2),
            "total_packages": sum(c["total_packages"] for c in couriers),
            "total_billing_excl_vat": round(total_excl, 2),
            "total_billing_incl_vat": round(total_incl, 2),
            "vat_amount": round(total_incl - total_excl, 2),
            "vat_rate": vat_rate,
        },
    }


def _compute_hourly_only(c: dict, hourly_rate: float) -> None:
    amt = c["total_hours"] * hourly_rate
    c["billing_excl_vat"] = amt
    if amt > 0:
        c["billing_breakdown"].append({
            "label": f"Saat × {hourly_rate:g} ₺",
            "qty": c["total_hours"],
            "rate": hourly_rate,
            "amount": amt,
        })


def _compute_hourly_plus_package(
    c: dict, hourly_rate: float, package_rate: float
) -> None:
    saat_amt = c["total_hours"] * hourly_rate
    pkt_amt = c["total_packages"] * package_rate
    c["billing_excl_vat"] = saat_amt + pkt_amt
    if saat_amt > 0:
        c["billing_breakdown"].append({
            "label": f"Saat × {hourly_rate:g} ₺",
            "qty": c["total_hours"],
            "rate": hourly_rate,
            "amount": saat_amt,
        })
    if pkt_amt > 0:
        c["billing_breakdown"].append({
            "label": f"Paket × {package_rate:g} ₺",
            "qty": c["total_packages"],
            "rate": package_rate,
            "amount": pkt_amt,
        })


def _compute_threshold_package(
    c: dict,
    hourly_rate: float,
    threshold: int,
    rate_low: float,
    rate_high: float,
) -> None:
    saat_amt = c["total_hours"] * hourly_rate
    # Eşik karşılaştırması: kuryenin bu restorandaki paket sayısı
    # Destek günleri ana atamadan ayrı sayılır (zaten ayrı kurye satırı).
    crossed = c["total_packages"] > threshold
    rate_used = rate_high if crossed else rate_low
    pkt_amt = c["total_packages"] * rate_used
    c["billing_excl_vat"] = saat_amt + pkt_amt

    if saat_amt > 0:
        c["billing_breakdown"].append({
            "label": f"Saat × {hourly_rate:g} ₺",
            "qty": c["total_hours"],
            "rate": hourly_rate,
            "amount": saat_amt,
        })
    if pkt_amt > 0:
        lbl = (
            f"Paket × {rate_used:g} ₺ "
            f"({'>' if crossed else '≤'}{threshold})"
        )
        c["billing_breakdown"].append({
            "label": lbl,
            "qty": c["total_packages"],
            "rate": rate_used,
            "amount": pkt_amt,
        })


def _compute_fixed_monthly(
    by_courier: dict[int, dict], fixed_monthly_fee: float
) -> None:
    """Aylık sabit hesabı:

    - Restoranın o ayki tutarı **1 kez** ana atanmış kuryeye yazılır
      (en çok çalışan ana kurye seçilir; genelde tek kişidir).
    - Eğer hiç ana kurye yoksa ama destek varsa, sabit ücret yine restoran
      toplamından gelir; tüm günler destek olarak fee/30 × gün hesabıyla.
    - Ana kurye 30 günden fazla çalıştıysa ekstra günler için fee/30 × ekstra.
    - Destek kuryeler için: fee/30 × destek_günü.
    """
    daily = fixed_monthly_fee / 30 if fixed_monthly_fee > 0 else 0

    # Ana kuryeler arasında en çok working_days olanı bul (genelde tek kişi)
    main_couriers = [
        c for c in by_courier.values() if not c["is_support"]
    ]
    main_couriers.sort(key=lambda c: -c["working_days"])
    primary = main_couriers[0] if main_couriers else None

    for cid, c in by_courier.items():
        if c is primary:
            # Ana kurye: aylık sabit tutar
            billing = fixed_monthly_fee
            if fixed_monthly_fee > 0:
                c["billing_breakdown"].append({
                    "label": "Aylık sabit",
                    "qty": 1,
                    "rate": fixed_monthly_fee,
                    "amount": fixed_monthly_fee,
                })
            # 30 günden fazla mesai için ekstra
            if c["working_days"] > 30 and daily > 0:
                extra_days = c["working_days"] - 30
                extra_amt = daily * extra_days
                billing += extra_amt
                c["billing_breakdown"].append({
                    "label": (
                        f"Ekstra mesai — {extra_days} gün × {daily:.2f} ₺"
                    ),
                    "qty": extra_days,
                    "rate": daily,
                    "amount": extra_amt,
                })
            c["billing_excl_vat"] = billing

        elif c["is_support"]:
            # Destek kurye: sadece çalıştığı günler × günlük tarife
            if c["working_days"] > 0 and daily > 0:
                amt = daily * c["working_days"]
                c["billing_excl_vat"] = amt
                c["billing_breakdown"].append({
                    "label": (
                        f"Destek vardiyası — {c['working_days']} gün × "
                        f"{daily:.2f} ₺"
                    ),
                    "qty": c["working_days"],
                    "rate": daily,
                    "amount": amt,
                })
            else:
                c["billing_excl_vat"] = 0.0

        else:
            # Diğer ana kuryeler (çoğul atama varsa) — fatura yok, primary aldı
            c["billing_excl_vat"] = 0.0
