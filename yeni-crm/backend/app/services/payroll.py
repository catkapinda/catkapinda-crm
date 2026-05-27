"""Bordro servisi — kurye bazında aylık net hakediş hesabı.

Önemli kurallar:
- Tutarlar yuvarlanmaz, küsüratıyla saklanır.
- Motor kirası prorate edilir: ay içinde aktif gün × (aylık_tutar / 30).
  Sude 31.03.2026 işe girdiyse 1 gün × 13.000/30 = 433,33 ₺ kira düşer.
- Diğer aylık kesintiler (motor satış taksiti, muhasebe, şirket) tam aydır.

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
from calendar import monthrange
from datetime import date

from psycopg.rows import dict_row

from app.core.database import get_connection


def _parse_date(value: object) -> date | None:
    """ISO tarih veya date objesini date'e dönüştür."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def active_days_in_period(
    period: str,
    start_date: object | None,
    exit_date: object | None,
) -> int:
    """Bir kuryenin verilen ay (period: 'YYYY-MM') içindeki aktif gün sayısı.

    - start_date: işe giriş tarihi (varsa)
    - exit_date: işten ayrılış tarihi (varsa)
    - Aktif aralık ay sınırlarıyla kesişir; gün sayısı dahildir.
    """
    try:
        y, m = period.split("-")
        yi, mi = int(y), int(m)
    except (ValueError, AttributeError):
        return 30

    last_day = monthrange(yi, mi)[1]
    period_start = date(yi, mi, 1)
    period_end = date(yi, mi, last_day)

    sd = _parse_date(start_date)
    ed = _parse_date(exit_date)

    active_start = max(period_start, sd) if sd else period_start
    active_end = min(period_end, ed) if ed else period_end

    # Bu ayda hiç aktif değilse 0
    if sd and sd > period_end:
        return 0
    if ed and ed < period_start:
        return 0

    return max(0, (active_end - active_start).days + 1)


KAPTAN_BONUS = 3000.0

# KDV tevkifat parametreleri (v2'den taşındı)
VAT_RATE = 0.20  # %20 KDV
TEVKIFAT_RATE = 0.20  # KDV'nin %20'si tevkifat olarak alıkonur
TEVKIFAT_THRESHOLD = 12000.0  # 12.000 ₺ altı fatura tevkifat'tan muaf

# Fatura matrahını düşüren kesinti tipleri (faturadan önce düşülür)
INVOICE_BASE_REDUCING_TYPES = {"Fatura Edilmeyen Tutar", "Fatura Edilemeyen Tutar"}


def calculate_tevkifat(invoice_total: float) -> dict:
    """KDV tevkifat hesabı.

    Args:
        invoice_total: Brüt fatura tutarı (KDV dahil)
    Returns:
        invoice_base_amount: KDV hariç matrah
        vat_amount: KDV tutarı (matrah × %20)
        tevkifat_amount: Tevkifat tutarı (KDV × %20, threshold üzerindeyse)
    """
    if invoice_total <= 0:
        return {"invoice_base_amount": 0.0, "vat_amount": 0.0, "tevkifat_amount": 0.0}

    invoice_base = invoice_total / (1 + VAT_RATE)
    vat = invoice_total - invoice_base
    tevkifat = vat * TEVKIFAT_RATE if invoice_total >= TEVKIFAT_THRESHOLD else 0.0
    return {
        "invoice_base_amount": round(invoice_base, 2),
        "vat_amount": round(vat, 2),
        "tevkifat_amount": round(tevkifat, 2),
    }


