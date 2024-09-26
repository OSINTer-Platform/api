from typing import Annotated
from fastapi import Depends
from . import ensure_user_from_request, get_user_from_request
from .authorization import (
    authorize_user,
    calc_allowed_areas,
    calc_source_exclusions,
    calc_webhook_limits,
)
from .common import Area, WebhookLimits, authorization_exception
from app.users.schemas import User


def get_allowed_areas(
    user: Annotated[User | None, Depends(get_user_from_request)]
) -> list[Area]:
    return calc_allowed_areas(user)


def get_webhook_limits(
    user: Annotated[User, Depends(ensure_user_from_request)]
) -> WebhookLimits:
    return calc_webhook_limits(user)


def get_source_exclusions(
    allowed_areas: Annotated[list[Area], Depends(get_allowed_areas)]
) -> list[str]:
    return calc_source_exclusions(allowed_areas)


class UserAuthorizer:
    def __init__(self, areas: list[Area]):
        self.areas: list[Area] = areas

    def __call__(
        self, user: Annotated[User, Depends(ensure_user_from_request)]
    ) -> User:
        authorized = authorize_user(user, self.areas)

        if not authorized:
            raise authorization_exception

        return user
