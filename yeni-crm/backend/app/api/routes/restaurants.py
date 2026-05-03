"""Restoran endpoint'leri."""
from fastapi import APIRouter

from app.services.restaurants import list_restaurants

router = APIRouter()


@router.get("")
async def list_all(active: bool | None = True) -> list[dict]:
    """Tüm restoranları listele."""
    return list_restaurants(active=active)
