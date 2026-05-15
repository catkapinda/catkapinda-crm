"""V2 → V3 belirli bir period için daily_entries (+gerekli personnel/restaurants) migration.

Kullanım (V3 backend container shell'inde):
    python scripts/migrate_v2_period.py --period 2026-04                    # dry-run
    python scripts/migrate_v2_period.py --period 2026-04 --apply            # gerçekten taşı
    python scripts/migrate_v2_period.py --period 2026-04 --apply --replace  # V3'teki Nisan'ı önce sil

Önkoşul env vars (V3 container'da olmalı):
    DATABASE_URL         → V3 PostgreSQL
    CK_V2_DATABASE_URL   → V2 PostgreSQL (geçici olarak V3 env'ine eklenmeli)

Akış (tek transaction):
    1. V2'den period'a ait daily_entries çek.
    2. Bu kayıtlardaki personnel_id ve restaurant_id setlerini topla.
    3. V2 restaurants/personnel'lardan bu ID'ler için ayrıntıları al.
    4. V3 restaurants ile (brand, branch) eşle. Eksik olanları V3'e ekle (sadece
       o restorana ait personnel'in alanı).
    5. V3 personnel ile person_code eşle. Eksik olanları V3'e ekle (V2'deki
       assigned_restaurant_id mapping'e göre V3'e map'lenmiş şekilde).
    6. ID mapping ile daily_entries'i V3'e INSERT et.
    7. Başarı → commit, hata → rollback.

Idempotency:
    - Restaurants/personnel için brand+branch / person_code ile var/yok kontrolü.
    - daily_entries için --replace bayrağı: önce DELETE WHERE period, sonra INSERT.

Output: özet log.
"""
from __future__ import annotations

import argparse
import os
import sys

import psycopg
from psycopg.rows import dict_row


# ─── Yardımcılar ─────────────────────────────────────────────────────

def get_table_columns(conn: psycopg.Connection, table_name: str) -> list[str]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        return [r["column_name"] for r in cur.fetchall()]


