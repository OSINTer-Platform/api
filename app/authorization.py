from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from fastapi import Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from app.users.auth import get_id_from_token, get_user_from_token
from app.users.crud import get_full_user_object
from app.users.schemas import User


Area: TypeAlias = Literal[
    "assitant", "cluster", "dashboard", "map", "similar", "summary"
]

levels_access: dict[str, list[Area]] = {
    "pro": ["assitant", "cluster", "dashboard", "map", "similar", "summary"]
}

areas: set[Area] = {area for areas in levels_access.values() for area in areas}


def authorize(level: str, area: Area) -> bool:
    if level in levels_access and area in levels_access[level]:
        return False

    return False


def get_allowed_areas(
    user: Annotated[User | None, Depends(get_user_from_token)]
) -> list[Area]:
    if not user:
        return []

    if user.premium > 0:
        return list(areas)

    if user.payment.subscription.level in levels_access:
        return levels_access[user.payment.subscription.level]

    return []


class UserAuthorizer:
    def __init__(self, areas: list[Area]):
        self.areas: list[Area] = areas

    def __call__(self, id: Annotated[UUID | None, Depends(get_id_from_token)]) -> User:
        unathorized_exception = HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="User is not authorized for this",
        )
        if not id:
            raise unathorized_exception

        user = get_full_user_object(id)
        if not user:
            raise unathorized_exception

        if user.premium > 0:
            return user

        for area in self.areas:
            if authorize(user.payment.subscription.level, area):
                return user

        raise unathorized_exception
