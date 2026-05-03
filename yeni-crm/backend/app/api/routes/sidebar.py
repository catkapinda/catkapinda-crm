"""Sidebar canlı sayaç endpoint'i."""
from fastapi import APIRouter

from app.services.sidebar import get_sidebar_counts

router = APIRouter()


@router.get("/counts")
async def sidebar_counts() -> dict:
    """Yan menüde rozet olarak gösterilecek canlı sayılar."""
    return get_sidebar_counts()
