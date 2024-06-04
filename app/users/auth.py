from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app import config_options
from app.utils.auth import OAuth2PasswordBearerWithCookie
from app.users.schemas import AuthUser, User

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


authentication_exception = HTTPException(
    HTTP_401_UNAUTHORIZED,
    detail="User is not authorized",
    headers={"WWW-Authenticate": "Bearer"},
)

authorization_exception = HTTPException(
    HTTP_403_FORBIDDEN,
    detail="User doesn't have necessary permissions",
)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            hours=config_options.ACCESS_TOKEN_EXPIRE_HOURS
        )
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(
        to_encode, config_options.SECRET_KEY, algorithm=config_options.JWT_ALGORITHMS[0]
    )
    return encoded_jwt


async def get_id_from_token(request: Request) -> UUID | None:
    token = await oauth2_scheme(request)

    if not token:
        return None

    try:
        payload = jwt.decode(
            token, config_options.SECRET_KEY, algorithms=config_options.JWT_ALGORITHMS
        )
        id: str | None = payload.get("sub")

        if id:
            return UUID(id)
        else:
            return None

    except JWTError:
        return None


def get_user_from_token(
    request: Request, id: Annotated[None | UUID, Depends(get_id_from_token)]
) -> User | None:
    if not id:
        return None

    try:
        return ensure_user_from_token(request, id)
    except:
        return None


def ensure_user_from_token(
    request: Request, id: Annotated[UUID | None, Depends(get_id_from_token)]
) -> User:
    if not id:
        raise authentication_exception

    user = cast(User | None, request.state.user_cache.get_user(id))
    if user:
        return user
    else:
        raise authentication_exception


def ensure_auth_user_from_token(
    request: Request, id: Annotated[UUID | None, Depends(get_id_from_token)]
) -> User:
    if not id:
        raise authentication_exception

    user = request.state.user_cache.get_auth_user(id)

    if not user:
        raise authentication_exception
    return cast(AuthUser, user)
