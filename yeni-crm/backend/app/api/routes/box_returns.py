"""Box / ekipman geri alım endpoint'leri."""
from fastapi import APIRouter, HTTPException

from app.services import box_returns as svc

router = APIRouter()


@router.get("")
async def list_box_returns(
    personnel_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    condition: str | None = None,
    search: str | None = None,
    limit: int = 500,
) -> dict:
    """Filtreli liste + KPI özet."""
    rows = svc.list_box_returns(
        personnel_id=personnel_id,
        date_from=date_from,
        date_to=date_to,
        condition=condition,
        search=search,
        limit=limit,
    )
    summary = svc.stats_summary(date_from=date_from, date_to=date_to)
    return {
        "items": rows,
        "summary": summary,
        "condition_options": svc.CONDITION_OPTIONS,
        "item_options": svc.ITEM_OPTIONS,
    }


@router.get("/{box_return_id}")
async def get_box_return(box_return_id: int) -> dict:
    row = svc.get_box_return(box_return_id)
    if not row:
        raise HTTPException(404, detail="Kayıt bulunamadı.")
    return row


@router.post("", status_code=201)
async def create_box_return(payload: dict) -> dict:
    try:
        return svc.create_box_return(payload)
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e


@router.patch("/{box_return_id}")
async def update_box_return(box_return_id: int, payload: dict) -> dict:
    try:
        return svc.update_box_return(box_return_id, payload)
    except LookupError as e:
        raise HTTPException(404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e


@router.delete("/{box_return_id}", status_code=204)
async def delete_box_return(box_return_id: int) -> None:
    try:
        svc.delete_box_return(box_return_id)
    except LookupError as e:
        raise HTTPException(404, detail=str(e)) from e
