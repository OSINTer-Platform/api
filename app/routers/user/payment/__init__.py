from typing import Annotated
from fastapi import APIRouter, Body, Depends, HTTPException

from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
import stripe

from app import config_options
from app.users.auth import ensure_user_from_request
from app.users.crud import update_user
from app.users.schemas import User, UserAddress
from app.users.stripe import get_or_create_customer, get_stripe_address
from .subscriptions import router as subscription_router

stripe.api_key = config_options.STRIPE_API_KEY

router = APIRouter(prefix="/payment")
router.include_router(subscription_router, tags=["payment"])


@router.get("/action/payment-intent")
def get_action_payment_intent(
    user: User = Depends(ensure_user_from_request),
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


@router.put("/address")
def update_customer_address(
    user_and_customer: Annotated[
        tuple[User, stripe.Customer], Depends(get_or_create_customer)
    ],
    address: Annotated[UserAddress, Body()],
) -> User:
    user, customer = user_and_customer

    stripeAddress = get_stripe_address(address)

    try:
        customer.modify(
            customer.id,
            address=stripeAddress,
            shipping={"name": address.customer_name, "address": stripeAddress},
            tax={"validate_location": "immediately"},
        )
    except stripe.InvalidRequestError as e:
        if e.code == "customer_tax_location_invalid":
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid address. Please specify a valid one",
            )
        raise e

    user.payment.address = address
    update_user(user)

    return user
