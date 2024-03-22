from fastapi import APIRouter

import stripe

from app import config_options
from .subscriptions import router as subscription_router

stripe.api_key = config_options.STRIPE_API_KEY

router = APIRouter()
router.include_router(subscription_router, prefix="/payment", tags=["payment"])
