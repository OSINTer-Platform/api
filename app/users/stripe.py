from typing import Annotated
from fastapi import Depends
import stripe

from app import config_options
from app.users.auth import ensure_user_from_request
from app.users.crud import update_user
from app.users.schemas import User

stripe.api_key = config_options.STRIPE_API_KEY


def get_or_create_customer(
    user: Annotated[User, Depends(ensure_user_from_request)],
) -> tuple[User, stripe.Customer]:
    if not user.payment.stripe_id:
        customer = stripe.Customer.create(
            name=user.username, metadata={"user_id": str(user.id)}
        )
        user.payment.stripe_id = customer.id
        update_user(user)

        return user, customer

    else:
        customer = stripe.Customer.retrieve(user.payment.stripe_id)
        return user, customer
