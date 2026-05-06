"""Bordro endpoint'leri."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from psycopg.rows import dict_row

from app.core.database import get_connection
from app.services.payroll import get_personnel_payroll, list_payroll
from app.services.payroll_pdf import generate_payroll_pdf
from app.services.personel import get_personnel
from app.services.signatures import (
    delete_signature,
    list_signatures_for_period,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/signatures")
async def list_signatures(period: str = "2026-03") -> list[dict]:
    """Belirli ay için bordrosunu imzalayan kuryeler — admin için."""
    return list_signatures_for_period(period=period)


@router.get("/sms-log/clear")
async def clear_payroll_sms_log(personnel_id: int, period: str) -> dict:
    """Belirli kurye+ay için SMS log kaydını siler.

    Admin debug — yeniden SMS gönderim akışını test etmek için.
    Kayıt silindiğinde aynı kurye×ay için bir sonraki onayda yeniden
    SMS gönderim denemesi yapılır (dedup sıfırlanır).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM payroll_sms_log "
                "WHERE personnel_id = %s AND period = %s",
                (personnel_id, period),
            )
            deleted = cur.rowcount
            conn.commit()
    return {
        "deleted": int(deleted),
        "personnel_id": int(personnel_id),
        "period": period,
    }


@router.get("/sms-log")
async def list_payroll_sms_log(
    period: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Bordro hazır SMS gönderim log'u — admin debugging için.

    Kim ne aldı / kime gitmedi / hangi sebeple atlandı görmek için.
    İsteğe bağlı `period=YYYY-MM` filtresi.
    """
    sql_base = """
        SELECT
          psl.id,
          psl.personnel_id,
          p.full_name,
          p.phone AS personnel_phone,
          psl.period,
          psl.sent_at,
          psl.status,
          psl.phone_used,
          psl.error,
          psl.triggered_by_approval_id
        FROM payroll_sms_log psl
        LEFT JOIN personnel p ON p.id = psl.personnel_id
    """
    params: tuple = ()
    if period:
        sql = sql_base + " WHERE psl.period = %s ORDER BY psl.sent_at DESC LIMIT %s"
        params = (period, limit)
    else:
        sql = sql_base + " ORDER BY psl.sent_at DESC LIMIT %s"
        params = (limit,)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    out: list[dict] = []
    for r in rows:
        out.append({
            "id": int(r["id"]),
            "personnel_id": int(r["personnel_id"]),
            "full_name": r.get("full_name"),
            "personnel_phone": r.get("personnel_phone"),
            "period": str(r["period"]),
            "sent_at": r["sent_at"].isoformat() if r.get("sent_at") else None,
            "status": str(r["status"]),
            "phone_used": r.get("phone_used"),
            "error": r.get("error"),
            "triggered_by_approval_id": (
                int(r["triggered_by_approval_id"])
                if r.get("triggered_by_approval_id") is not None
                else None
            ),
        })
    return out


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

    try:
        payroll = get_personnel_payroll(personnel_id=personnel_id, period=period)
        if not payroll:
            raise HTTPException(status_code=404, detail="Bordro bulunamadı")

        personnel = get_personnel(personnel_id)
        signature = get_signature(personnel_id, period, include_data=True)
        pdf_bytes = generate_payroll_pdf(
            payroll, personnel, period, signature=signature,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Tanı için tam traceback log'a yazılsın + response'a hatanın türü
        # ve mesajı düşsün (sadece staging — production'da generic 500 olabilir)
        log.exception(
            "PDF generation failed personnel=%s period=%s",
            personnel_id, period,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: {str(exc)[:400]}"
            ),
        ) from exc

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