def _calc_brut_for_restaurant(
    pricing_model: str | None,
    rest_data: dict,
    hours: float,
    packages: int,
    is_full_threshold: bool = False,
) -> float:
    """Bir restorandaki kurye saat/paketi için brüt hesabı.

    KURYE TARAFI tarifeleri kullanılır (restaurants.courier_*).
    Bu tarifeler restoranın bize kestiği (hourly_rate, package_rate_*) ile
    KARIŞTIRILMAMALI. Örnek Fasuli/SushiCo/Quick China:
      Restoran (CK alır): saatlik 273, paket low/high 34/47 — KDV hariç
      Kurye   (CK öder): saatlik 250, paket low/high 20/25 — KDV dahil

    Sistem default (Fasuli/SushiCo/Köroğlu vb.): threshold_package
    eşik 390, low 20, high 25, saatlik 250.
    Quick China özel: hourly_plus_package, saatlik 250 + paket 25 sabit.

    Restoran'da courier_* kolonları doluysa onlar, değilse default.
    """
    # Kurye tarafı tarifeleri — daima courier_* alanları + ÇK standardı default
    # NOT: Restoran pm'i (fixed_monthly, hourly_only vb.) buraya etki ETMEZ.
    # Sistem default: threshold_package 250/390/20/25 (Quick China override
    # ile hourly_plus_package olur; Doğu Otomotiv courier_hourly_rate=295).
    courier_pm = (
        rest_data.get("courier_pricing_model")
        or "threshold_package"
    ).strip()
    hr = float(rest_data.get("courier_hourly_rate") or 250)
    pr = float(rest_data.get("courier_package_rate") or 0)
    lo = float(rest_data.get("courier_package_rate_low") or 20)
    hi = float(rest_data.get("courier_package_rate_high") or 25)

    if courier_pm == "hourly_only":
        return hours * hr
    if courier_pm == "hourly_plus_package":
        return hours * hr + packages * pr
    # Default: threshold_package
    rate = hi if is_full_threshold else lo
    return hours * hr + packages * rate


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
                    -- Vardiya standardı: önce restoran (her restoranın kendi
                    -- vardiya saati), sonra personel kaydı, son çare 11
                    COALESCE(
                        NULLIF(r.standard_daily_hours, 0),
                        NULLIF(p.standard_daily_hours, 0),
                        11
                    ) AS standard_daily_hours,
                    COALESCE(p.motor_purchase_monthly_amount, 0) AS motor_taksit,
                    COALESCE(p.motor_purchase, '') AS motor_purchase_flag,
                    COALESCE(p.motor_rental_monthly_amount, 0) AS motor_kira_aylik,
                    COALESCE(p.motor_rental, '') AS motor_rental_flag,
                    COALESCE(p.vehicle_type, '') AS vehicle_type,
                    COALESCE(p.accountant_cost, 0) AS muhasebe_aylik,
                    COALESCE(p.new_company_setup, 'Hayır') AS sirket,
                    COALESCE(p.company_setup_cost, 0) AS sirket_acilis,
                    COALESCE(p.company_setup_effective_date::text, '') AS sirket_tarih,
                    COALESCE(p.accounting_type, '') AS muhasebe_tipi,
                    p.start_date::text AS start_date,
                    p.exit_date::text AS exit_date,
                    r.brand AS rest_brand, r.branch AS rest_branch,
                    r.pricing_model AS pricing_model
                FROM personnel p
                LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
                WHERE (
                      -- Aktif kişiler her zaman dahil
                      COALESCE(p.status, 'Aktif') = 'Aktif'
                      -- Pasif kişiler: exit_date'leri bu dönemden ÖNCE
                      -- DEĞİLSE dahil. Yani 19 Mart pasife alınan Mart
                      -- bordrosunda var, Nisan'da yok.
                      OR (
                          COALESCE(p.exit_date::date, '1900-01-01'::date)
                          >= (%s || '-01')::date
                      )
                  )
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
                (period, period),
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
                    r.package_threshold, r.fixed_monthly_fee,
                    -- KURYE TARAFI tarifeleri (CK'nin kuryeye ödediği)
                    r.courier_pricing_model,
                    r.courier_hourly_rate,
                    r.courier_package_rate,
                    r.courier_package_rate_low,
                    r.courier_package_rate_high,
                    r.courier_package_threshold
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
                # Restoran tarafı (CK alır) — geriye uyumluluk için
                "pricing_model": e["pricing_model"],
                "hourly_rate": e["hourly_rate"],
                "package_rate": e["package_rate"],
                "package_rate_low": e["package_rate_low"],
                "package_rate_high": e["package_rate_high"],
                "package_threshold": e["package_threshold"],
                "fixed_monthly_fee": e["fixed_monthly_fee"],
                # KURYE TARAFI (CK öder) — hakediş hesabında kullanılır
                "courier_pricing_model": e.get("courier_pricing_model"),
                "courier_hourly_rate": e.get("courier_hourly_rate"),
                "courier_package_rate": e.get("courier_package_rate"),
                "courier_package_rate_low": e.get("courier_package_rate_low"),
                "courier_package_rate_high": e.get("courier_package_rate_high"),
                "courier_package_threshold": e.get("courier_package_threshold"),
            }

    # Restaurant brand/branch — destek satırlarında göstermek için
    rest_info_map: dict[int, dict] = {}
    try:
        with get_connection() as conn2:
            with conn2.cursor(row_factory=dict_row) as cur2:
                cur2.execute(
                    "SELECT id, brand, branch, pricing_model FROM restaurants"
                )
                for row in cur2.fetchall():
                    rest_info_map[int(row["id"])] = {
                        "brand": row.get("brand"),
                        "branch": row.get("branch"),
                        "pricing_model": row.get("pricing_model"),
                    }
    except Exception:
        pass

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
        # Eşik karşılaştırması KURYE tarafından (CK'nın kurye eşiği — default 390).
        # Restoran modeli courier override etmediyse pricing_model'i takip et.
        rest_pricing = pricing_map.get(assigned_rid, {}) if assigned_rid else {}
        courier_pm = (rest_pricing.get("courier_pricing_model")
                      or p.get("pricing_model") or "")
        if assigned_rid and (courier_pm == "threshold_package"
                             or p.get("pricing_model") == "threshold_package"):
            threshold = int(
                rest_pricing.get("courier_package_threshold")
                or rest_pricing.get("package_threshold")
                or 390
            )
            ana_threshold_aşıldı = ana_pkts > threshold

        # Ana brüt hesabı
        ana_brut = 0.0
        ekstra_mesai_brut = 0.0  # bayram x2 fazlası → ana brut'a eklenir
        ekstra_mesai_days = 0.0
        is_fixed_billing = float(p["monthly_fixed_cost"] or 0) > 0
        std_daily = float(p.get("standard_daily_hours") or 11)

        if is_fixed_billing:
            # Sabit aylık personel — formül atlanır
            ana_brut = float(p["monthly_fixed_cost"])

            # Bayram / ekstra mesai: günlük standart üstündeki saatler
            # (örn 22 saat yazılan bayram günü → 11 saat fazla = 1 gün ekstra)
            if std_daily > 0:
                overtime_hours = 0.0
                for e in my_entries:
                    cov = (e.get("coverage_type") or "").strip()
                    if cov == "Destek":
                        continue  # destek günleri ana atamada sayılmaz
                    e_assigned = e.get("assigned_restaurant_id")
                    if e_assigned is not None and e["rid"] != e_assigned:
                        continue  # destek (ana atama dışı)
                    wh = float(e.get("worked_hours") or 0)
                    if wh > std_daily:
                        overtime_hours += wh - std_daily
                if overtime_hours > 0:
                    ekstra_mesai_days = overtime_hours / std_daily
                    daily_rate = ana_brut / 30
                    ekstra_mesai_brut = daily_rate * ekstra_mesai_days
                    ana_brut += ekstra_mesai_brut

        elif assigned_rid:
            rest_data = pricing_map.get(assigned_rid)
            if rest_data:
                pm = (rest_data.get("pricing_model") or "").strip()
                # KURYE hakediş hesabı restoran modelinden bağımsız —
                # daima _calc_brut_for_restaurant (default threshold_package
                # 250/390/20/25, courier_* override'ları varsa onlar).
                # Restoran pm = fixed_monthly bile olsa kurye threshold ile
                # hesaplanır (per-courier monthly_fixed_cost > 0 olan
                # özel kayıtlar zaten yukarıdaki sabit dal'da yakalanır).
                ana_brut = _calc_brut_for_restaurant(
                    pm, rest_data, ana_hours, ana_pkts,
                    is_full_threshold=ana_threshold_aşıldı,
                )

        # Destek hesabı (her destek restoranı ayrı)
        # NOT — coverage_type='Yönetim' (Joker/BM/Kaptan/RTŞ operasyon kapama):
        #   • KURYEYE ekstra ücret YOK → bordro destek_brut=0 (sabit aylık zaten
        #     yeterli, ek hak ediş üretmez)
        #   • RESTORANA fatura YANSIR → daily_entries kaydı durur, restoran
        #     paket×tarife / saat×tarife olarak faturalanır (collections.py)
        #   destek_lines'a coverage_kind='Yönetim' ile amount=0 ekleniyor —
        #   audit trail için. Marj hesabı bu blokları görür ama bordro toplam
        #   brut'a etki etmez.
        destek_by_rest: dict[int, dict] = {}
        for e in my_entries:
            rid = e["rid"]
            cov = (e.get("coverage_type") or "").strip()
            is_yonetim_cover = cov == "Yönetim"
            is_support = (
                cov == "Destek"
                or is_yonetim_cover
                or (assigned_rid is not None and rid != assigned_rid)
            )
            if not is_support or not rid:
                continue
            d = destek_by_rest.setdefault(
                rid,
                {"hours": 0, "pkts": 0, "days": 0, "yonetim": False},
            )
            d["hours"] += float(e.get("worked_hours") or 0)
            d["pkts"] += int(e.get("package_count") or 0)
            d["days"] += 1
            # Bir gün bile Yönetim kaydı varsa o restoran-destek bloğu
            # yönetim olarak işaretlenir (fiyatlandırma yapılmaz).
            if is_yonetim_cover:
                d["yonetim"] = True

        for rid, dvals in destek_by_rest.items():
            rest_data = pricing_map.get(rid, {})
            pm = (rest_data.get("pricing_model") or "").strip()
            courier_pm_support = (
                (rest_data.get("courier_pricing_model") or pm or "").strip()
            )

            # Yönetim destek satırı → ekstra ücret yok
            if dvals.get("yonetim"):
                amt = 0.0
            else:
                # Bu restorandaki destek paket eşiği — kurye eşiği (default 390)
                crossed = False
                if courier_pm_support == "threshold_package" or pm == "threshold_package":
                    threshold = int(
                        rest_data.get("courier_package_threshold")
                        or rest_data.get("package_threshold")
                        or 390
                    )
                    crossed = dvals["pkts"] > threshold
                # Destek hesabı — restoran modelinden bağımsız, kurye threshold
                # default'u uygulanır (250/390/20/25 + courier_* override).
                amt = _calc_brut_for_restaurant(
                    pm, rest_data, dvals["hours"], dvals["pkts"], crossed,
                )

            destek_brut_total += amt
            destek_days_total += dvals["days"]
            rinfo = rest_info_map.get(rid, {})
            destek_lines.append({
                "restaurant_id": rid,
                "rest_brand": rinfo.get("brand"),
                "rest_branch": rinfo.get("branch"),
                "pricing_model": rinfo.get("pricing_model") or pm,
                "days": dvals["days"],
                "hours": dvals["hours"],
                "packages": dvals["pkts"],
                "amount": round(amt, 2),
                "coverage_kind": "Yönetim" if dvals.get("yonetim") else "Destek",
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
        # Araç tipi: "Çat Kapında Satış", "Çat Kapında Kiralık", "Kendi Motoru"
        vehicle_type = (p.get("vehicle_type") or "").strip()
        is_own_motor = vehicle_type == "Kendi Motoru"

        # Motor satış taksiti — sadece "Çat Kapında Satış" + flag "Evet" + tutar > 0
        # Kendi motoru ile çalışan kuryelerden taksit kesilmez
        motor_taksit = 0.0
        if not is_own_motor and p.get("motor_purchase_flag") == "Evet":
            motor_taksit = float(p["motor_taksit"] or 0)

        # Motor kirası — ay içindeki aktif gün × (aylık tutar / 30)
        # Sude 31.03 işe girdiyse 1 gün × 13.000/30 = 433,33 ₺
        # Kendi motoru ile çalışan kuryelerden kira kesilmez
        motor_kira = 0.0
        if not is_own_motor and p.get("motor_rental_flag") == "Evet":
            kira_aylik = float(p.get("motor_kira_aylik") or 0)
            if kira_aylik > 0:
                aktif_gun = active_days_in_period(
                    period, p.get("start_date"), p.get("exit_date")
                )
                # Tam ay (30+) tam kira, daha azsa orantılı
                prorate = min(aktif_gun, 30) / 30
                motor_kira = kira_aylik * prorate

        muhasebe = (
            float(p["muhasebe_aylik"] or 0)
            if p["muhasebe_tipi"] == "Çat Kapında Muhasebe"
            else 0
        )
        sirket_acilis = 0.0
        # Şirket açılış bedeli — sadece o ay yapıldıysa düş
        if p["sirket"] == "Evet" and p["sirket_tarih"]:
            if p["sirket_tarih"][:7] == period:
                sirket_acilis = float(p["sirket_acilis"] or 0)

        sabit_total = motor_taksit + motor_kira + muhasebe + sirket_acilis

        # KDV + Tevkifat hesabı — şahıs şirketi/serbest meslek kuryeleri (hem
        # 'Çat Kapında Muhasebe' hem 'Kendi Muhasebecisi') KDV dahil fatura
        # keser; KDV'nin %20'si tevkifat olarak ÇK tarafından alıkonur.
        # Fatura matrahı: brüt − ("Fatura Edilmeyen Tutar" + motor satış taksiti).
        # Motor satış taksiti faturadan düşülür (kuryenin kendi varlığı haline
        # geliyor) → KDV ve tevkifat o tutar üzerinden hesaplanmaz.
        invoice_base_reducing = sum(
            float(d["amount"] or 0)
            for d in my_deductions
            if d["deduction_type"] in INVOICE_BASE_REDUCING_TYPES
        )
        invoice_base_reducing += motor_taksit  # motor satış taksiti
        muhasebe_tipi = (p["muhasebe_tipi"] or "").strip()
        is_invoice_courier = True  # KDV dahil fatura keserler
        is_ck_muhasebe = muhasebe_tipi == "Çat Kapında Muhasebe"
        tevkifat_breakdown = {
            "invoice_base_amount": 0.0,
            "vat_amount": 0.0,
            "tevkifat_amount": 0.0,
            "fatura_total": 0.0,
        }
        tevkifat_amount = 0.0
        if is_invoice_courier:
            invoice_total = max(toplam_brut - invoice_base_reducing, 0.0)
            tevkifat_breakdown = calculate_tevkifat(invoice_total)
            tevkifat_breakdown["fatura_total"] = round(invoice_total, 2)
            tevkifat_amount = tevkifat_breakdown["tevkifat_amount"]

        # Net
        net = toplam_brut - ded_total - sabit_total - tevkifat_amount

        payroll.append({
            "id": pid,
            "full_name": p["full_name"],
            "person_code": p["person_code"],
            "role": p["role"],
            "assigned_restaurant_id": assigned_rid,
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
            "ana_brut": round(ana_brut - ekstra_mesai_brut, 2),
            "ekstra_mesai_brut": round(ekstra_mesai_brut, 2),
            "ekstra_mesai_days": round(ekstra_mesai_days, 2),
            "destek_brut": round(destek_brut_total, 2),
            "kaptan_bonus": kaptan_bonus,
            "toplam_brut": round(toplam_brut, 2),
            # Kesintiler
            "motor_taksit": motor_taksit,
            "motor_kira": round(motor_kira, 2),
            "muhasebe": muhasebe,
            "sirket_acilis": sirket_acilis,
            "kesinti_groups": [
                {"type": t, **g} for t, g in ded_groups.items()
            ],
            "kesinti_total": round(ded_total, 2),
            "sabit_total": round(sabit_total, 2),
            # Tevkifat
            "tevkifat": round(tevkifat_amount, 2),
            "tevkifat_breakdown": tevkifat_breakdown,
            "is_ck_muhasebe": is_ck_muhasebe,
            # Net
            "net": round(net, 2),
        })

    # Özet
    total_brut = sum(x["toplam_brut"] for x in payroll)
    total_net = sum(x["net"] for x in payroll)
    total_kesinti = sum(
        x["kesinti_total"] + x["sabit_total"] + x["tevkifat"] for x in payroll
    )
    total_tevkifat = sum(x["tevkifat"] for x in payroll)

    return {
        "period": period,
        "rows": payroll,
        "summary": {
            "courier_count": len(payroll),
            "total_brut": round(total_brut, 2),
            "total_kesinti": round(total_kesinti, 2),
            "total_tevkifat": round(total_tevkifat, 2),
            "total_net": round(total_net, 2),
        },
    }


def list_payroll(period: str) -> dict:
    """API'den çağrılan public fonksiyon."""
    return list_personnel_payroll(period=period)


def get_personnel_payroll(personnel_id: int, period: str) -> dict | None:
    """Tek kurye için bordro detayı (PDF/yazdır için)."""
    result = list_personnel_payroll(period=period)
    for r in result["rows"]:
        if r["id"] == personnel_id:
            return r
    return None
