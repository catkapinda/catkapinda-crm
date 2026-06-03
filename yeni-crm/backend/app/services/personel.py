"""Personel servis — listeleme ve CRUD operasyonları."""
from psycopg.rows import dict_row

from app.core.database import get_connection


# Güncellenebilir kolonlar — beyaz liste
EDITABLE_COLUMNS: set[str] = {
    # Temel
    "full_name", "person_code", "role", "status", "phone", "current_plate",
    "assigned_restaurant_id", "start_date", "exit_date",
    # Hakediş & faturalandırma
    "monthly_fixed_cost",            # kuryeye ödenen aylık (sabit)
    "fixed_monthly_billing",         # restorana yansıyan sabit aylık (KDV hariç)
    # Kimlik & banka
    "tc_no", "iban", "tax_number", "tax_office",
    # Adres & acil durum
    "address", "emergency_contact_name", "emergency_contact_phone", "notes",
    # Araç
    "vehicle_type",
    "motor_purchase", "motor_purchase_sale_price",
    "motor_purchase_start_date", "motor_purchase_commitment_months",
    "motor_purchase_installment_count", "motor_purchase_monthly_amount",
    "motor_purchase_monthly_deduction",
    "motor_rental", "motor_rental_monthly_amount",
    "motor_rental_effective_date", "motor_end_date",
    # Muhasebe
    "accounting_type", "accountant_cost", "accounting_revenue",
    "accounting_effective_date",
    # Şirket açılışı
    "new_company_setup", "company_setup_cost", "company_setup_revenue",
    "company_setup_effective_date",
    "cost_model",
}


# Detaylı tek-kayıt için döndürülen kolonlar
DETAIL_COLUMNS = """
    id, person_code, full_name, role, status, phone, current_plate,
    assigned_restaurant_id, start_date, exit_date,
    monthly_fixed_cost, fixed_monthly_billing,
    vehicle_type,
    motor_purchase, motor_purchase_sale_price, motor_purchase_start_date,
    motor_purchase_commitment_months, motor_purchase_installment_count,
    motor_purchase_monthly_amount, motor_purchase_monthly_deduction,
    motor_rental, motor_rental_monthly_amount, motor_rental_effective_date,
    motor_end_date,
    accounting_type, accountant_cost, accounting_revenue,
    accounting_effective_date,
    new_company_setup, company_setup_cost, company_setup_revenue,
    company_setup_effective_date, cost_model,
    tc_no, iban, tax_number, tax_office,
    address, emergency_contact_name, emergency_contact_phone, notes
"""


def list_personnel(status: str | None = None) -> list[dict]:
    """Personel listesi getir."""
    sql = f"""
        SELECT {DETAIL_COLUMNS}
        FROM personnel
    """
    params: list = []
    if status:
        sql += " WHERE status = %s"
        params.append(status)
    sql += " ORDER BY person_code"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


