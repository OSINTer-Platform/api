from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from .. import config_options
from ..utils.auth import OAuth2PasswordBearerWithCookie
from .crud import verify_user
from .schemas import UserBase

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            hours=config_options.ACCESS_TOKEN_EXPIRE_HOURS
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config_options.SECRET_KEY, algorithm=config_options.JWT_ALGORITHMS[0]
    )
    return encoded_jwt


async def get_user_from_token(token: str = Depends(oauth2_scheme)):
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

    user: UserBase | None = verify_user(username)

    if not isinstance(user, UserBase):
        raise credentials_exception

    return user
