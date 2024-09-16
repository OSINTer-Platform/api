from datetime import UTC, datetime
from typing import Annotated, Literal, TypeAlias, TypeGuard, TypeVar, TypedDict
import typing

from fastapi import Depends

from app.users.auth import ensure_user_from_token
from app.users.auth import get_user_from_token, authorization_exception
from app.users.schemas import User


Area: TypeAlias = Literal[
    "articles",
    "assistant",
    "cluster",
    "dashboard",
    "map",
    "similar",
    "summary",
    "cve",
    "webhook",
]

Level: TypeAlias = Literal["base", "pro"]

levels = typing.get_args(Level)


class WebhookLimits(TypedDict):
    max_count: int
    max_feeds_per_hook: int


levels_access: dict[Level, list[Area]] = {
    "base": ["articles"],
    "pro": [
        "articles",
        "assistant",
        "cluster",
        "dashboard",
        "map",
        "similar",
        "summary",
        "cve",
    ],
}

webhook_limits: dict[Literal[Level, "premium"], WebhookLimits] = {
    "base": {"max_count": 0, "max_feeds_per_hook": 0},
    "pro": {"max_count": 10, "max_feeds_per_hook": 3},
    "premium": {"max_count": 10, "max_feeds_per_hook": 3},
}

areas: set[Area] = {area for areas in levels_access.values() for area in areas}


def is_level(level: str) -> TypeGuard[Level]:
    return level in levels


def authorize(level: str, area: Area) -> bool:
    return is_level(level) and area in levels_access[level]


def get_allowed_areas(
    user: Annotated[User | None, Depends(get_user_from_token)]
) -> list[Area]:
    if not user:
        return []

    if user.premium.status:
        return list(areas)

    if is_level(user.payment.subscription.level):
        return levels_access[user.payment.subscription.level]

    return []


def get_webhook_limits(
    user: Annotated[User, Depends(ensure_user_from_token)]
) -> WebhookLimits:
    if user.premium.status:
        return webhook_limits["premium"]
    elif is_level(user.payment.subscription.level):
        return webhook_limits[user.payment.subscription.level]
    else:
        raise authorization_exception


def get_source_exclusions(
    allowed_areas: Annotated[list[Area], Depends(get_allowed_areas)]
) -> list[str]:
    areas_to_fields: dict[Area, str] = {
        "map": "ml.coordinates",
        "cluster": "ml.cluster",
        "similar": "similar",
        "summary": "summary",
    }

    return [v for k, v in areas_to_fields.items() if not k in allowed_areas]


UserType = TypeVar("UserType", bound=User)


def expire_premium(user: UserType) -> UserType:
    if (
        user.premium.expire_time > 0
        and user.premium.expire_time < datetime.now(UTC).timestamp()
    ):
        user.premium.status = False
        user.premium.expire_time = 0

    return user


class UserAuthorizer:
    def __init__(self, areas: list[Area]):
        self.areas: list[Area] = areas

    def __call__(self, user: Annotated[User, Depends(ensure_user_from_token)]) -> User:
        if user.premium.status:
            return user

        for area in self.areas:
            if authorize(user.payment.subscription.level, area):
                return user

        raise authorization_exception
