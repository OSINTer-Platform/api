from typing import Annotated, cast
from fastapi import APIRouter, HTTPException, Header, Request

from starlette.status import HTTP_400_BAD_REQUEST
import stripe

from app import config_options
from app.users import models, schemas
from app.users.crud import update_user

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




@router.get("/prices", response_model=None)
def get_prices() -> dict[str, stripe.Price]:
    return prices_by_id


@router.get("/products", response_model=None)
def get_products() -> dict[str, stripe.Product]:
    return products_by_id


        )
        )

