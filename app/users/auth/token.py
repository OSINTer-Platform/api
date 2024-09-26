from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Request
from jose import JWTError, jwt

from app import config_options
from app.utils.auth import OAuth2PasswordBearerWithCookie

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


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
