"""Hakediş & faturalandırma motoru.

Kurallar: `yeni-crm/docs/hakedis-kurallari.md`.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.restaurants import get_restaurant


# Aylık sabit anlaşmalı restoranlarda günlük standart saat.
# Veride henüz dedicated kolon yok; SC Petshop ve Sushi Inn için 10 saat.
# Modal ile düzenlenebilir hâle gelene kadar varsayılan budur.
DEFAULT_FIXED_DAILY_HOURS = 10


def restaurant_monthly_breakdown(restaurant_id: int, period: str) -> dict:
    """Restoranın o aydaki kurye bazında detayı + fatura tutarı."""
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
            p.monthly_fixed_cost,
            p.fixed_monthly_billing,
            -- Vardiya saati: önce restoran (kendi vardiya saati),
            -- sonra personel kaydı, son çare 11
            COALESCE(
                NULLIF(r.standard_daily_hours, 0),
                NULLIF(p.standard_daily_hours, 0),
                11
            ) AS standard_daily_hours
        FROM daily_entries d
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE d.restaurant_id = %s
          AND LEFT(d.entry_date::text, 7) = %s
        ORDER BY p.full_name NULLS LAST, d.entry_date
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (restaurant_id, period))
            entries = cur.fetchall()

    by_courier: dict[int, dict] = {}
    unassigned_count = 0
    unassigned_absences = 0

    for e in entries:
        cid = e["actual_personnel_id"]
        worked_hours = float(e.get("worked_hours") or 0)
        # KRİTİK: çalışıldı mı/değil mi sadece worked_hours üzerinden.
        # absence_reason yanlış etiketlenmiş olabilir (örn destek satırlarında
        # status='Normal' ama absence_reason='Diğer' yazıyor). Saat varsa çalıştı.
        worked = worked_hours > 0
        coverage = (e.get("coverage_type") or "").strip()

        if cid is None:
            unassigned_count += 1
            if not worked:
                unassigned_absences += 1
            continue

        if cid not in by_courier:
            assigned = e.get("assigned_restaurant_id")
            by_courier[cid] = {
                "personnel_id": cid,
                "full_name": e.get("full_name"),
                "person_code": e.get("person_code"),
                "role": e.get("role"),
                "is_support": (
                    coverage == "Destek"
                    or (assigned is not None and assigned != restaurant_id)
                ),
                "monthly_fixed_cost": float(e.get("monthly_fixed_cost") or 0),
                "fixed_monthly_billing": float(
                    e.get("fixed_monthly_billing") or 0
                ),
                "standard_daily_hours": float(
                    e.get("standard_daily_hours") or 11
                ),
                "entries": 0,
                "working_days": 0,
                "absences": 0,
                "total_hours": 0.0,
                "total_packages": 0,
                "overtime_hours": 0.0,
                "ekstra_mesai_days": 0.0,
                "billing_excl_vat": 0.0,
                "billing_incl_vat": 0.0,
                "billing_breakdown": [],
            }

        c = by_courier[cid]
        c["entries"] += 1
        if worked:
            c["working_days"] += 1
            c["total_hours"] += worked_hours
            c["total_packages"] += int(e.get("package_count") or 0)
            # Bayram/x2 mesai: günlük standart saatten fazla yazılmış kayıtlar
            std = c.get("standard_daily_hours") or 11
            if worked_hours > std:
                c["overtime_hours"] += worked_hours - std
        else:
            c["absences"] += 1

    # Ekstra mesai gün sayısı (bayram x2 katsayısı)
    for c in by_courier.values():
        std = c.get("standard_daily_hours") or 11
        if std > 0:
            c["ekstra_mesai_days"] = c["overtime_hours"] / std

    # Anlaşma tipine göre hesap
    if pricing == "fixed_monthly":
        _compute_fixed_monthly(by_courier, fixed_monthly_fee)
    else:
        for c in by_courier.values():
            # SABİT AYLIK PERSONEL — yalnızca KENDİ restoranındaysa:
            # Restoran Takım Şefi, Kaptan, BM sabit aylık anlaşmalıdır.
            # Kendi atandığı restoranda → fatura = fixed_monthly_billing.
            # DESTEK olarak başka restorana giderse (is_support=True) →
            # o restorana joker gibi yansır, normal tarife uygulanır
            # (saat × saatlik + paket × paket tarifesi). RTS/joker'in
            # kendi sabit maaşı zaten kendi restoranına yazıldığı için
            # destekteki restorandan ekstra para almazız ama o restoranı
            # tarife üzerinden faturalandırırız.
            if (
                c["fixed_monthly_billing"] > 0
                and c["working_days"] > 0
                and not c.get("is_support")
            ):
                _compute_personnel_fixed_billing(c)
                continue

            if pricing == "hourly_only":
                _compute_hourly_only(c, hourly_rate)
            elif pricing == "hourly_plus_package":
                _compute_hourly_plus_package(c, hourly_rate, package_rate)
            elif pricing == "threshold_package":
                _compute_threshold_package(
                    c, hourly_rate, package_threshold,
                    package_rate_low, package_rate_high,
                )

            # Destek olarak gelen sabit aylık personel için bilgilendirme
            # (görsel olarak "joker gibi kullanıldı" açıklaması)
            if (
                c.get("is_support")
                and c["fixed_monthly_billing"] > 0
                and c["working_days"] > 0
            ):
                role_lbl = c.get("role") or "Sabit aylık personel"
                c["billing_breakdown"].append({
                    "label": (
                        f"ℹ {role_lbl} destek — kendi sabit maaşı kendi "
                        f"restoranına yazıldı, buraya tarife üzerinden faturalandı"
                    ),
                    "qty": 0,
                    "rate": 0,
                    "amount": 0,
                })

    # KDV hesabı
    for c in by_courier.values():
        c["billing_excl_vat"] = round(c["billing_excl_vat"], 2)
        c["billing_incl_vat"] = round(
            c["billing_excl_vat"] * (1 + vat_rate / 100), 2
        )

    couriers = sorted(
        by_courier.values(),
        key=lambda x: (
            x["is_support"],
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


def _compute_personnel_fixed_billing(c: dict) -> None:
    """Sabit aylık anlaşmalı personel (Takım Şefi, Kaptan, BM) için fatura.

    `personnel.fixed_monthly_billing` KDV hariç sabit aylık tutardır.
    Bayram / fazla mesai (kuryenin günlük standart saat üzeri çalıştığı saatler)
    aynı oranda restoran faturasına da yansır.
    """
    billing = c["fixed_monthly_billing"]
    role_lbl = c.get("role") or "Sabit aylık"
    if billing > 0:
        c["billing_breakdown"].append({
            "label": f"Aylık sabit ({role_lbl})",
            "qty": 1,
            "rate": billing,
            "amount": billing,
        })
    # Ekstra mesai: payroll'da hesaplanan ekstra_mesai_days değerini kullan
    extra_days = float(c.get("ekstra_mesai_days") or 0)
    if extra_days > 0 and billing > 0:
        daily = billing / 30
        extra_amt = daily * extra_days
        billing += extra_amt
        c["billing_breakdown"].append({
            "label": (
                f"Bayram/ekstra mesai — {extra_days:g} gün × "
                f"{daily:,.2f} ₺ (aylık/30)"
            ),
            "qty": extra_days,
            "rate": daily,
            "amount": extra_amt,
        })

    c["billing_excl_vat"] = billing

    if c.get("monthly_fixed_cost", 0) > 0:
        # Bilgilendirme satırı — bu hesaba dahil değil, sadece görüntü
        c["billing_breakdown"].append({
            "label": (
                f"ℹ Kuryeye ödenen aylık: "
                f"{c['monthly_fixed_cost']:,.2f} ₺ (kar farkı)"
            ),
            "qty": 0,
            "rate": 0,
            "amount": 0,
        })


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
    """Aylık sabit hesabı.

    - Restoranın aylık sabit tutarı (örn 79.800 ₺) **1 kez** ana atanmış kuryeye
      yazılır (en çok mesai yapan ana kurye).
    - Ana kurye ekstra mesai yaptıysa: standart günlük saat üzerinden hesaplanır.
        beklenen_saat = working_days × standard_daily_hours
        ekstra_saat = total_hours - beklenen_saat
        ekstra_gün = ekstra_saat / standard_daily_hours
        ekstra_fatura = ekstra_gün × (fixed_monthly_fee / 30)
    - Destek olarak gelen kurye: working_days × (fixed_monthly_fee / 30).
    """
    daily_fee = fixed_monthly_fee / 30 if fixed_monthly_fee > 0 else 0
    standard_daily_hours = DEFAULT_FIXED_DAILY_HOURS

    main_couriers = [
        c for c in by_courier.values() if not c["is_support"]
    ]
    main_couriers.sort(key=lambda c: -c["working_days"])
    primary = main_couriers[0] if main_couriers else None

    for cid, c in by_courier.items():
        if c is primary:
            billing = fixed_monthly_fee
            if fixed_monthly_fee > 0:
                c["billing_breakdown"].append({
                    "label": "Aylık sabit",
                    "qty": 1,
                    "rate": fixed_monthly_fee,
                    "amount": fixed_monthly_fee,
                })
            # Ekstra mesai — saat bazında karar
            expected_hours = c["working_days"] * standard_daily_hours
            extra_hours = c["total_hours"] - expected_hours
            if extra_hours > 0 and daily_fee > 0:
                extra_days = extra_hours / standard_daily_hours
                extra_amt = extra_days * daily_fee
                billing += extra_amt
                if extra_days == int(extra_days):
                    qty_lbl = f"{int(extra_days)} gün"
                else:
                    qty_lbl = f"{extra_days:.2f} gün"
                c["billing_breakdown"].append({
                    "label": (
                        f"Ekstra mesai — {qty_lbl} × {daily_fee:.2f} ₺ "
                        f"({extra_hours:g} saat fazlalık)"
                    ),
                    "qty": extra_days,
                    "rate": daily_fee,
                    "amount": extra_amt,
                })
            c["billing_excl_vat"] = billing

        elif c["is_support"]:
            if c["working_days"] > 0 and daily_fee > 0:
                amt = daily_fee * c["working_days"]
                c["billing_excl_vat"] = amt
                c["billing_breakdown"].append({
                    "label": (
                        f"Destek vardiyası — {c['working_days']} gün × "
                        f"{daily_fee:.2f} ₺"
                    ),
                    "qty": c["working_days"],
                    "rate": daily_fee,
                    "amount": amt,
                })
            else:
                c["billing_excl_vat"] = 0.0

        else:
            c["billing_excl_vat"] = 0.0
