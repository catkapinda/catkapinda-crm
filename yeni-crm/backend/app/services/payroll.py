"""Bordro servisi — kurye bazında aylık net hakediş hesabı.

Brüt = ana atama + destek günleri (her birinin restoran formülüne göre)
- Kurye aylık sabitse (`monthly_fixed_cost > 0`) → standart formül atlanır,
  sabit tutar geçerli + Kaptan bonusu (rolü Kaptan ise)
- Aksi halde:
    - Saatlik / Saat+Prim / Eşikli (390) → restoranın hourly_rate, package_rate
      (eşikli durumda kuryenin O AY o restorandaki paket toplamı eşiği aşarsa
      yüksek tarife)
    - Aylık Sabit restoran → restoranın atanmış kuryesi olarak
      monthly_fixed_cost / 30 × çalışılan gün
- Destek günleri (coverage='Destek' veya kuryenin kendi restoranı dışı):
    - Destek gittiği restoranın formülü uygulanır

Kesintiler (deductions tablosundan):
- Yakıt, Avans, HGS, Trafik Cezası, Bakım, Ağır Bakım, Kaza, Kask,
  Telefon Tutacağı, Elcik, Motor Hasar, İdari Ceza, Fatura Edilemeyen
- Zimmet Taksiti (otomatik, equipment_issue_id ile)
- Motor satış taksidi (personnel.motor_purchase_monthly_amount)
- Aylık muhasebe bedeli (ÇK muhasebe için accountant_cost)
- Şirket açılış bedeli (yapıldıysa company_setup_cost — tek seferlik)

Net = Brüt + Kaptan bonusu − tüm kesintiler
"""
from psycopg.rows import dict_row

from app.core.database import get_connection


KAPTAN_BONUS = 3000.0


def _calc_brut_for_restaurant(
    pricing_model: str | None,
    rest_data: dict,
    hours: float,
    packages: int,
    is_full_threshold: bool = False,
) -> float:
    """Bir restorandaki kurye saat/paketi için brüt hesabı."""
    pm = (pricing_model or "").strip()
    hr = float(rest_data.get("hourly_rate") or 0)
    pr = float(rest_data.get("package_rate") or 0)
    lo = float(rest_data.get("package_rate_low") or 0)
    hi = float(rest_data.get("package_rate_high") or 0)
    threshold = int(rest_data.get("package_threshold") or 390)

    if pm == "hourly_only":
        return hours * hr
    if pm == "hourly_plus_package":
        return hours * hr + packages * pr
    if pm == "threshold_package":
        # Eşik karşılaştırması için kurye-restoran toplam paketleri kullan
        rate = hi if is_full_threshold else lo
        return hours * hr + packages * rate
    return 0


