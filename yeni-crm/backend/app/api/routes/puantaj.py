"""Puantaj endpoint'leri."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.puantaj import (
    available_periods,
    bulk_fill,
    daily_matrix,
    list_entries,
    summary_by_restaurant,
    upsert_cell,
)
from app.services import puantaj_approvals as approvals
from app.services.puantaj_template import generate_puantaj_template
from app.services.puantaj_template_import import import_puantaj_template

router = APIRouter()


@router.get("/template")
async def template(
    period: str = "2026-03",
    restaurant_id: int | None = None,
):
    """Toplu puantaj Excel şablonu — operasyon ekibi için.

    Her kurye için iki satır (Saat + Paket) × günler matrisi.
    restaurant_id verilmezse tüm aktif personel dahil.
    """
    try:
        xlsx_bytes = generate_puantaj_template(
            period=period, restaurant_id=restaurant_id,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Şablon üretilemedi: {e}"
        ) from e

    filename = f"puantaj-sablon-{period}.xlsx"
    if restaurant_id:
        filename = f"puantaj-sablon-{period}-rest{restaurant_id}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


class CellPayload(BaseModel):
    personnel_id: int
    entry_date: str  # YYYY-MM-DD
    cell_type: str  # normal | izin | gelmedi | raporlu | ihbarsiz | empty
    worked_hours: float = 0
    package_count: int = 0
    coverage_type: str | None = None
    restaurant_id: int | None = None
    notes: str | None = None
    covers_personnel_id: int | None = None  # gelmediğinde yerine giren


@router.get("/periods")
async def periods() -> list[str]:
    """Veride mevcut tüm aylar (YYYY-MM) — yeni → eski."""
    return available_periods()


@router.get("/entries")
async def entries(
    period: str,
    restaurant_id: int | None = None,
    personnel_id: int | None = None,
    limit: int = 5000,
) -> list[dict]:
    """Belirli ay için puantaj girişleri."""
    return list_entries(
        period=period,
        restaurant_id=restaurant_id,
        personnel_id=personnel_id,
        limit=limit,
    )


@router.get("/summary-by-restaurant")
async def summary_restaurant(period: str) -> list[dict]:
    """Restoran bazında aylık özet."""
    return summary_by_restaurant(period=period)


@router.get("/matrix")
async def matrix(period: str = "2026-03") -> dict:
    """Personel × gün matrisi — grid sayfası için."""
    return daily_matrix(period=period)


class BulkFillPayload(BaseModel):
    period: str
    pattern: str  # weekdays | all | weekend_off | copy_previous
    hours: float = 9
    package_count: int = 0
    personnel_ids: list[int] | None = None
    restaurant_id: int | None = None


@router.post("/bulk-fill")
async def post_bulk_fill(payload: BulkFillPayload) -> dict:
    """Hızlı doldur (toplu giriş) — boş hücreleri varsayılan değerlerle doldurur."""
    return bulk_fill(
        period=payload.period,
        pattern=payload.pattern,
        hours=payload.hours,
        package_count=payload.package_count,
        personnel_ids=payload.personnel_ids,
        restaurant_id=payload.restaurant_id,
    )


# ─────────────────────────────────────────────────────────
# Onay endpoint'leri (operasyon → admin akışı)
# ─────────────────────────────────────────────────────────


class ApprovalSubmitPayload(BaseModel):
    restaurant_id: int
    period: str
    submitted_by: str | None = None


class ApprovalDecidePayload(BaseModel):
    status: str  # approved | rejected
    decided_by: str | None = None
    decision_notes: str | None = None


@router.get("/approvals")
async def get_approvals(
    status: str | None = None,
    period: str | None = None,
) -> list[dict]:
    """Onay listesi. Default: tümü, en yeni başta. status='pending' ile filtre."""
    return approvals.list_approvals(status=status, period=period)


@router.get("/approvals/summary")
async def get_approvals_summary(period: str) -> dict:
    """O ay için pending/approved/rejected sayıları."""
    return approvals.get_summary_by_period(period=period)


@router.get("/approvals/restaurant/{restaurant_id}")
async def get_approval_for_restaurant(
    restaurant_id: int, period: str,
) -> dict:
    """Belirli restoran+ay için onay durumu (yoksa boş dict)."""
    res = approvals.get_for_restaurant(restaurant_id, period)
    return res or {}


@router.post("/approvals/submit")
async def submit_approval(payload: ApprovalSubmitPayload) -> dict:
    """Restoranın aylık puantajını onaya gönder."""
    try:
        return approvals.submit_for_approval(
            restaurant_id=payload.restaurant_id,
            period=payload.period,
            submitted_by=payload.submitted_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: int, payload: ApprovalDecidePayload) -> dict:
    """Admin onay/red — status='approved' veya 'rejected'."""
    try:
        result = approvals.decide(
            approval_id=approval_id,
            status=payload.status,
            decided_by=payload.decided_by,
            decision_notes=payload.decision_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail="Onay kaydı bulunamadı")
    return result


@router.patch("/cell")
async def patch_cell(payload: CellPayload) -> dict:
    """Bir günü güncelle / oluştur (UPSERT)."""
    try:
        return upsert_cell(
            personnel_id=payload.personnel_id,
            entry_date=payload.entry_date,
            cell_type=payload.cell_type,
            worked_hours=payload.worked_hours,
            package_count=payload.package_count,
            coverage_type=payload.coverage_type,
            notes=payload.notes,
            restaurant_id=payload.restaurant_id,
            covers_personnel_id=payload.covers_personnel_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/template/import")
async def import_template(
    file: UploadFile = File(...),
    period: str = "2026-03",
) -> dict:
    """Doldurulmuş Excel şablonunu yükle ve daily_entries'e işle.

    Sheet'ler:
      - 'Puantaj': her kurye 3 satır (Saat / Paket / Durum)
        Durum kodları: G=Gelmedi, R=Raporlu, Z=İzin, X=İhbarsız, D=Destek
      - 'Destek': tarih + kurye + restoran + saat + paket
    """
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {e}") from e
    try:
        return import_puantaj_template(file_bytes=file_bytes, period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"İçe aktarma hatası: {e}"
        ) from e


@router.get("/replacement-candidates")
async def replacement_candidates(restaurant_id: int) -> dict:
    """Bir restoran için yerine giren olabilecek personel listesi.

    Gruplar:
      - same_restaurant: O restorana atanmış aktif kuryeler
      - other_restaurant_couriers: Diğer restoranların kuryeleri (destek olarak gelebilir)
      - jokers: Tüm aktif Joker'ler
      - management: BM / Kaptan / RTŞ
    Frontend dropdown'da bu grupları gösterir.
    """
    from app.core.database import get_connection
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    p.id, p.person_code, p.full_name, p.role,
                    p.assigned_restaurant_id,
                    r.brand AS rest_brand, r.branch AS rest_branch
                FROM personnel p
                LEFT JOIN restaurants r ON r.id = p.assigned_restaurant_id
                WHERE COALESCE(p.status, 'Aktif') = 'Aktif'
                ORDER BY p.role, r.brand NULLS LAST, p.full_name
                """
            )
            rows = cur.fetchall()

    same_restaurant: list[dict] = []
    other_restaurant_couriers: list[dict] = []
    jokers: list[dict] = []
    management: list[dict] = []

    for r in rows:
        item = {
            "id": int(r["id"]),
            "person_code": r.get("person_code"),
            "full_name": r.get("full_name"),
            "role": r.get("role"),
            "rest_brand": r.get("rest_brand"),
            "rest_branch": r.get("rest_branch"),
        }
        role = (r.get("role") or "").strip()
        rid = r.get("assigned_restaurant_id")

        if role in ("Bölge Müdürü", "Kaptan", "Restoran Takım Şefi"):
            management.append(item)
        elif role == "Joker":
            jokers.append(item)
        elif role == "Kurye":
            if rid == restaurant_id:
                same_restaurant.append(item)
            elif rid is not None:
                # Atanmış başka restoranın kuryesi → destek olarak gelebilir
                other_restaurant_couriers.append(item)

    return {
        "restaurant_id": restaurant_id,
        "same_restaurant": same_restaurant,
        "other_restaurant_couriers": other_restaurant_couriers,
        "jokers": jokers,
        "management": management,
    }
