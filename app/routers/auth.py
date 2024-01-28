from datetime import timedelta
from typing import Literal
from typing_extensions import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from app.users.auth import (
    create_access_token,
    get_full_user,
    get_user_from_token,
    verify_auth_data,
)
from app.users.crud import create_user, verify_user
from app.users.schemas import User, UserBase

from .. import config_options
from ..common import DefaultResponse, DefaultResponseStatus, HTTPError
from ..utils.auth import SignupForm


router = APIRouter()


# Should also check whether mail server is active and available, once implemented
async def check_mail_available() -> bool:
    return config_options.EMAIL_SERVER_AVAILABLE


@router.get("/forgotten-password")
async def check_password_recovery_availability(
    mail_available: bool = Depends(check_mail_available),
) -> dict[Literal["available"], bool]:
    return {"available": mail_available}


@router.post(
    "/forgotten-password/send-mail/",
    response_model=DefaultResponse,
    responses={
        200: {"model": DefaultResponse},
        404: {
            "model": HTTPError,
            "description": "Returned when the username doesn't exist in DB",
        },
        405: {
            "model": HTTPError,
            "description": "Returned if password recovery by email isn't available",
        },
    },
)
async def send_password_recovery_mail(
    username: str, email: str, mail_available: bool = Depends(check_mail_available)
) -> DefaultResponse:
    if mail_available:
        current_user = verify_user(username=username)

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with that username wasn't found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            if verify_user(username=username, email=email):
                # This needs to send the recovery email, once implemented
                raise NotImplemented

    else:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Password recovery by email currently isn't supported",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return DefaultResponse(
        status=DefaultResponseStatus.SUCCESS,
        msg="Email sent, if address matches the one given on signup.",
    )


@router.get("/status")
async def get_auth_status(
    current_user: User = Depends(get_full_user),
) -> User:
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    _: UserBase = Depends(get_user_from_token),
) -> None:
    response.delete_cookie(key="access_token")
    return


class TokenWithDetails(TypedDict):
    token: str
    max_age: int
    secure: bool


def get_token_with_details(
    username: str, password: str, remember: bool
) -> TokenWithDetails:
    expire_date = timedelta(
        hours=config_options.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS
        if remember
        else config_options.ACCESS_TOKEN_EXPIRE_HOURS
    )
    user = verify_auth_data(username=username, password=password)

    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=expire_date
    )

    return {
        "token": access_token,
        "max_age": int(expire_date.total_seconds()),
        "secure": config_options.ENABLE_HTTPS,
    }


@router.post(
    "/login",
    responses={
        200: {},
        401: {
            "model": HTTPError,
            "description": "Returned when password doesn't match username",
        },
        404: {
            "model": HTTPError,
            "description": "Returned when username isn't found in DB",
        },
    },
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Query(False),
) -> None:
    token: TokenWithDetails = get_token_with_details(
        username=form_data.username, password=form_data.password, remember=remember_me
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {token['token']}",
        max_age=token["max_age"],
        httponly=True,
        samesite="strict",
        path="/",
        secure=token["secure"],
    )

    return None


@router.post(
    "/get-token",
    responses={
        200: {},
        401: {
            "model": HTTPError,
            "description": "Returned when password doesn't match username",
        },
        404: {
            "model": HTTPError,
            "description": "Returned when username isn't found in DB",
        },
    },
)
async def get_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Query(False),
) -> TokenWithDetails:
    token: TokenWithDetails = get_token_with_details(
        username=form_data.username, password=form_data.password, remember=remember_me
    )

    return token


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
async def signup(
    form_data: SignupForm = Depends(),
) -> DefaultResponse:
    if form_data.signup_code and config_options.SIGNUP_CODE != form_data.signup_code:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A wrong signup code was entered",
        )
    premium = (
        bool(config_options.SIGNUP_CODE)
        and config_options.SIGNUP_CODE == form_data.signup_code
    )
    if create_user(
        username=form_data.username,
        password=form_data.password,
        email=form_data.email,
        premium=1 if premium else 0,
    ):
        return DefaultResponse(status=DefaultResponseStatus.SUCCESS, msg="User created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists",
        )
