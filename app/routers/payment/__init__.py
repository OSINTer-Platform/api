from typing import Annotated, Literal, TypeAlias, TypedDict
from fastapi import APIRouter, Depends, Request

import stripe

from app import config_options
from app.users import schemas
from app.users.auth import get_user_from_request
from app.users.stripe import get_stripe_address

stripe.api_key = config_options.STRIPE_API_KEY

router = APIRouter()

PriceLookupKey: TypeAlias = Literal["base-month", "pro-month"]

product = stripe.Product.list().data
products_by_id: dict[str, stripe.Product] = {obj["id"]: obj for obj in product}

prices = stripe.Price.list().data
prices_by_id: dict[str, stripe.Price] = {obj["id"]: obj for obj in prices}
prices_by_key: dict[PriceLookupKey, stripe.Price] = {
    price["lookup_key"]: price for price in prices
}


class PriceCalculation(TypedDict):
    currency: str
    estimate: bool
    lookup_key: str
    price_id: str
    tax_amount: int
    total_unit_amount: int
    total_without_tax: int


@router.get("/prices", response_model=None)
def get_prices() -> dict[str, stripe.Price]:
    return prices_by_id


@router.get("/products", response_model=None)
def get_products() -> dict[str, stripe.Product]:
    return products_by_id


@router.get("/price/calc/{price_key}")
def calculate_price(
    price_key: PriceLookupKey,
    user: Annotated[schemas.User | None, Depends(get_user_from_request)],
    request: Request,
) -> PriceCalculation:
    price = prices_by_key[price_key]

    invoice: stripe.Invoice
    estimate = True

    if user and user.payment.address:
        invoice = stripe.Invoice.create_preview(
            customer=user.payment.stripe_id,
            automatic_tax={"enabled": True},
            subscription_details={"items": [{"price": price.id}]},
        )
        estimate = False

    elif request.client:
        invoice = stripe.Invoice.create_preview(
            automatic_tax={"enabled": True},
            customer_details={"tax": {"ip_address": request.client.host}},
            subscription_details={"items": [{"price": price.id}]},
        )
    else:
        invoice = stripe.Invoice.create_preview(
            subscription_details={"items": [{"price": price.id}]}
        )

    exTax = invoice.total_excluding_tax

    return {
        "currency": invoice.currency,
        "estimate": estimate,
        "lookup_key": price_key,
        "price_id": price.id,
        "tax_amount": invoice.tax if invoice.tax else 0,
        "total_unit_amount": invoice.total,
        "total_without_tax": exTax if exTax else invoice.total,
    }
