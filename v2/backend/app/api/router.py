from fastapi import APIRouter

from app.api.routes import attendance, auth, deductions, health, personnel

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(deductions.router, prefix="/deductions", tags=["deductions"])
api_router.include_router(personnel.router, prefix="/personnel", tags=["personnel"])
