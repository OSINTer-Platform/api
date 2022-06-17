from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from fastapi.security import OAuth2, OAuth2PasswordRequestForm

from typing import Optional

from jose import JWTError, jwt
from datetime import datetime, timedelta

from ..users import create_user, User
from ..common import DefaultResponse, DefaultResponseStatus, HTTPError

from ..utils.auth import (
    OAuth2PasswordBearerWithCookie,
    OAuth2PasswordRequestFormWithEmail,
)

from .. import config_options

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
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


def get_user_from_username(username: str):
    return User(
        username=username,
        index_name=config_options.ELASTICSEARCH_USER_INDEX,
        es_conn=config_options.es_conn,
    )


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
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user: User = get_user_from_username(username=username)

    if not user.user_exist():
        raise credentials_exception

    return user


# Should also check whether mail server is active and available, once implemented
async def check_mail_available():
    return config_options.EMAIL_SERVER_AVAILABLE


@router.get("/forgotten-password")
async def check_password_recovery_availability(
    mail_available: bool = Depends(check_mail_available),
):
    return {"available": mail_available}


@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_user_from_token)):
    response.delete_cookie(key="access_token")
    return


@router.post(
    "/login",
    responses={
        200: {},
        401: {
            "model": HTTPError,
            "description": "Returned when the username exist in DB but doesn't match the password",
        },
        404: {
            "model": HTTPError,
            "description": "Returned when the username doesn't exist in DB",
        },
    },
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Query(False),
):
    current_user = get_user_from_username(form_data.username)
    if not current_user.user_exist():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that username wasn't found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not current_user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=timedelta(days=30) if remember_me else None,
    )

    cookie_options = {
        "key": "access_token",
        "value": f"Bearer {access_token}",
        "httponly": True,
        "samesite": "strict",
        "path": "/",
        "secure": config_options.HTTPS,
    }

    if remember_me:
        cookie_options["max_age"] = timedelta(
            hours=config_options.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS
        ).total_seconds()

    response.set_cookie(**cookie_options)

    return {}


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
    responses={
        201: {"msg": "User created"},
        409: {
            "model": HTTPError,
            "description": "Returned when the username already exist in DB",
        },
    },
)
async def signup(form_data: OAuth2PasswordRequestFormWithEmail = Depends()):
    current_user = get_user_from_username(form_data.username)
    if create_user(current_user, form_data.password, form_data.email):
        return DefaultResponse(status=DefaultResponseStatus.SUCCESS, msg="User created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists",
        )
