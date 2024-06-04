from datetime import UTC, datetime
from typing import Annotated, Literal, TypeAlias, TypeVar

from fastapi import Depends

from app.users.auth import ensure_user_from_token
from app.users.auth import get_user_from_token, auth_exception
from app.users.schemas import User


Area: TypeAlias = Literal[
    "assistant", "cluster", "dashboard", "map", "similar", "summary", "cve"
]

levels_access: dict[str, list[Area]] = {
    "pro": ["assistant", "cluster", "dashboard", "map", "similar", "summary", "cve"]
}

areas: set[Area] = {area for areas in levels_access.values() for area in areas}


def authorize(level: str, area: Area) -> bool:
    return level in levels_access and area in levels_access[level]


def get_allowed_areas(
    user: Annotated[User | None, Depends(get_user_from_token)]
) -> list[Area]:
    if not user:
        return []

    if user.premium.status:
        return list(areas)

    if user.payment.subscription.level in levels_access:
        return levels_access[user.payment.subscription.level]

    return []


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

        raise auth_exception