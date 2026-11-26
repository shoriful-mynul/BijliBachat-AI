from fastapi import APIRouter

from app.api.routes.bills import router as bill_router
from app.api.routes.health import router as health_router
from app.api.routes.meter import router as meter_router
from app.api.routes.tariffs import router as tariff_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(tariff_router, tags=["tariffs"])
api_router.include_router(bill_router, tags=["bills"])
api_router.include_router(meter_router, tags=["meter"])
