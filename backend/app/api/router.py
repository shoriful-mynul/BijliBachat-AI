from fastapi import APIRouter

from app.api.routes.account import router as account_router
from app.api.routes.appliances import router as appliance_router
from app.api.routes.bills import router as bill_router
from app.api.routes.health import router as health_router
from app.api.routes.history import router as history_router
from app.api.routes.meter import router as meter_router
from app.api.routes.predictions import router as prediction_router
from app.api.routes.tariffs import router as tariff_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(tariff_router, tags=["tariffs"])
api_router.include_router(bill_router, tags=["bills"])
api_router.include_router(meter_router, tags=["meter"])
api_router.include_router(prediction_router, tags=["predictions"])
api_router.include_router(appliance_router, tags=["appliances"])
api_router.include_router(history_router, tags=["history"])
api_router.include_router(account_router, tags=["account"])
