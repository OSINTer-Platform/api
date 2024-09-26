from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Request

from .common import authentication_exception
from .token import get_id_from_token
from app.users.schemas import User


def get_user_from_request(
    request: Request,
    id: Annotated[None | UUID, Depends(get_id_from_token)],
    api_key: Annotated[str | None, Query()] = None,
) -> User | None:
    if not id:
        return None

    user: User | None = request.state.user_cache.get_user_from_api_key(api_key)

    if not user:
        user = request.state.user_cache.get_user_from_id(id)

    return user


def ensure_user_from_request(
    user: Annotated[User | None, Depends(get_user_from_request)]
) -> User:
    if not user:
        raise authentication_exception

    return user
