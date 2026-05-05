"""Puantaj (daily_entries) servisi.

`entry_date` text tipindedir (YYYY-MM-DD). Bu yüzden ay filtresinde
`LEFT(entry_date::text, 7) = '2026-03'` cast'i kullanılır.
"""
from psycopg.rows import dict_row

from app.core.database import get_connection


def list_entries(
    period: str,
    restaurant_id: int | None = None,
    personnel_id: int | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Bir ay için puantaj kayıtları (restoran + personel adı JOIN'lu)."""
    sql = """
        SELECT
            d.id,
            d.entry_date,
            d.restaurant_id,
            r.brand AS restaurant_brand,
            r.branch AS restaurant_branch,
            r.pricing_model,
            d.actual_personnel_id,
            d.planned_personnel_id,
            p.full_name AS personnel_name,
            p.person_code,
            p.role AS personnel_role,
            d.worked_hours,
            d.package_count,
            d.coverage_type,
            d.absence_reason,
            d.status,
            d.notes,
            d.monthly_invoice_amount
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        WHERE LEFT(d.entry_date::text, 7) = %s
    """
    params: list = [period]

    if restaurant_id is not None:
        sql += " AND d.restaurant_id = %s"
        params.append(restaurant_id)
    if personnel_id is not None:
        sql += " AND d.actual_personnel_id = %s"
        params.append(personnel_id)

    sql += " ORDER BY d.entry_date DESC, r.brand, p.full_name LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


def summary_by_restaurant(period: str) -> list[dict]:
    """Restoran bazında aylık özet — kart görünümü için."""
    sql = """
        SELECT
            r.id AS restaurant_id,
            r.brand,
            r.branch,
            r.pricing_model,
            r.target_headcount,
            COUNT(d.id) AS entries,
            COUNT(DISTINCT d.actual_personnel_id) AS unique_personnel,
            COALESCE(SUM(d.worked_hours), 0) AS total_hours,
            COALESCE(SUM(d.package_count), 0) AS total_packages,
            COUNT(*) FILTER (
                WHERE d.absence_reason IS NOT NULL AND d.absence_reason <> ''
            ) AS absences
        FROM daily_entries d
        LEFT JOIN restaurants r ON r.id = d.restaurant_id
        WHERE LEFT(d.entry_date::text, 7) = %s
        GROUP BY r.id, r.brand, r.branch, r.pricing_model, r.target_headcount
        ORDER BY r.brand NULLS LAST, r.branch NULLS LAST
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (period,))
            rows = cur.fetchall()
    # numerik tipleri normalize et (Decimal → float)
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "restaurant_id": r["restaurant_id"],
                "brand": r["brand"],
                "branch": r["branch"],
                "pricing_model": r["pricing_model"],
                "target_headcount": r["target_headcount"],
                "entries": int(r["entries"] or 0),
                "unique_personnel": int(r["unique_personnel"] or 0),
                "total_hours": float(r["total_hours"] or 0),
                "total_packages": int(r["total_packages"] or 0),
                "absences": int(r["absences"] or 0),
            }
        )
    return out


def upsert_cell(
    personnel_id: int,
    entry_date: str,
    cell_type: str,
    worked_hours: float = 0,
    package_count: int = 0,
    coverage_type: str | None = None,
    notes: str | None = None,
    restaurant_id: int | None = None,
) -> dict:
    """Bir günün puantajını güncelle / oluştur.

    cell_type: 'normal' | 'izin' | 'gelmedi' | 'raporlu' | 'ihbarsiz' | 'empty'
    - normal → status='Normal', absence_reason=None
    - izin → status='İzin', absence_reason='İzin', hours=0, packages=0
    - gelmedi → status='Gelmedi', absence_reason='Gelmedi', hours=0
    - raporlu → status='Raporlu', absence_reason='Raporlu', hours=0
    - ihbarsiz → status='İhbarsız', absence_reason='İhbarsız', hours=0
    - empty → kayıt sil
    """
    type_map = {
        "normal": ("Normal", None),
        "izin": ("İzin", "İzin"),
        "gelmedi": ("Gelmedi", "Gelmedi"),
        "raporlu": ("Raporlu", "Raporlu"),
        "ihbarsiz": ("İhbarsız", "İhbarsız"),
    }

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Önce mevcut kayıt var mı bak
            cur.execute(
                """
                SELECT id, restaurant_id FROM daily_entries
                WHERE actual_personnel_id = %s
                  AND entry_date::text = %s
                LIMIT 1
                """,
                (personnel_id, entry_date),
            )
            existing = cur.fetchone()

            if cell_type == "empty":
                # Sil
                if existing:
                    cur.execute(
                        "DELETE FROM daily_entries WHERE id = %s",
                        (existing["id"],),
                    )
                conn.commit()
                return {"action": "deleted", "id": existing["id"] if existing else None}

            status, absence = type_map.get(cell_type, ("Normal", None))

            # Sadece normal'da saat/paket geçerli
            if cell_type != "normal":
                worked_hours = 0
                package_count = 0

            # Restaurant_id yoksa: kuryenin atandığı restoran (Joker hariç)
            if restaurant_id is None:
                cur.execute(
                    "SELECT assigned_restaurant_id FROM personnel WHERE id = %s",
                    (personnel_id,),
                )
                p = cur.fetchone()
                if p and p.get("assigned_restaurant_id"):
                    restaurant_id = p["assigned_restaurant_id"]
                elif existing and existing.get("restaurant_id"):
                    restaurant_id = existing["restaurant_id"]
                else:
                    raise ValueError(
                        "Restoran belirlenemedi (kurye atanmamış olabilir)",
                    )

            if existing:
                cur.execute(
                    """
                    UPDATE daily_entries
                    SET worked_hours = %s,
                        package_count = %s,
                        status = %s,
                        absence_reason = %s,
                        coverage_type = %s,
                        notes = %s,
                        restaurant_id = COALESCE(%s, restaurant_id)
                    WHERE id = %s
                    RETURNING id
                    """,
                    (
                        worked_hours, package_count, status, absence,
                        coverage_type, notes, restaurant_id,
                        existing["id"],
                    ),
                )
                action = "updated"
            else:
                cur.execute(
                    """
                    INSERT INTO daily_entries
                        (entry_date, restaurant_id, actual_personnel_id,
                         planned_personnel_id, worked_hours, package_count,
                         status, absence_reason, coverage_type, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        entry_date, restaurant_id, personnel_id, personnel_id,
                        worked_hours, package_count,
                        status, absence, coverage_type, notes,
                    ),
                )
                action = "created"

            row = cur.fetchone()
            conn.commit()

    return {"action": action, "id": row["id"] if row else None}


def bulk_fill(
    period: str,
    pattern: str,
    hours: float = 9,
    package_count: int = 0,
    personnel_ids: list[int] | None = None,
    restaurant_id: int | None = None,
) -> dict:
    """Hızlı doldur (toplu giriş).

    pattern:
      - 'weekdays' → hafta içi tüm günleri dolduruir (boş hücreler)
      - 'all' → ayın tüm günlerini doldurur (boş hücreler)
      - 'weekend_off' → hafta sonu boş bırakır, hafta içi 9 saat
      - 'copy_previous' → bir önceki ayın puantajını kopyalar
    """
    from datetime import date as date_cls
    from calendar import monthrange

    y, m = period.split("-")
    yi, mi = int(y), int(m)
    last_day = monthrange(yi, mi)[1]

    inserted = 0
    skipped = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Personel listesi
            if personnel_ids:
                cur.execute(
                    "SELECT id, assigned_restaurant_id FROM personnel "
                    "WHERE id = ANY(%s) AND COALESCE(status, 'Aktif') = 'Aktif'",
                    (personnel_ids,),
                )
            else:
                cur.execute(
                    "SELECT id, assigned_restaurant_id FROM personnel "
                    "WHERE COALESCE(status, 'Aktif') = 'Aktif' "
                    "AND assigned_restaurant_id IS NOT NULL",
                )
            personnel = cur.fetchall()

            if pattern == "copy_previous":
                # Önceki ayı kopyala
                prev_y, prev_m = (yi, mi - 1) if mi > 1 else (yi - 1, 12)
                prev_period = f"{prev_y:04d}-{prev_m:02d}"
                cur.execute(
                    """
                    SELECT actual_personnel_id, restaurant_id, entry_date,
                           worked_hours, package_count, coverage_type, status
                    FROM daily_entries
                    WHERE LEFT(entry_date::text, 7) = %s
                      AND COALESCE(worked_hours, 0) > 0
                    """,
                    (prev_period,),
                )
                prev_rows = cur.fetchall()
                for r in prev_rows:
                    pid, rid, ed, wh, pc, ct, st = r
                    # Ay/gün shift
                    if not ed:
                        continue
                    eds = str(ed)
                    try:
                        d = int(eds[8:10])
                    except ValueError:
                        continue
                    if d > last_day:
                        continue  # Mart 31, Şubat 28-29 farkı için
                    new_date = f"{yi:04d}-{mi:02d}-{d:02d}"
                    # Var mı kontrol
                    cur.execute(
                        "SELECT 1 FROM daily_entries "
                        "WHERE actual_personnel_id = %s AND entry_date::text = %s",
                        (pid, new_date),
                    )
                    if cur.fetchone():
                        skipped += 1
                        continue
                    cur.execute(
                        """
                        INSERT INTO daily_entries
                            (entry_date, restaurant_id, actual_personnel_id,
                             planned_personnel_id, worked_hours, package_count,
                             status, coverage_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (new_date, rid, pid, pid, wh, pc, st or "Normal", ct),
                    )
                    inserted += 1
            else:
                # weekdays / all / weekend_off pattern
                for p in personnel:
                    pid, p_rid = p
                    target_rid = restaurant_id or p_rid
                    if not target_rid:
                        continue
                    for day in range(1, last_day + 1):
                        dt = date_cls(yi, mi, day)
                        is_weekend = dt.weekday() >= 5  # Cts/Paz
                        if pattern == "weekdays" and is_weekend:
                            continue
                        if pattern == "weekend_off" and is_weekend:
                            continue
                        # 'all' ise her gün doldur

                        date_str = dt.isoformat()
                        # Var mı?
                        cur.execute(
                            "SELECT 1 FROM daily_entries "
                            "WHERE actual_personnel_id = %s "
                            "  AND entry_date::text = %s",
                            (pid, date_str),
                        )
                        if cur.fetchone():
                            skipped += 1
                            continue

                        cur.execute(
                            """
                            INSERT INTO daily_entries
                                (entry_date, restaurant_id, actual_personnel_id,
                                 planned_personnel_id, worked_hours, package_count,
                                 status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'Normal')
                            """,
                            (
                                date_str, target_rid, pid, pid,
                                hours, package_count,
                            ),
                        )
                        inserted += 1
            conn.commit()

    return {"inserted": inserted, "skipped": skipped, "pattern": pattern}


def daily_matrix(period: str) -> dict:
    """Personel × gün matrisi — puantaj grid sayfası için.

    Her personelin her günü için hücre verisi:
        type: normal | izin | gelmedi | raporlu | ihbarsiz | empty
        hours, packages, is_joker (destek)

    Sıralama: ana atanmış kuryeler restoran adına göre, sonra Joker/BM.
    """
    # 1. Aktif personel + O AYKI GERÇEK ÇALIŞTIĞI restoranı al
    # (kuryenin assigned_restaurant_id'si güncel olmayabilir; örn Doyuyo
    # Mart'ta kapandı ama kuryeler hâlâ orada görünüyor — gerçekte rest_id=9'da
    # çalışıyorlar). En çok puantaj kaydı olan restoranı tercih et.
    personnel_sql = """
        WITH active_rest AS (
            SELECT pid, rid FROM (
                SELECT
                    d.actual_personnel_id AS pid,
                    d.restaurant_id AS rid,
                    COUNT(*) AS cnt,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.actual_personnel_id
                        ORDER BY COUNT(*) DESC, d.restaurant_id
                    ) AS rn
                FROM daily_entries d
                WHERE LEFT(d.entry_date::text, 7) = %s
                  AND COALESCE(d.worked_hours, 0) > 0
                GROUP BY d.actual_personnel_id, d.restaurant_id
            ) t
            WHERE rn = 1
        )
        SELECT
            p.id, p.full_name, p.person_code, p.role,
            p.assigned_restaurant_id,
            COALESCE(r_active.brand, r_assigned.brand) AS rest_brand,
            COALESCE(r_active.branch, r_assigned.branch) AS rest_branch
        FROM personnel p
        LEFT JOIN active_rest a ON a.pid = p.id
        LEFT JOIN restaurants r_active ON r_active.id = a.rid
        LEFT JOIN restaurants r_assigned ON r_assigned.id = p.assigned_restaurant_id
        WHERE
            -- 1) Aktif personel
            COALESCE(p.status, 'Aktif') = 'Aktif'
            -- 2) Atanmamış (Joker) veya AKTİF restorana atanmış
            -- (Pasif restoranın kuryeleri burada elenir — örn ay içinde kapanan restoran)
            AND (
                p.assigned_restaurant_id IS NULL
                OR EXISTS (
                    SELECT 1 FROM restaurants r3
                    WHERE r3.id = p.assigned_restaurant_id
                      AND COALESCE(r3.active, 1) = 1
                )
            )
        ORDER BY
            COALESCE(r_active.brand, r_assigned.brand) NULLS LAST,
            COALESCE(r_active.branch, r_assigned.branch) NULLS LAST,
            p.role, p.person_code
    """

    # 2. O ayın tüm puantaj kayıtları
    entries_sql = """
        SELECT
            d.actual_personnel_id,
            d.entry_date,
            d.worked_hours,
            d.package_count,
            d.coverage_type,
            d.absence_reason,
            d.status,
            d.restaurant_id,
            p.assigned_restaurant_id
        FROM daily_entries d
        LEFT JOIN personnel p ON p.id = d.actual_personnel_id
        WHERE LEFT(d.entry_date::text, 7) = %s
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # personnel_sql tek parametre: CTE içinde period (active_rest)
            cur.execute(personnel_sql, (period,))
            personnel = cur.fetchall()

            cur.execute(entries_sql, (period,))
            entries = cur.fetchall()

            # Toplam summary'yi direkt DB'den çek (Dashboard ile aynı toplam)
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_entries,
                    COALESCE(SUM(worked_hours), 0) AS total_hours,
                    COALESCE(SUM(package_count), 0) AS total_packages,
                    COUNT(*) FILTER (WHERE COALESCE(worked_hours, 0) > 0) AS worked_days
                FROM daily_entries
                WHERE LEFT(entry_date::text, 7) = %s
                """,
                (period,),
            )
            db_totals = cur.fetchone() or {}

    # 3. Personel + restoran + gün → cell map
    # Aynı kuryenin farklı restoranlardaki kayıtları ayrı tutulur ki ana ve destek
    # satırları ayrı gösterilebilsin.
    by_pid_rid_day: dict[tuple[int, int | None, int], dict] = {}
    pid_to_assigned_rid: dict[int, int | None] = {}
    pid_destek_rids: dict[int, set[int]] = {}

    for e in entries:
        pid = e["actual_personnel_id"]
        if pid is None:
            continue
        date_str = str(e["entry_date"])
        if not date_str or len(date_str) < 10:
            continue
        try:
            day = int(date_str[8:10])
        except ValueError:
            continue

        rid = e.get("restaurant_id")
        assigned_rid = e.get("assigned_restaurant_id")
        if pid not in pid_to_assigned_rid:
            pid_to_assigned_rid[pid] = assigned_rid

        worked_hours = float(e.get("worked_hours") or 0)
        worked = worked_hours > 0
        coverage = (e.get("coverage_type") or "").strip()
        status = (e.get("status") or "").strip()
        absence = (e.get("absence_reason") or "").strip()

        if worked:
            cell_type = "normal"
        elif status == "İzin" or absence == "İzin":
            cell_type = "izin"
        elif "rapor" in absence.lower() or "rapor" in status.lower():
            cell_type = "raporlu"
        elif "ihbar" in absence.lower():
            cell_type = "ihbarsiz"
        elif absence:
            cell_type = "gelmedi"
        else:
            cell_type = "empty"

        # Destek mi: ana atamadan farklı restoran ya da explicit Destek coverage
        is_support = (
            coverage == "Destek"
            or (
                assigned_rid is not None
                and rid is not None
                and assigned_rid != rid
            )
        )
        if is_support and rid is not None:
            pid_destek_rids.setdefault(pid, set()).add(rid)

        key = (pid, rid, day)
        existing = by_pid_rid_day.get(key)
        # Mevcut normal kaydını koru
        if existing and existing["type"] == "normal" and cell_type != "normal":
            continue

        by_pid_rid_day[key] = {
            "type": cell_type,
            "hours": worked_hours,
            "packages": int(e.get("package_count") or 0),
            "is_support": is_support,
            "restaurant_id": rid,
        }

    # Restoran info map (destek satırlarında brand göstermek için)
    rest_info: dict[int, dict] = {}
    try:
        with get_connection() as conn2:
            with conn2.cursor(row_factory=dict_row) as cur2:
                cur2.execute("SELECT id, brand, branch, pricing_model FROM restaurants")
                for row in cur2.fetchall():
                    rest_info[int(row["id"])] = {
                        "brand": row.get("brand"),
                        "branch": row.get("branch"),
                        "pricing_model": row.get("pricing_model"),
                    }
    except Exception:
        pass

    # 4. Her personel için: ANA satır + destek satır(lar)ı
    def _build_cells_for(
        pid: int, rid: int | None,
    ) -> tuple[list[dict], float, int, int]:
        cells: list[dict] = []
        total_hours = 0.0
        total_pkts = 0
        worked_days = 0
        for day in range(1, 32):
            cell = by_pid_rid_day.get((pid, rid, day))
            if cell:
                cells.append(cell)
                if cell["type"] == "normal":
                    total_hours += cell["hours"]
                    total_pkts += cell["packages"]
                    worked_days += 1
            else:
                cells.append({
                    "type": "empty", "hours": 0, "packages": 0,
                    "is_support": False, "restaurant_id": rid,
                })
        return cells, total_hours, total_pkts, worked_days

    rows: list[dict] = []
    for p in personnel:
        pid = p["id"]
        # Bu kuryenin kullandığı tüm restoran id'leri (ana + destekler)
        rids_used: set[int | None] = set()
        for (k_pid, k_rid, _), _ in by_pid_rid_day.items():
            if k_pid == pid:
                rids_used.add(k_rid)

        # Ana satırın restoran id'sini belirle:
        # 1) Personnel.assigned_restaurant_id (eğer kullanılmışsa)
        # 2) Yoksa en çok kayıt olan restoran (zaten personnel_sql'in bulduğu)
        assigned_rid = pid_to_assigned_rid.get(pid)
        ana_rid: int | None = None
        if assigned_rid is not None and assigned_rid in rids_used:
            ana_rid = assigned_rid
        else:
            # En çok kullanılanı seç (entry sayısı)
            count_by_rid: dict[int | None, int] = {}
            for (k_pid, k_rid, _), c in by_pid_rid_day.items():
                if k_pid == pid and c["type"] != "empty":
                    count_by_rid[k_rid] = count_by_rid.get(k_rid, 0) + 1
            if count_by_rid:
                ana_rid = max(count_by_rid.items(), key=lambda x: x[1])[0]
            elif rids_used:
                ana_rid = next(iter(rids_used))

        # Ana satır
        ana_cells, ana_hours, ana_pkts, ana_days = _build_cells_for(pid, ana_rid)
        rows.append({
            "id": pid,
            "row_key": f"{pid}-main",
            "full_name": p["full_name"],
            "person_code": p["person_code"],
            "role": p["role"],
            "rest_brand": p["rest_brand"],
            "rest_branch": p["rest_branch"],
            "rest_id": ana_rid,
            "is_support_row": False,
            "cells": ana_cells,
            "total_hours": round(ana_hours, 1),
            "total_packages": ana_pkts,
            "worked_days": ana_days,
            "joker_days": 0,  # ana satırda destek yok
        })

        # Destek satırları (her destek restoranı için ayrı)
        destek_rids = pid_destek_rids.get(pid, set())
        # ana_rid destek setinden çıkar (eğer ana atama yoksa ve en çok destek varsa karışmasın)
        destek_rids = destek_rids - {ana_rid}
        for drid in sorted(destek_rids, key=lambda x: (rest_info.get(x, {}).get("brand") or "", x)):
            d_cells, d_hours, d_pkts, d_days = _build_cells_for(pid, drid)
            if d_days == 0:
                continue
            r_meta = rest_info.get(drid, {})
            rows.append({
                "id": pid,
                "row_key": f"{pid}-d-{drid}",
                "full_name": p["full_name"],
                "person_code": p["person_code"],
                "role": p["role"],
                "rest_brand": r_meta.get("brand"),
                "rest_branch": r_meta.get("branch"),
                "rest_id": drid,
                "is_support_row": True,
                "cells": d_cells,
                "total_hours": round(d_hours, 1),
                "total_packages": d_pkts,
                "worked_days": d_days,
                "joker_days": d_days,  # destek satırının tüm günleri destek
            })

    # 5. Aylık özet sayılar
    cell_counts: dict[str, int] = {}
    for cell in by_pid_rid_day.values():
        cell_counts[cell["type"]] = cell_counts.get(cell["type"], 0) + 1

    return {
        "period": period,
        "rows": rows,
        "summary": {
            # DB'den direkt — dashboard ile tutarlı (null personel kayıtları dahil)
            "total_hours": round(float(db_totals.get("total_hours") or 0), 1),
            "total_packages": int(db_totals.get("total_packages") or 0),
            "worked_days": int(db_totals.get("worked_days") or 0),
            "joker_days": sum(r["joker_days"] for r in rows),
            "cell_counts": cell_counts,
            # Tekil kurye sayısı (destek satırı duplicate, sadece personel)
            "personnel_count": len({r["id"] for r in rows}),
            "row_count": len(rows),
        },
    }


def available_periods() -> list[str]:
    """Veride mevcut olan tüm aylar (YYYY-MM) — yeni → eski sıralı."""
    sql = """
        SELECT DISTINCT LEFT(entry_date::text, 7) AS period
        FROM daily_entries
        WHERE entry_date IS NOT NULL AND entry_date::text <> ''
        ORDER BY period DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [r[0] for r in rows if r[0]]
