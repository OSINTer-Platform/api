from uuid import UUID
from fastapi import APIRouter
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from typing_extensions import TypedDict

import stripe

from app.users.auth import ensure_id_from_token

router = APIRouter()


class PaymentDetails(TypedDict):
    amount: int
    currency: str


payment_options: dict[str, PaymentDetails] = {
    "personal": {
        "amount": 1500,
        "currency": "usd",
    }
}


class PaymentDetailsWithIntent(PaymentDetails):
    client_secret: str


@router.get("/payment-types")
def get_payment_types() -> dict[str, PaymentDetails]:
    return payment_options


@router.post("/create-payment-intent")
def create_payment_intent(
    _: UUID = Depends(ensure_id_from_token), payment_type: str = Query(...)
) -> PaymentDetailsWithIntent:
    if payment_type not in payment_options:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payment method wasn't recognized",
        )

    payment_details = payment_options[payment_type]

    intent = stripe.PaymentIntent.create(
        amount=payment_details["amount"],
        currency=payment_details["currency"],
        automatic_payment_methods={
            "enabled": True,
        },
    )

    return {"client_secret": intent["client_secret"], **payment_details}
