"""Bordro endpoint'leri."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.payroll import get_personnel_payroll, list_payroll
from app.services.payroll_pdf import generate_payroll_pdf
from app.services.personel import get_personnel
from app.services.signatures import (
    delete_signature,
    list_signatures_for_period,
)

router = APIRouter()


@router.get("/signatures")
async def list_signatures(period: str = "2026-03") -> list[dict]:
    """Belirli ay için bordrosunu imzalayan kuryeler — admin için."""
    return list_signatures_for_period(period=period)


@router.delete("/signatures/{personnel_id}")
async def delete_personnel_signature(
    personnel_id: int,
    period: str = "2026-03",
) -> dict:
    """Bir kuryenin belirli aydaki imzasını sil — yeniden imzalanması gerektiğinde."""
    deleted = delete_signature(personnel_id=personnel_id, period=period)
    return {"deleted": deleted}


@router.get("")
async def get_payroll(period: str = "2026-03") -> dict:
    """Aylık bordro — tüm aktif kuryelerin brüt+kesinti+net özeti."""
    return list_payroll(period=period)


@router.get("/{personnel_id}")
async def get_personnel_payroll_detail(
    personnel_id: int,
    period: str = "2026-03",
) -> dict:
    """Tek kurye bordro detayı (yazdır / PDF için)."""
    row = get_personnel_payroll(personnel_id=personnel_id, period=period)
    if not row:
        raise HTTPException(status_code=404, detail="Bordro bulunamadı")
    return row


@router.get("/{personnel_id}/pdf")
async def get_personnel_payroll_pdf(
    personnel_id: int,
    period: str = "2026-03",
):
    """Tek kurye bordrosunu PDF olarak indir (Content-Disposition: attachment)."""
    from app.services.signatures import get_signature

    payroll = get_personnel_payroll(personnel_id=personnel_id, period=period)
    if not payroll:
        raise HTTPException(status_code=404, detail="Bordro bulunamadı")

    personnel = get_personnel(personnel_id)
    signature = get_signature(personnel_id, period, include_data=True)
    pdf_bytes = generate_payroll_pdf(payroll, personnel, period, signature=signature)

    full_name = (payroll.get("full_name") or f"kurye-{personnel_id}").strip()
    safe_name = (
        full_name.replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
    )
    filename = f"Bordro_{safe_name}_{period}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
