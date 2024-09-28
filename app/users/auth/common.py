from typing import Literal, TypeAlias, TypedDict
import typing

from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

authentication_exception = HTTPException(
    HTTP_401_UNAUTHORIZED,
    detail="User is not authorized",
    headers={"WWW-Authenticate": "Bearer"},
)

authorization_exception = HTTPException(
    HTTP_403_FORBIDDEN,
    detail="User doesn't have necessary permissions",
)


Area: TypeAlias = Literal[
    "api",
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

SubscriptionLevel: TypeAlias = Literal["base", "pro"]
Level: TypeAlias = Literal[SubscriptionLevel, "premium", "enterprise"]

levels = typing.get_args(Level)


class WebhookLimits(TypedDict):
    max_count: int
    max_feeds_per_hook: int


levels_access: dict[Level, list[Area]] = {
    "base": ["articles", "webhook"],
    "pro": [
        "articles",
        "assistant",
        "cluster",
        "dashboard",
        "map",
        "similar",
        "summary",
        "cve",
        "webhook",
    ],
    "premium": [
        "articles",
        "assistant",
        "cluster",
        "dashboard",
        "map",
        "similar",
        "summary",
        "cve",
        "webhook",
    ],
    "enterprise": [
        "api",
        "articles",
        "assistant",
        "cluster",
        "dashboard",
        "map",
        "similar",
        "summary",
        "cve",
        "webhook",
    ],
}

webhook_limits: dict[Level, WebhookLimits] = {
    "base": {"max_count": 3, "max_feeds_per_hook": 3},
    "premium": {"max_count": 3, "max_feeds_per_hook": 3},
    "pro": {"max_count": 10, "max_feeds_per_hook": 3},
    "enterprise": {"max_count": 10, "max_feeds_per_hook": 3},
}

areas: set[Area] = {area for areas in levels_access.values() for area in areas}