def fetch_period_entries(v2: psycopg.Connection, period: str) -> list[dict]:
    with v2.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT *
            FROM daily_entries
            WHERE LEFT(entry_date::text, 7) = %s
            ORDER BY entry_date, id
            """,
            (period,),
        )
        return [dict(r) for r in cur.fetchall()]


def fetch_by_ids(conn: psycopg.Connection, table: str, ids: set[int]) -> dict[int, dict]:
    if not ids:
        return {}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {table} WHERE id = ANY(%s)", (list(ids),))
        return {r["id"]: dict(r) for r in cur.fetchall()}


def fetch_v3_restaurants_by_key(v3: psycopg.Connection) -> dict[tuple, int]:
    with v3.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, brand, branch FROM restaurants")
        return {(r["brand"], r["branch"]): r["id"] for r in cur.fetchall()}


def fetch_v3_personnel_by_code(v3: psycopg.Connection) -> dict[str, int]:
    with v3.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, person_code FROM personnel WHERE person_code IS NOT NULL"
        )
        return {r["person_code"]: r["id"] for r in cur.fetchall()}


def _filter_payload(row: dict, allowed_cols: list[str]) -> dict:
    return {k: v for k, v in row.items() if k in allowed_cols and k != "id"}


def insert_row(
    conn: psycopg.Connection,
    table: str,
    payload: dict,
) -> int:
    if not payload:
        raise RuntimeError(f"insert_row: payload boş ({table})")
    cols = list(payload.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    cols_csv = ", ".join(cols)
    sql = f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders}) RETURNING id"
    with conn.cursor() as cur:
        cur.execute(sql, list(payload.values()))
        new_id = cur.fetchone()[0]
    return new_id


# ─── Ana akış ────────────────────────────────────────────────────────

def run(period: str, apply: bool, replace: bool) -> int:
    v2_url = os.environ.get("CK_V2_DATABASE_URL")
    v3_url = os.environ.get("DATABASE_URL")
    if not v2_url:
        print("FATAL: CK_V2_DATABASE_URL env var gerekli (V3 container'a geçici ekle).")
        return 1
    if not v3_url:
        print("FATAL: DATABASE_URL env var gerekli.")
        return 1

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n=== V2 → V3 migration | period={period} | mode={mode} ===\n")

    with psycopg.connect(v2_url) as v2, psycopg.connect(v3_url) as v3:
        v2.autocommit = False
        v3.autocommit = False

        try:
            # --- Schema bilgisi
            v3_rest_cols = get_table_columns(v3, "restaurants")
            v3_pers_cols = get_table_columns(v3, "personnel")
            v3_entry_cols = get_table_columns(v3, "daily_entries")
            v2_entry_cols = get_table_columns(v2, "daily_entries")
            entry_common = [c for c in v3_entry_cols if c in v2_entry_cols and c != "id"]
            print(f"daily_entries ortak kolonlar: {len(entry_common)} adet")

            # --- V2 veri
            v2_entries = fetch_period_entries(v2, period)
            print(f"V2 daily_entries ({period}): {len(v2_entries)} kayıt")
            if not v2_entries:
                print("V2'de bu period için kayıt yok. Çıkış.")
                return 0

            rest_ids_used = {e["restaurant_id"] for e in v2_entries if e.get("restaurant_id")}
            pers_ids_used = {e["actual_personnel_id"] for e in v2_entries if e.get("actual_personnel_id")}
            print(f"Kullanılan restoran sayısı: {len(rest_ids_used)}")
            print(f"Kullanılan kurye sayısı: {len(pers_ids_used)}")

            v2_rests = fetch_by_ids(v2, "restaurants", rest_ids_used)
            v2_personnel = fetch_by_ids(v2, "personnel", pers_ids_used)

            # --- V3 mevcut
            v3_rest_by_key = fetch_v3_restaurants_by_key(v3)
            v3_pers_by_code = fetch_v3_personnel_by_code(v3)
            print(f"V3 restoran sayısı: {len(v3_rest_by_key)}")
            print(f"V3 kurye sayısı (person_code'lu): {len(v3_pers_by_code)}")

            # --- ID mapping + eksikleri ekle
            rest_id_map: dict[int, int] = {}
            pers_id_map: dict[int, int] = {}
            added_rests, added_pers = 0, 0

            print("\n--- Restaurants ---")
            for v2_id, v2_r in v2_rests.items():
                key = (v2_r.get("brand"), v2_r.get("branch"))
                if key in v3_rest_by_key:
                    rest_id_map[v2_id] = v3_rest_by_key[key]
                else:
                    payload = _filter_payload(v2_r, v3_rest_cols)
                    if apply:
                        new_id = insert_row(v3, "restaurants", payload)
                        v3_rest_by_key[key] = new_id
                        rest_id_map[v2_id] = new_id
                    else:
                        rest_id_map[v2_id] = -1
                    added_rests += 1
                    print(f"  + Yeni restoran: {key}")

            print("\n--- Personnel ---")
            for v2_id, v2_p in v2_personnel.items():
                code = v2_p.get("person_code")
                if code and code in v3_pers_by_code:
                    pers_id_map[v2_id] = v3_pers_by_code[code]
                else:
                    payload = _filter_payload(v2_p, v3_pers_cols)
                    # assigned_restaurant_id'yi V3 ID'ye çevir
                    if "assigned_restaurant_id" in payload:
                        v2_rest = payload["assigned_restaurant_id"]
                        if v2_rest is not None:
                            payload["assigned_restaurant_id"] = rest_id_map.get(v2_rest)
                    if apply:
                        new_id = insert_row(v3, "personnel", payload)
                        if code:
                            v3_pers_by_code[code] = new_id
                        pers_id_map[v2_id] = new_id
                    else:
                        pers_id_map[v2_id] = -1
                    added_pers += 1
                    print(f"  + Yeni kurye: {v2_p.get('full_name')} ({code})")

            # --- Replace mode: V3'te bu period'u sil
            if apply and replace:
                with v3.cursor() as cur:
                    cur.execute(
                        "DELETE FROM daily_entries WHERE LEFT(entry_date::text, 7) = %s",
                        (period,),
                    )
                    print(f"\nReplace: V3 daily_entries silindi ({cur.rowcount} kayıt)")

            # --- daily_entries INSERT
            print("\n--- daily_entries ---")
            cols_csv = ", ".join(entry_common)
            placeholders = ", ".join(["%s"] * len(entry_common))
            sql = f"INSERT INTO daily_entries ({cols_csv}) VALUES ({placeholders})"

            inserted = 0
            skipped = 0
            for e in v2_entries:
                v2_rest = e.get("restaurant_id")
                v2_pers = e.get("actual_personnel_id")
                new_rest = rest_id_map.get(v2_rest) if v2_rest else None
                new_pers = pers_id_map.get(v2_pers) if v2_pers else None
                # Eğer kaynak FK varsa ama V3 mapping yapılamadıysa skip
                if v2_rest and not new_rest:
                    skipped += 1
                    continue
                if v2_pers and not new_pers:
                    skipped += 1
                    continue

                row = dict(e)
                row["restaurant_id"] = new_rest
                row["actual_personnel_id"] = new_pers
                vals = [row.get(c) for c in entry_common]

                if apply:
                    with v3.cursor() as cur:
                        cur.execute(sql, vals)
                inserted += 1

            # --- Commit / rollback
            if apply:
                v3.commit()
                print(
                    f"\n✅ APPLIED: {inserted} entry yazıldı, {skipped} atlandı, "
                    f"{added_rests} restoran, {added_pers} kurye eklendi."
                )
            else:
                v3.rollback()
                print(
                    f"\n[DRY-RUN] Eklenecek: {inserted} entry, {skipped} atlanacak, "
                    f"{added_rests} restoran, {added_pers} kurye.\n"
                    f"(Hiçbir veri yazılmadı. Onaylarsan --apply ile çalıştır.)"
                )
            return 0

        except Exception as e:
            v3.rollback()
            print(f"\n❌ HATA: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="V2 → V3 period migration")
    parser.add_argument("--period", required=True, help="YYYY-MM (örn. 2026-04)")
    parser.add_argument(
        "--apply", action="store_true",
        help="Gerçekten yaz (default dry-run)",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="V3'teki bu period'a ait daily_entries'i önce sil (idempotent)",
    )
    args = parser.parse_args()
    return run(period=args.period, apply=args.apply, replace=args.replace)


if __name__ == "__main__":
    sys.exit(main())
