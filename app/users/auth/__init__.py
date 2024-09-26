from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Request

from .token import get_id_from_token
from app.users.schemas import User


authentication_exception = HTTPException(
    HTTP_401_UNAUTHORIZED,
    detail="User is not authorized",
    headers={"WWW-Authenticate": "Bearer"},
)

authorization_exception = HTTPException(
    HTTP_403_FORBIDDEN,
    detail="User doesn't have necessary permissions",
)


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
