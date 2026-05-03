"""Personel CRUD endpoint'leri."""
from fastapi import APIRouter

from app.services.personel import list_personnel

router = APIRouter()


@router.get("")
async def list_all(status: str | None = None) -> list[dict]:
    """Tüm personeli listele.

    status: 'Aktif', 'Pasif' veya None (hepsi)
    """
    return list_personnel(status=status)