def get_personnel(personnel_id: int) -> dict | None:
    """Tek personel detayı."""
    sql = f"SELECT {DETAIL_COLUMNS} FROM personnel WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (personnel_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def update_personnel(personnel_id: int, fields: dict) -> dict | None:
    """Personel alanlarını güncelle. Sadece beyaz listedeki alanlar."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    if not safe:
        return get_personnel(personnel_id)

    set_parts = [f"{col} = %s" for col in safe.keys()]
    sql = f"""
        UPDATE personnel
        SET {', '.join(set_parts)}
        WHERE id = %s
        RETURNING id
    """
    params = list(safe.values()) + [personnel_id]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            updated = cur.fetchone()
            conn.commit()
    if not updated:
        return None
    return get_personnel(personnel_id)


class DeactivationError(Exception):
    """Pasife alma akışında ön-koşul karşılanmadığında atılır.

    code: bordro_yok | bordro_imzasiz | bordro_odenmedi | zaten_pasif
    detail: insan-okur Türkçe mesaj
    context: opsiyonel ek alanlar (period, signature_id, vs.)
    """

    def __init__(self, code: str, detail: str, context: dict | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.context = context or {}


def _last_period_with_entries(personnel_id: int) -> str | None:
    """Kişinin daily_entries içinde puantajı olan en son ayı döner (YYYY-MM).

    NOT: daily_entries'te kurye kolonu 'actual_personnel_id'dir
    (personnel_id YOK). Yanlış kolon adı 500'e yol açıyordu.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TO_CHAR(MAX(entry_date), 'YYYY-MM') AS last_period
                FROM daily_entries
                WHERE actual_personnel_id = %s
                """,
                (personnel_id,),
            )
            row = cur.fetchone()
    return row[0] if row and row[0] else None


def _signature_state(personnel_id: int, period: str) -> dict | None:
    """Bir kişinin verilen dönem için bordro/imza/ödeme durumunu döner.

    Dönüş: None (kayıt yok) | dict {id, signed_at, paid_at}
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, signed_at, paid_at
                FROM payroll_signatures
                WHERE personnel_id = %s AND period = %s
                LIMIT 1
                """,
                (personnel_id, period),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def deactivate_personnel(personnel_id: int, exit_date: str) -> dict:
    """Personeli pasife al — ön kontroller geçilirse status='Pasif' + exit_date.

    Akış:
      1. Personel mevcut mu? Zaten pasif mi?
      2. Son puantajı olan ay'ı bul → o ay için bordro hazır mı?
         - Hazır değilse: DeactivationError('bordro_yok', ...)
      3. Bordro imzalı mı? Değilse: DeactivationError('bordro_imzasiz', ...)
      4. Bordro ödendi (paid_at NOT NULL)? Değilse: DeactivationError('bordro_odenmedi', ...)
      5. Hepsi tamamsa: status='Pasif', exit_date = parametre
    """
    # 1. Personel kontrolü
    person = get_personnel(personnel_id)
    if not person:
        raise DeactivationError(
            "bulunamadi",
            "Personel bulunamadı.",
        )
    if (person.get("status") or "Aktif") == "Pasif":
        raise DeactivationError(
            "zaten_pasif",
            f"{person.get('full_name')} zaten pasif durumda.",
            {"exit_date": person.get("exit_date")},
        )

    # 2. Son puantaj ayı
    last_period = _last_period_with_entries(personnel_id)
    if not last_period:
        # Hiç puantajı yoksa direkt pasife alabilir (yeni eklenmiş ama hiç çalışmamış)
        # Bu pratikte 'iptal' senaryosudur, mali yükümlülük yok
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE personnel
                    SET status = 'Pasif', exit_date = %s
                    WHERE id = %s
                    """,
                    (exit_date, personnel_id),
                )
                conn.commit()
        return get_personnel(personnel_id) or {}

    # 3. Son ay bordrosu hazır mı?
    sig = _signature_state(personnel_id, last_period)
    if not sig:
        raise DeactivationError(
            "bordro_yok",
            f"{person.get('full_name')} için {last_period} bordrosu henüz "
            "hazırlanmamış. Pasife almadan önce bordroyu hazırlayıp kuryeye "
            "imzalatmanız ve ödemeyi tamamlamanız gerekiyor.",
            {"period": last_period},
        )

    # 4. İmzalı mı?
    if not sig.get("signed_at"):
        raise DeactivationError(
            "bordro_imzasiz",
            f"{last_period} dönemi bordrosu kuryenin imzasını bekliyor. "
            "Kurye CRM üzerinden imzaladıktan sonra ödeme yapıp pasife alabilirsiniz.",
            {"period": last_period, "signature_id": sig.get("id")},
        )

    # 5. Ödendi mi?
    if not sig.get("paid_at"):
        raise DeactivationError(
            "bordro_odenmedi",
            f"{last_period} dönemi bordrosu imzalı ancak ödeme henüz yapılmadı. "
            "Hakediş Onayları'ndan ödemeyi işaretleyip ardından pasife alabilirsiniz.",
            {"period": last_period, "signature_id": sig.get("id")},
        )

    # Tüm koşullar tamam — pasife al
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE personnel
                SET status = 'Pasif', exit_date = %s
                WHERE id = %s
                """,
                (exit_date, personnel_id),
            )
            conn.commit()

    return get_personnel(personnel_id) or {}


def delete_personnel_cascade(personnel_id: int) -> bool:
    """Personeli kalıcı olarak sil — tüm ilişkili kayıtlarla.

    Cascade silinen tablolar (sıra önemli — foreign key bağımlılığı):
      - daily_entries (col: actual_personnel_id) — puantaj girişleri
      - deductions — kesintiler
      - equipment_assignments — ekipman zimmeti
      - courier_sessions — kurye CRM giriş token'ları
      - payroll_signatures — bordro imzaları
      - payroll_sms_log — gönderilmiş SMS log'ları
      - courier_requests — motor/muhasebe/avans talepleri
      - personnel — asıl kayıt

    Tablo yoksa atlanır (to_regclass kontrolü). Tek transaction —
    biri patlarsa hiçbiri silinmez.
    """
    person = get_personnel(personnel_id)
    if not person:
        return False

    # ÖNEMLİ: daily_entries kolonu 'actual_personnel_id', diğerleri 'personnel_id'.
    # Tablolar foreign key bağımlılığına göre sıralı silinir.
    related_tables = [
        ("daily_entries", "actual_personnel_id"),
        ("deductions", "personnel_id"),
        ("equipment_assignments", "personnel_id"),
        ("courier_sessions", "personnel_id"),
        ("payroll_signatures", "personnel_id"),
        ("payroll_sms_log", "personnel_id"),
        ("courier_requests", "personnel_id"),
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for table, col in related_tables:
                # Tablo var mı kontrol et — eksikse atla
                cur.execute(
                    "SELECT to_regclass(%s) IS NOT NULL AS exists",
                    (f"public.{table}",),
                )
                row = cur.fetchone()
                if not (row and row[0]):
                    continue

                # Kolon var mı kontrol et — eski schema'da olmayabilir
                cur.execute(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                      AND column_name = %s
                    """,
                    (table, col),
                )
                if not cur.fetchone():
                    continue

                cur.execute(
                    f"DELETE FROM {table} WHERE {col} = %s",
                    (personnel_id,),
                )

            # Asıl personel kaydı
            cur.execute(
                "DELETE FROM personnel WHERE id = %s",
                (personnel_id,),
            )
            conn.commit()
    return True