def list_personnel_payroll(period: str) -> list[dict]:
    """O ay maaş alacak tüm aktif kuryelerin brüt+kesinti+net özeti."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Aktif kuryeler + atanmış restoran bilgisi
            cur.execute(
                """
                SELECT
                    p.id, p.full_name, p.person_code, p.role,
                    p.assigned_restaurant_id,
                    COALESCE(p.monthly_fixed_cost, 0) AS monthly_fixed_cost,
                    COALESCE(p.fixed_monthly_billing, 0) AS fixed_monthly_billing,
                    COALESCE(p.motor_purchase_monthly_amount, 0) AS motor_taksit,
                    COALESCE(p.motor_rental_monthly_amount, 0) AS motor_kira,
                    COALESCE(p.accountant_cost, 0) AS muhasebe_aylik,
                    COALESCE(p.new_company_setup, 'Hayır') AS sirket,
                    COALESCE(p.company_setup_cost, 0) AS sirket_acilis,
                    COALESCE(p.company_setup_effective_date::text, '') AS sirket_tarih,
                    COALESCE(p.accounting_type, '') AS muhasebe_tipi,
                    r.brand AS rest_brand, r.branch AS rest_branch,
                    r.pricing_model AS pricing_model
                FROM personnel p
                LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
                WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
                  AND (
                      p.assigned_restaurant_id IS NULL
                      OR COALESCE(r.active, 1) = 1
                  )
                  AND EXISTS (
                      SELECT 1 FROM daily_entries d
                      WHERE d.actual_personnel_id = p.id
                        AND LEFT(d.entry_date::text, 7) = %s
                  )
                ORDER BY r.brand NULLS LAST, r.branch NULLS LAST, p.role, p.person_code
                """,
                (period,),
            )
            personnel = cur.fetchall()

            # 2. O ay tüm puantajları + restoran bilgisi
            cur.execute(
                """
                SELECT
                    d.actual_personnel_id AS pid,
                    d.restaurant_id AS rid,
                    d.worked_hours, d.package_count,
                    d.coverage_type,
                    r.pricing_model, r.hourly_rate, r.package_rate,
                    r.package_rate_low, r.package_rate_high,
                    r.package_threshold, r.fixed_monthly_fee
                FROM daily_entries d
                LEFT JOIN restaurants r ON r.id = d.restaurant_id
                WHERE LEFT(d.entry_date::text, 7) = %s
                  AND COALESCE(d.worked_hours, 0) > 0
                """,
                (period,),
            )
            entries = cur.fetchall()

            # 3. O ay tüm kesintiler
            cur.execute(
                """
                SELECT
                    d.personnel_id, d.deduction_type, d.amount, d.notes,
                    d.equipment_issue_id, e.item_name AS equipment_name,
                    e.installment_count
                FROM deductions d
                LEFT JOIN courier_equipment_issues e ON e.id = d.equipment_issue_id
                WHERE LEFT(d.deduction_date::text, 7) = %s
                """,
                (period,),
            )
            deductions = cur.fetchall()

    # Personel × restoran toplam paket (eşik karşılaştırması için)
    pkg_totals: dict[tuple[int, int], int] = {}
    for e in entries:
        if not e["pid"] or not e["rid"]:
            continue
        key = (e["pid"], e["rid"])
        pkg_totals[key] = pkg_totals.get(key, 0) + int(e.get("package_count") or 0)

    # Personel × restoran toplam saat / paket / gün
    by_courier: dict[int, dict] = {}
    for e in entries:
        pid = e["pid"]
        if pid is None:
            continue
        c = by_courier.setdefault(pid, {"main_hours": 0, "main_pkts": 0,
                                       "main_days": 0, "support_lines": [],
                                       "support_days": 0, "support_brut": 0.0})
        # Bu kayıt ana mı destek mi?
        # personel.assigned_restaurant_id'yi bul
        # Pratik: rid != assigned_restaurant_id veya coverage='Destek' → destek

    # Personellerin assigned_restaurant_id'sini kolayca al
    assigned_map = {p["id"]: p["assigned_restaurant_id"] for p in personnel}
    pricing_map: dict[int, dict] = {}
    for e in entries:
        if e["rid"] is not None:
            pricing_map[e["rid"]] = {
                "pricing_model": e["pricing_model"],
                "hourly_rate": e["hourly_rate"],
                "package_rate": e["package_rate"],
                "package_rate_low": e["package_rate_low"],
                "package_rate_high": e["package_rate_high"],
                "package_threshold": e["package_threshold"],
                "fixed_monthly_fee": e["fixed_monthly_fee"],
            }

    # 4. Her personel için brüt hesapla
    payroll: list[dict] = []
    for p in personnel:
        pid = p["id"]
        assigned_rid = p["assigned_restaurant_id"]
        c = by_courier.get(pid, {})
        # Bu kuryenin tüm Mart kayıtları
        my_entries = [e for e in entries if e["pid"] == pid]

        ana_hours = 0.0
        ana_pkts = 0
        ana_days = 0
        destek_lines: list[dict] = []
        destek_days_total = 0
        destek_brut_total = 0.0

        # Ana restoran toplamları (eşik için)
        for e in my_entries:
            rid = e["rid"]
            cov = (e.get("coverage_type") or "").strip()
            is_support = cov == "Destek" or (
                assigned_rid is not None and rid != assigned_rid
            )
            wh = float(e.get("worked_hours") or 0)
            pc = int(e.get("package_count") or 0)
            if is_support:
                # Destek satırını biriktir; aynı restorana birden fazla destek
                # gün varsa onları topla
                pass
            else:
                ana_hours += wh
                ana_pkts += pc
                ana_days += 1

        # Eşikli kontrol için ana restorandaki toplam paket
        ana_threshold_aşıldı = False
        if assigned_rid and p.get("pricing_model") == "threshold_package":
            threshold = int(
                pricing_map.get(assigned_rid, {}).get("package_threshold") or 390
            )
            ana_threshold_aşıldı = ana_pkts > threshold

        # Ana brüt hesabı
        ana_brut = 0.0
        is_fixed_billing = float(p["monthly_fixed_cost"] or 0) > 0
        if is_fixed_billing:
            # Sabit aylık personel — formül atlanır
            ana_brut = float(p["monthly_fixed_cost"])
        elif assigned_rid:
            rest_data = pricing_map.get(assigned_rid)
            if rest_data:
                pm = (rest_data.get("pricing_model") or "").strip()
                if pm == "fixed_monthly":
                    # Aylık sabit restoran — kurye sabit aylık (monthly_fixed_cost)
                    # Veride monthly_fixed_cost = 0 ise restoran tarifesinin
                    # 30'a bölümünden gün × ödenen
                    daily = (
                        float(rest_data.get("fixed_monthly_fee") or 0) / 30
                    )
                    ana_brut = daily * ana_days
                else:
                    ana_brut = _calc_brut_for_restaurant(
                        pm, rest_data, ana_hours, ana_pkts,
                        is_full_threshold=ana_threshold_aşıldı,
                    )

        # Destek hesabı (her destek restoranı ayrı)
        destek_by_rest: dict[int, dict] = {}
        for e in my_entries:
            rid = e["rid"]
            cov = (e.get("coverage_type") or "").strip()
            is_support = cov == "Destek" or (
                assigned_rid is not None and rid != assigned_rid
            )
            if not is_support or not rid:
                continue
            d = destek_by_rest.setdefault(rid, {"hours": 0, "pkts": 0, "days": 0})
            d["hours"] += float(e.get("worked_hours") or 0)
            d["pkts"] += int(e.get("package_count") or 0)
            d["days"] += 1

        for rid, dvals in destek_by_rest.items():
            rest_data = pricing_map.get(rid, {})
            pm = (rest_data.get("pricing_model") or "").strip()
            # Bu restorandaki destek paket eşiği — destek kuryesi kendi paket
            # sayısı ile eşik karşılaştırılır
            crossed = False
            if pm == "threshold_package":
                threshold = int(rest_data.get("package_threshold") or 390)
                crossed = dvals["pkts"] > threshold
            if pm == "fixed_monthly":
                # Destek günü × günlük tarife
                daily = float(rest_data.get("fixed_monthly_fee") or 0) / 30
                amt = daily * dvals["days"]
            else:
                amt = _calc_brut_for_restaurant(
                    pm, rest_data, dvals["hours"], dvals["pkts"], crossed,
                )
            destek_brut_total += amt
            destek_days_total += dvals["days"]
            destek_lines.append({
                "restaurant_id": rid,
                "days": dvals["days"],
                "hours": dvals["hours"],
                "packages": dvals["pkts"],
                "amount": round(amt, 2),
            })

        # Kaptan bonusu
        kaptan_bonus = (
            KAPTAN_BONUS if p["role"] == "Kaptan" and not is_fixed_billing else 0
        )

        # Toplam brüt
        toplam_brut = ana_brut + destek_brut_total + kaptan_bonus

        # 5. Kesintiler
        my_deductions = [d for d in deductions if d["personnel_id"] == pid]
        ded_groups: dict[str, dict] = {}
        ded_total = 0.0
        for d in my_deductions:
            t = d["deduction_type"]
            amt = float(d["amount"] or 0)
            ded_total += amt
            grp = ded_groups.setdefault(t, {"count": 0, "total": 0.0, "lines": []})
            grp["count"] += 1
            grp["total"] += amt
            line = {"amount": amt, "notes": d.get("notes")}
            if d.get("equipment_name"):
                line["equipment"] = d["equipment_name"]
                line["installments"] = d.get("installment_count")
            grp["lines"].append(line)

        # Sabit kesintiler (personnel'den)
        motor_taksit = float(p["motor_taksit"] or 0)
        muhasebe = float(p["muhasebe_aylik"] or 0) if p["muhasebe_tipi"] == "Çat Kapında Muhasebe" else 0
        sirket_acilis = 0.0
        # Şirket açılış bedeli — sadece o ay yapıldıysa düş
        if p["sirket"] == "Evet" and p["sirket_tarih"]:
            if p["sirket_tarih"][:7] == period:
                sirket_acilis = float(p["sirket_acilis"] or 0)

        sabit_total = motor_taksit + muhasebe + sirket_acilis

        # Net
        net = toplam_brut - ded_total - sabit_total

        payroll.append({
            "id": pid,
            "full_name": p["full_name"],
            "person_code": p["person_code"],
            "role": p["role"],
            "rest_brand": p["rest_brand"],
            "rest_branch": p["rest_branch"],
            "pricing_model": p.get("pricing_model"),
            "is_fixed_salary": is_fixed_billing,
            # Çalışma
            "ana_hours": round(ana_hours, 1),
            "ana_packages": ana_pkts,
            "ana_days": ana_days,
            "destek_days": destek_days_total,
            "destek_lines": destek_lines,
            # Brüt
            "ana_brut": round(ana_brut, 2),
            "destek_brut": round(destek_brut_total, 2),
            "kaptan_bonus": kaptan_bonus,
            "toplam_brut": round(toplam_brut, 2),
            # Kesintiler
            "motor_taksit": motor_taksit,
            "muhasebe": muhasebe,
            "sirket_acilis": sirket_acilis,
            "kesinti_groups": [
                {"type": t, **g} for t, g in ded_groups.items()
            ],
            "kesinti_total": round(ded_total, 2),
            "sabit_total": round(sabit_total, 2),
            # Net
            "net": round(net, 2),
        })

    # Özet
    total_brut = sum(x["toplam_brut"] for x in payroll)
    total_net = sum(x["net"] for x in payroll)
    total_kesinti = sum(x["kesinti_total"] + x["sabit_total"] for x in payroll)

    return {
        "period": period,
        "rows": payroll,
        "summary": {
            "courier_count": len(payroll),
            "total_brut": round(total_brut, 2),
            "total_kesinti": round(total_kesinti, 2),
            "total_net": round(total_net, 2),
        },
    }


def list_payroll(period: str) -> dict:
    """API'den çağrılan public fonksiyon."""
    return list_personnel_payroll(period=period)
