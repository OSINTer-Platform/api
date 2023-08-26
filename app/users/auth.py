from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from .. import config_options
from ..utils.auth import OAuth2PasswordBearerWithCookie
from .crud import get_full_user_object, verify_user
from .schemas import User, UserBase

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


async def get_username_from_token(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, config_options.SECRET_KEY, algorithms=config_options.JWT_ALGORITHMS
        )
        username: str | None = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    return username


def verify_auth_data(
    username: str = Depends(get_username_from_token), password: str | None = None
) -> UserBase:
    user_obj = verify_user(username=username, password=password)

    if user_obj:
        return user_obj
    else:
        if password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )


def get_user_from_token(username: str = Depends(get_username_from_token)) -> UserBase:
    return verify_auth_data(username)


def get_full_user(username: str = Depends(get_username_from_token)) -> User:
    user_obj = get_full_user_object(username)

    if user_obj:
        return user_obj
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
