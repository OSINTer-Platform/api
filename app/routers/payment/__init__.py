from typing import Annotated, cast
from fastapi import APIRouter, HTTPException, Header, Request

from starlette.status import HTTP_400_BAD_REQUEST
import stripe

from app import config_options
from app.users import models, schemas
from app.users.crud import update_user

stripe.api_key = config_options.STRIPE_API_KEY

router = APIRouter()

products: dict[str, stripe.Product] = {
    obj["id"]: obj for obj in stripe.Product.list().data
}


def get_user_from_stripe_id(id: str) -> tuple[schemas.User, str | None]:
    user_obj: models.User = list(
        models.User.by_stripe_id(config_options.couch_conn)[id]
    )[0]
    return schemas.User.model_validate(user_obj), cast(str | None, user_obj.rev)


def handle_subscription_change(e: stripe.Event) -> None:
    data = e.data["object"]
    user, rev = get_user_from_stripe_id(data["customer"])

    root_obj: schemas.UserPayment.Subscription | schemas.UserPayment.Action

    if e.type in ["invoice.paid", "invoice.payment_action_required"]:
        root_obj = user.payment.action
    else:
        root_obj = user.payment.subscription

    if root_obj.last_updated > data["created"]:
        return

    match e.type:
        case "customer.subscription.updated":
            if data["status"] in ["trailing", "active"]:
                # WARNING: Potential problematic undefined object reference
                product_id = data["plan"]["product"]
                level = products[product_id]["metadata"]["level"]

                user.payment.subscription.level = level
                user.payment.subscription.state = "active"
            elif data["status"] in [
                "unpaid",
                "canceled",
                "incomplete_expired",
                "incomplete",
            ]:
                user.payment.subscription.level = ""
                user.payment.subscription.state = "closed"
            elif data["status"] in ["past_due"]:
                user.payment.subscription.state = "past_due"
            else:
                raise Exception(f'Got unexpected status: "{data["status"]}"')

        case "customer.subscription.deleted":
            user.payment.subscription = schemas.UserPayment.Subscription(state="closed")
            user.payment.action = schemas.UserPayment.Action()

        case "invoice.payment_action_required":
            user.payment.action = schemas.UserPayment.Action(
                required=True,
                payment_intent=data["payment_intent"],
                invoice_url=data["hosted_invoice_url"],
            )

        case "invoice.paid":
            user.payment.action = schemas.UserPayment.Action(
                last_updated=data["created"],
                required=False,
            )

    if e.type.startswith("customer.subscription"):
        user.payment.subscription.stripe_subscription_id = data["id"]
        user.payment.subscription.stripe_product_id = data["plan"]["product"]

    root_obj.last_updated = data["created"]

    update_user(user, rev)


@router.get("/prices", response_model=None)
def get_prices() -> list[stripe.Price]:
    prices = stripe.Price.list(lookup_keys=["pro-month"])

    return prices.data


@router.get("/products", response_model=None)
def get_products() -> dict[str, stripe.Product]:
    return products


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

    print(event.type)

    if event.type in [
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_action_required",
        "invoice.paid",
    ]:
        handle_subscription_change(event)
