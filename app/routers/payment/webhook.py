from typing import Annotated
from fastapi import APIRouter, HTTPException, Header, Request
from starlette.status import HTTP_400_BAD_REQUEST
import stripe

from app import config_options
from app.users import models, schemas
from app.users.crud import update_user

from .common import products_by_id

router = APIRouter()


def get_user_from_stripe_id(id: str) -> schemas.User:
    user_obj: models.User = list(
        models.User.by_stripe_id(config_options.couch_conn)[id]
    )[0]
    return schemas.User.model_validate(user_obj)


def handle_subscription_change(e: stripe.Event) -> None:
    data = e.data["object"]
    user = get_user_from_stripe_id(data["customer"])

    if e.type.startswith("invoice"):
        if user.payment.invoice.last_updated > data["created"]:
            return
        elif data["billing_reason"] == "subscription_create":
            if e.type in ["invoice.payment_action_required", "invoice.payment_failed"]:
                return

    elif e.type.startswith("customer.subscriptions"):
        if user.payment.subscription.last_updated > data["created"]:
            return

    match e.type:
        case "customer.subscription.updated":

            if data["status"] in ["trailing", "active"]:
                # WARNING: Potential problematic undefined object reference
                product_id = data["plan"]["product"]
                level = products_by_id[product_id]["metadata"]["level"]

                user.payment.subscription.level = level
                user.payment.subscription.state = "active"
            elif data["status"] in [
                "unpaid",
                "canceled",
                "incomplete_expired",
                "incomplete",
            ]:
                user.payment.subscription.stripe_product_id = ""
                user.payment.subscription.stripe_subscription_id = ""
                user.payment.subscription.level = ""
                user.payment.subscription.state = "closed"
            elif data["status"] in ["past_due"]:
                user.payment.subscription.state = "past_due"
            else:
                raise Exception(f'Got unexpected status: "{data["status"]}"')

        case "customer.subscription.deleted":
            user.payment.subscription = schemas.UserPayment.Subscription(state="closed")
            user.payment.invoice = schemas.UserPayment.Invoice()

        case "invoice.payment_failed":
            user.payment.invoice.action_required = True
            user.payment.invoice.action_type = "update"
            user.payment.invoice.payment_intent = data["payment_intent"]

        case "invoice.payment_action_required":
            user.payment.invoice.action_required = True
            user.payment.invoice.action_type = "authenticate"
            user.payment.invoice.payment_intent = data["payment_intent"]

        case "invoice.paid":
            user.payment.invoice.action_required = False
            user.payment.invoice.action_type = ""
            user.payment.invoice.payment_intent = ""

    if e.type.startswith("customer.subscription"):
        user.payment.subscription.stripe_subscription_id = data["id"]
        user.payment.subscription.stripe_product_id = data["plan"]["product"]
        user.payment.subscription.last_updated = data["created"]
        user.payment.subscription.cancel_at_period_end = data["cancel_at_period_end"]
        user.payment.subscription.current_period_end = data["current_period_end"]
        user.payment.subscription.automatic_tax = data["automatic_tax"]["enabled"]

    elif e.type.startswith("invoice"):
        user.payment.invoice.invoice_url = data["hosted_invoice_url"]
        user.payment.invoice.last_updated = data["created"]

    update_user(user)


@router.post("/stripe-webhook")
async def handle_stripe_webhook(
    stripe_signature: Annotated[str, Header()], request: Request
) -> None:
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, stripe_signature, config_options.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(
            HTTP_400_BAD_REQUEST, "Error when verifying webhook signature"
        )

    if event.type in [
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.created",
        "invoice.payment_action_required",
        "invoice.payment_failed",
        "invoice.paid",
    ]:
        handle_subscription_change(event)