def create_personnel(fields: dict) -> dict | None:
    """Yeni personel ekle."""
    safe = {k: v for k, v in fields.items() if k in EDITABLE_COLUMNS}
    # En azından isim ve rol gerekli
    if not safe.get("full_name") or not safe.get("role"):
        raise ValueError("İsim ve rol zorunludur")

    cols = list(safe.keys())
    vals = list(safe.values())
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"""
        INSERT INTO personnel ({', '.join(cols)})
        VALUES ({placeholders})
        RETURNING id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vals)
            row = cur.fetchone()
            conn.commit()
    if not row:
        return None
    return get_personnel(row[0])


def page_insights(period: str) -> dict:
    """Personel sayfası için akıllı içgörüler — gerçek puantaj verisi üzerinden."""
    insights: dict = {
        "threshold_near": [],
        "capacity_gaps": [],
        "top_recovery": [],
        "pending_actions": 0,
    }

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Eşik aşımı yakın olanlar (eşikli restoranda 300-500 paket arası)
            cur.execute(
                """
                SELECT
                    p.id, p.full_name, p.person_code,
                    r.brand, r.branch,
                    r.package_threshold,
                    r.package_rate_low, r.package_rate_high,
                    COALESCE(SUM(d.package_count), 0) AS pkts
                FROM daily_entries d
                JOIN personnel p ON p.id = d.actual_personnel_id
                JOIN restaurants r ON r.id = d.restaurant_id
                WHERE LEFT(d.entry_date::text, 7) = %s
                  AND r.pricing_model = 'threshold_package'
                  AND COALESCE(p.status, 'Aktif') = 'Aktif'
                  AND COALESCE(d.worked_hours, 0) > 0
                GROUP BY p.id, p.full_name, p.person_code,
                         r.brand, r.branch, r.package_threshold,
                         r.package_rate_low, r.package_rate_high
                HAVING SUM(COALESCE(d.package_count, 0)) BETWEEN 300 AND 500
                ORDER BY pkts DESC
                LIMIT 5
                """,
                (period,),
            )
            insights["threshold_near"] = [
                {
                    "id": r["id"],
                    "full_name": r["full_name"],
                    "person_code": r["person_code"],
                    "brand": r["brand"],
                    "branch": r["branch"],
                    "packages": int(r["pkts"] or 0),
                    "threshold": int(r["package_threshold"] or 390),
                    "rate_low": float(r["package_rate_low"] or 0),
                    "rate_high": float(r["package_rate_high"] or 0),
                }
                for r in cur.fetchall()
            ]

            # 2. Eksik kapasite (target > actual)
            cur.execute(
                """
                SELECT
                    r.id, r.brand, r.branch, r.target_headcount,
                    COUNT(DISTINCT d.actual_personnel_id)
                        FILTER (WHERE COALESCE(d.worked_hours, 0) > 0) AS actual
                FROM restaurants r
                LEFT JOIN daily_entries d
                    ON d.restaurant_id = r.id
                   AND LEFT(d.entry_date::text, 7) = %s
                WHERE COALESCE(r.active, 1) = 1
                  AND COALESCE(r.target_headcount, 0) > 0
                GROUP BY r.id, r.brand, r.branch, r.target_headcount
                HAVING COUNT(DISTINCT d.actual_personnel_id)
                       FILTER (WHERE COALESCE(d.worked_hours, 0) > 0)
                       < r.target_headcount
                ORDER BY
                    (r.target_headcount -
                     COUNT(DISTINCT d.actual_personnel_id)
                       FILTER (WHERE COALESCE(d.worked_hours, 0) > 0)) DESC
                LIMIT 5
                """,
                (period,),
            )
            insights["capacity_gaps"] = [
                {
                    "id": r["id"],
                    "brand": r["brand"],
                    "branch": r["branch"],
                    "target": int(r["target_headcount"] or 0),
                    "actual": int(r["actual"] or 0),
                }
                for r in cur.fetchall()
            ]

    # 3. Top recovery — SADECE Bölge Müdürü ve Joker.
    # Cover kavramı sadece sabit maaşlı yönetim rolleri için anlamlıdır.
    # Kurye/Kaptan: çalıştıkları her şey değişken ödemeyle dönüyor (zaten gider).
    # RTŞ: maaşı restoran tarafından karşılanır, bizim cebimizden değil.
    # Sadece BM+Joker bizim cebimizden sabit maaş alır → saha çalışmasıyla
    # restoran faturasına yansıyan tutar 'cover'ı oluşturur.
    mgmt = management_summary(period=period)
    scored = []
    for m in mgmt:
        if m["salary"] <= 0:
            continue
        if m["role"] not in ("Bölge Müdürü", "Joker"):
            continue
        # BM/Joker sabit maaşlıdır; SAHADAKİ HER GÜN (kendi restoranı dahil)
        # restoran faturasına yansır → maaş geri kazanımına sayılır.
        # field_* tüm saha günlerini kapsar (cover_* yalnızca kendi restoranı
        # dışıydı; BM tek restorana atanmışsa cover=0 olup yanlış 0% çıkıyordu).
        field_hours = m.get("field_hours", m["cover_hours"])
        field_packages = m.get("field_packages", m["cover_packages"])
        recovered = field_hours * 200 + field_packages * 25
        pct = min(1.0, recovered / m["salary"]) if m["salary"] else 0
        scored.append({
            **m,
            "recovery_pct": round(pct, 3),
            "recovered_amount": round(recovered, 2),
        })
    scored.sort(key=lambda x: -x["recovery_pct"])
    insights["top_recovery"] = scored[:2]

    return insights


def top_performers(period: str, limit: int = 3) -> list[dict]:
    """Aya göre paket sayısı en yüksek personel (sahne için)."""
    sql = """
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            r.brand, r.branch,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COUNT(*) FILTER (WHERE d.worked_hours > 0) AS working_days
        FROM daily_entries d
        JOIN personnel p ON p.id = d.actual_personnel_id
        LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
        WHERE LEFT(d.entry_date::text, 7) = %s
          -- Aktif kişiler her zaman; pasif kişiler ancak exit_date'i bu
          -- dönemden ÖNCE değilse (o dönem içinde aktiflerdi).
          AND (
              COALESCE(p.status, 'Aktif') = 'Aktif'
              OR COALESCE(p.exit_date::date, '1900-01-01'::date)
                 >= (%s || '-01')::date
          )
          AND COALESCE(d.worked_hours, 0) > 0
        GROUP BY p.id, p.full_name, p.person_code, p.role, r.brand, r.branch
        HAVING COALESCE(SUM(d.package_count), 0) > 0
        ORDER BY total_packages DESC, total_hours DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period, period, limit))
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "brand": r["brand"],
            "branch": r["branch"],
            "total_packages": int(r["total_packages"] or 0),
            "total_hours": float(r["total_hours"] or 0),
            "working_days": int(r["working_days"] or 0),
        })
    return out


