from typing import Annotated, Literal
from typing_extensions import TypedDict
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

import stripe

from app.users.auth import (
    ensure_user_from_token,
)
from app.users.crud import update_user
from app.users.schemas import User


router = APIRouter()


def create_customer(name: str, email: str, id: str) -> stripe.Customer:
    return stripe.Customer.create(name=name, email=email, metadata={"user_id": id})


class SubscriptionCreation(TypedDict):
    type: Literal["setup", "payment"]
    client_secret: str


@router.post("/subscription")
def create_subscription(
    user: User = Depends(ensure_user_from_token),
    email: str | None = Body(None),
    price_id: str = Body(...),
) -> SubscriptionCreation:
    if not user.payment.stripe_id:
        if not email:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing email"
            )

        customer = create_customer(user.username, email, str(user.id))
        user.payment.stripe_id = customer.id
        update_user(user)
    elif user.payment.subscription.state not in ["", "closed"]:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT, detail="User is already subscribed"
        )

    try:
        subscription = stripe.Subscription.create(
            customer=user.payment.stripe_id,
            items=[
                {
                    "price": price_id,
                }
            ],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent", "pending_setup_intent"],
        )

        if subscription.pending_setup_intent is not None:
            return {
                "type": "setup",
                "client_secret": subscription.pending_setup_intent.client_secret,  # type: ignore
            }
        else:
            return {
                "type": "payment",
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,  # type: ignore
            }
    except stripe.APIError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=e.user_message)


@router.delete("/subscription")
def cancel_subscription(
    immediate: Annotated[bool, Query()] = False,
    user: User = Depends(ensure_user_from_token),
) -> None:
    if user.payment.subscription.state in ["active", "past_due"]:
        if immediate:
            stripe.Subscription.cancel(user.payment.subscription.stripe_subscription_id)
        else:
            stripe.Subscription.modify(
                user.payment.subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
    else:
        raise HTTPException(
            HTTP_404_NOT_FOUND, "User doesn't have any active subscriptions"
        )


@router.post("/subscription/uncancel")
def resume_subscription(user: Annotated[User, Depends(ensure_user_from_token)]) -> None:
    if user.payment.subscription.state not in ["active", "past_due"]:
        raise HTTPException(
            HTTP_404_NOT_FOUND, "User doesn't have any active subscriptions"
        )
    elif not user.payment.subscription.cancel_at_period_end:
        raise HTTPException(HTTP_400_BAD_REQUEST, "User subscription isn't cancelled")

    stripe.Subscription.modify(
        user.payment.subscription.stripe_subscription_id, cancel_at_period_end=False
    )


@router.post("/subscription/acknowledge-close")
def acknowledge_subscription_closing(
    user: User = Depends(ensure_user_from_token),
) -> None:
    if (
        user.payment.subscription.state != "closed"
        and user.payment.subscription.state != ""
    ):
        raise HTTPException(HTTP_400_BAD_REQUEST, "User subscription isn't closed")

    user.payment.subscription.state = ""
    update_user(user)
