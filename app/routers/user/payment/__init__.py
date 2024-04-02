from fastapi import APIRouter, Depends, HTTPException

from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
import stripe

from app import config_options
from app.users.auth import ensure_user_from_token
from app.users.schemas import User
from .subscriptions import router as subscription_router

stripe.api_key = config_options.STRIPE_API_KEY

router = APIRouter(prefix="/payment")
router.include_router(subscription_router, tags=["payment"])


@router.get("/action/payment-intent")
def get_action_payment_intent(
    user: User = Depends(ensure_user_from_token),
) -> dict[str, str]:
    if not user.payment.invoice.payment_intent:
        raise HTTPException(
            HTTP_404_NOT_FOUND, "No payment intent was found for user action"
        )

    payment_intent = stripe.PaymentIntent.retrieve(user.payment.invoice.payment_intent)
    if not payment_intent.client_secret:
        raise HTTPException(
            HTTP_500_INTERNAL_SERVER_ERROR, "Error when loading payment intent"
        )
    return {"client_secret": payment_intent.client_secret}
