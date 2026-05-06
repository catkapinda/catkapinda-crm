"""Bordro endpoint'leri."""
import logging
from urllib.parse import quote

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
    mark_paid as svc_mark_paid,
    unmark_paid as svc_unmark_paid,
)

log = logging.getLogger(__name__)

router = APIRouter()


# Türkçe karakter → ASCII tablosu (Content-Disposition filename için)
_TR_ASCII = str.maketrans({
    "ç": "c", "Ç": "C",
    "ğ": "g", "Ğ": "G",
    "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O",
    "ş": "s", "Ş": "S",
    "ü": "u", "Ü": "U",
    "â": "a", "Â": "A",
    "î": "i", "Î": "I",
    "û": "u", "Û": "U",
})


def _safe_filename(name: str) -> str:
    """HTTP Content-Disposition için güvenli ASCII dosya adı."""
    s = name.translate(_TR_ASCII)
    # Geriye kalan ASCII-dışı karakterleri at
    s = s.encode("ascii", "ignore").decode("ascii")
    return s.replace(" ", "_").replace("/", "-").replace("\\", "-")


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


@router.patch("/signatures/{personnel_id}/mark-paid")
async def mark_signature_paid(
    personnel_id: int,
    period: str,
    paid_by: str | None = None,
    paid_amount: float | None = None,
) -> dict:
    """İmzalı bordroyu 'ödendi' olarak işaretle (Hakediş Onayları sayfası)."""
    row = svc_mark_paid(
        personnel_id=personnel_id,
        period=period,
        paid_by=paid_by,
        paid_amount=paid_amount,
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="İmza kaydı bulunamadı (kurye+ay)",
        )
    return row


@router.patch("/signatures/{personnel_id}/unmark-paid")
async def unmark_signature_paid(personnel_id: int, period: str) -> dict:
    """Ödendi işaretini geri al (admin yanlış işaretlediyse)."""
    ok = svc_unmark_paid(personnel_id=personnel_id, period=period)
    if not ok:
        raise HTTPException(status_code=404, detail="İmza kaydı bulunamadı")
    return {"unmarked": True, "personnel_id": personnel_id, "period": period}


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

    # ASCII fallback (eski tarayıcılar) + RFC 5987 UTF-8 (modern tarayıcılar).
    # Bu kombinasyon UnicodeEncodeError'ı önler (latin-1 zorunluluğu) ve
    # modern tarayıcılarda Türkçe karakterli dosya adı görünür.
    ascii_name = _safe_filename(full_name)
    pretty_name = full_name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    ascii_filename = f"Bordro_{ascii_name}_{period}.pdf"
    utf8_filename = f"Bordro_{pretty_name}_{period}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_filename}"; '
                f"filename*=UTF-8''{quote(utf8_filename)}"
            ),
            "Cache-Control": "no-store",
        },
    )
