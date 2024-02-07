from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app import config_options
from app.utils.auth import OAuth2PasswordBearerWithCookie
from app.users.crud import get_full_user_object
from app.users.schemas import User

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
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


def ensure_id_from_token(
    id: None | UUID = Depends(get_id_from_token),
) -> UUID:
    if id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return id


def get_user_from_token(
    id: UUID = Depends(ensure_id_from_token),
) -> User:
    user = get_full_user_object(id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_auth_user_from_token(
    id: UUID = Depends(ensure_id_from_token),
) -> User:
    user = get_full_user_object(id, auth=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def check_premium(id: UUID | None = Depends(get_id_from_token)) -> bool:
    if not id:
        return False

    user = get_full_user_object(id)
    if not user:
        return False

    return user.premium > 0


def require_premium(premium: bool = Depends(check_premium)) -> None:
    if not premium:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not a premium user",
        )
