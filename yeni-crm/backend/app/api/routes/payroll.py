"""Bordro endpoint'leri."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.payroll import get_personnel_payroll, list_payroll
from app.services.payroll_pdf import generate_payroll_pdf
from app.services.personel import get_personnel

router = APIRouter()


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
    payroll = get_personnel_payroll(personnel_id=personnel_id, period=period)
    if not payroll:
        raise HTTPException(status_code=404, detail="Bordro bulunamadı")

    personnel = get_personnel(personnel_id)
    pdf_bytes = generate_payroll_pdf(payroll, personnel, period)

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
