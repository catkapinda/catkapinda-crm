from fastapi import APIRouter

from app.api.routes import announcements, attendance, audit, auth, backups, deductions, equipment, health, overview, payroll, personnel, purchases, reports, restaurants, sales

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(backups.router, prefix="/backups", tags=["backups"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(overview.router, prefix="/overview", tags=["overview"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(deductions.router, prefix="/deductions", tags=["deductions"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
api_router.include_router(personnel.router, prefix="/personnel", tags=["personnel"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(restaurants.router, prefix="/restaurants", tags=["restaurants"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
