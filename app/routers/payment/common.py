from typing import Literal, TypeAlias, TypedDict
import stripe

PriceLookupKey: TypeAlias = Literal["base-month", "pro-month"]


class PriceCalculation(TypedDict):
    currency: str
    estimate: bool
    lookup_key: str
    price_id: str
    tax_amount: int
    total_unit_amount: int
    total_without_tax: int


product = stripe.Product.list().data
products_by_id: dict[str, stripe.Product] = {obj["id"]: obj for obj in product}

prices = stripe.Price.list().data
prices_by_id: dict[str, stripe.Price] = {obj["id"]: obj for obj in prices}
prices_by_key: dict[PriceLookupKey, stripe.Price] = {
    price["lookup_key"]: price for price in prices
}
