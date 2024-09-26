from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Header, Request
from starlette.status import HTTP_401_UNAUTHORIZED

from app.users.auth.authorization import authorize_user

from .common import authentication_exception
from .token import get_id_from_token
from app.users.schemas import User


def get_user_from_request(
    request: Request,
    id: Annotated[None | UUID, Depends(get_id_from_token)],
    api_key: Annotated[str | None, Header()] = None,
) -> User | None:
    user: User | None

    if api_key:
        user = request.state.user_cache.get_user_from_api_key(api_key)

        if not user:
            raise HTTPException(HTTP_401_UNAUTHORIZED, "Provided API key is invalid")
        if not authorize_user(user, ["api"]):
            raise HTTPException(
                HTTP_401_UNAUTHORIZED,
                "User attached to API key isn't authorized for api access",
            )

        return user

    if not id:
        return None

    user = request.state.user_cache.get_user_from_id(id)

    return user


def ensure_user_from_request(
    user: Annotated[User | None, Depends(get_user_from_request)]
) -> User:
    if not user:
        raise authentication_exception

    return user