def management_summary(period: str) -> list[dict]:
    """Yönetim & Yedek Operasyon — yalnız gerçek yönetim rolleri.

    'Cover' tanımı (KRİTİK):
      RTS / Kaptan / BM kendi atandığı restoranda zaten sabit maaşıyla
      çalışıyor — bu normal iş, COVER DEĞİL. Cover yalnız:
        • Restoran Takım Şefi/Kaptan/BM → kendi restoranı DIŞINDA
          başka restoranlara destek olarak gittiği entry'ler
        • Joker (assigned_restaurant_id NULL) → her entry cover
          (Joker'in 'evi' yok)

    SQL: d.restaurant_id IS DISTINCT FROM p.assigned_restaurant_id
      · Joker (assigned NULL) için: NULL IS DISTINCT FROM <id> → TRUE → dahil
      · RTS Recep (assigned=Quick China) için:
          QC entry  → QC IS DISTINCT FROM QC → FALSE → dışlanır ✓
          Başka  → Other IS DISTINCT FROM QC → TRUE  → dahil ✓
    """
    # İki ayrı toplam:
    #   cover_* → kendi atandığı restoran DIŞINDAKİ günler (RTŞ/Kaptan için
    #             "ekstra destek" anlamı taşır)
    #   field_* → TÜM saha günleri (assigned dahil). BM/Joker bizim cebimizden
    #             sabit maaş alır; nerede çalışırsa çalışsın o gün restoran
    #             faturasına yansır → maaş geri kazanımı bunun üzerinden ölçülür.
    sql = """
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            COALESCE(p.monthly_fixed_cost, 0) AS salary,
            -- Kendi restoranı dışı (cover)
            COALESCE(SUM(d.worked_hours) FILTER (
                WHERE d.worked_hours > 0
                  AND d.restaurant_id IS DISTINCT FROM p.assigned_restaurant_id
            ), 0) AS cover_hours,
            COALESCE(SUM(d.package_count) FILTER (
                WHERE d.worked_hours > 0
                  AND d.restaurant_id IS DISTINCT FROM p.assigned_restaurant_id
            ), 0) AS cover_packages,
            COUNT(*) FILTER (
                WHERE d.worked_hours > 0
                  AND d.restaurant_id IS DISTINCT FROM p.assigned_restaurant_id
            ) AS cover_days,
            -- Tüm saha günleri (assigned dahil)
            COALESCE(SUM(d.worked_hours) FILTER (WHERE d.worked_hours > 0), 0) AS field_hours,
            COALESCE(SUM(d.package_count) FILTER (WHERE d.worked_hours > 0), 0) AS field_packages,
            COUNT(*) FILTER (WHERE d.worked_hours > 0) AS field_days
        FROM personnel p
        LEFT JOIN daily_entries d
            ON d.actual_personnel_id = p.id
           AND LEFT(d.entry_date::text, 7) = %s
        WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
          AND p.role IN ('Bölge Müdürü', 'Joker', 'Kaptan', 'Restoran Takım Şefi')
        GROUP BY p.id, p.full_name, p.person_code, p.role, p.monthly_fixed_cost
        ORDER BY salary DESC, field_packages DESC
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "person_code": r["person_code"],
            "role": r["role"],
            "salary": float(r["salary"] or 0),
            "cover_hours": float(r["cover_hours"] or 0),
            "cover_packages": int(r["cover_packages"] or 0),
            "cover_days": int(r["cover_days"] or 0),
            "field_hours": float(r["field_hours"] or 0),
            "field_packages": int(r["field_packages"] or 0),
            "field_days": int(r["field_days"] or 0),
        })
    return out


def next_person_code(role: str) -> str:
    """Role göre bir sonraki uygun person_code'u öner.

    - Kurye → CK-K??
    - Joker → CK-J??
    - Bölge Müdürü → CK-BM??
    - Kaptan → CK-KP??
    - Restoran Takım Şefi → CK-S??
    """
    prefix_map = {
        "Kurye": "CK-K",
        "Joker": "CK-J",
        "Bölge Müdürü": "CK-BM",
        "Kaptan": "CK-KP",
        "Restoran Takım Şefi": "CK-S",
    }
    prefix = prefix_map.get(role, "CK-X")

    sql = """
        SELECT person_code FROM personnel
        WHERE person_code LIKE %s
        ORDER BY person_code DESC
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"{prefix}%",))
            row = cur.fetchone()

    if not row or not row[0]:
        return f"{prefix}01"

    # Mevcut son koddan sayısal kısmı al
    existing = row[0]
    try:
        num_part = existing[len(prefix):]
        next_num = int(num_part) + 1
        return f"{prefix}{next_num:02d}"
    except (ValueError, IndexError):
        return f"{prefix}01"


def list_personnel_stats(period: str) -> list[dict]:
    """Personel listesi için aylık aggregate stats — paket / saat / çalışılan gün.

    /personel sayfasındaki kart bazlı 'Paket / Saat / Gün' alanları için
    kullanılır. Tek query ile tüm aktif personel için per-period
    toplamları döndürür (LEFT JOIN ile veri olmayanlar 0/0/0 görünür).

    Args:
        period: 'YYYY-MM' formatında ay
    """
    sql = """
        SELECT
            p.id,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COUNT(DISTINCT d.entry_date)
                FILTER (WHERE COALESCE(d.worked_hours, 0) > 0) AS working_days
        FROM personnel p
        LEFT JOIN daily_entries d
            ON d.actual_personnel_id = p.id
           AND LEFT(d.entry_date::text, 7) = %s
        GROUP BY p.id
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    return [
        {
            "personnel_id": int(r["id"]),
            "total_packages": int(r["total_packages"] or 0),
            "total_hours": float(r["total_hours"] or 0),
            "working_days": int(r["working_days"] or 0),
        }
        for r in rows
    ]
