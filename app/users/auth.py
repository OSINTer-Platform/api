from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app import config_options
from app.utils.auth import OAuth2PasswordBearerWithCookie
from app.users.crud import get_full_user_object, verify_user
from app.users.schemas import User, UserBase

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


async def get_username_from_token(request: Request) -> str | None:
    token = await oauth2_scheme(request)

    if not token:
        return None

    try:
        payload = jwt.decode(
            token, config_options.SECRET_KEY, algorithms=config_options.JWT_ALGORITHMS
        )
        username: str | None = payload.get("sub")

        return username
    except JWTError:
        return None


def ensure_username_from_token(
    username: None | str = Depends(get_username_from_token),
) -> str:
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username


def verify_auth_data(
    username: str = Depends(ensure_username_from_token), password: str | None = None
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


def get_user_from_token(
    username: str = Depends(ensure_username_from_token),
) -> UserBase:
    return verify_auth_data(username)


def require_premium(user: UserBase = Depends(get_user_from_token)) -> None:
    if not user.premium > 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not a premium user",
        )


def get_full_user(username: str = Depends(ensure_username_from_token)) -> User:
    user_obj = get_full_user_object(username)

    if user_obj:
        return user_obj
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
