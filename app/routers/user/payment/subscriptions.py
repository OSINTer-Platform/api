from typing import Annotated, Literal
from typing_extensions import TypedDict
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

import stripe

from app.users.stripe import get_or_create_customer
from app.users.auth import (
    ensure_user_from_request,
)
from app.users.crud import update_user
from app.users.schemas import User


router = APIRouter()


class SubscriptionCreation(TypedDict):
    type: Literal["setup", "payment"]
    client_secret: str


@router.post("/subscription")
def create_subscription(
    user_and_customer: Annotated[
        tuple[User, stripe.Customer], Depends(get_or_create_customer)
    ],
    price_id: Annotated[str, Body()],
    email: Annotated[str, Body()],
) -> SubscriptionCreation:
    user, customer = user_and_customer

    if email != customer.email:
        customer.modify(customer.id, email=email)

    if user.payment.subscription.state not in ["", "closed"]:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT, detail="User is already subscribed"
        )

    try:
        subscription = stripe.Subscription.create(
            automatic_tax={"enabled": True},
            customer=customer.id,
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


@router.post("/subscription/change")
def change_subscription(
    user: Annotated[User, Depends(ensure_user_from_request)],
    price_id: Annotated[str, Body()],
) -> None:
    try:
        subscription_item = stripe.SubscriptionItem.list(
            limit=1, subscription=user.payment.subscription.stripe_subscription_id
        ).data[0]
    except (stripe.InvalidRequestError, IndexError):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="User doesn't have any active subscription",
        )

    stripe.SubscriptionItem.modify(subscription_item.id, price=price_id)


@router.delete("/subscription")
def cancel_subscription(
    immediate: Annotated[bool, Query()] = False,
    user: User = Depends(ensure_user_from_request),
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
def resume_subscription(
    user: Annotated[User, Depends(ensure_user_from_request)]
) -> None:
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
    user: User = Depends(ensure_user_from_request),
) -> None:
    if (
        user.payment.subscription.state != "closed"
        and user.payment.subscription.state != ""
    ):
        raise HTTPException(HTTP_400_BAD_REQUEST, "User subscription isn't closed")

    user.payment.subscription.state = ""
    update_user(user)
