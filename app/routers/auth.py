from datetime import UTC, datetime, timedelta
from typing import Literal
from typing_extensions import TypedDict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_422_UNPROCESSABLE_ENTITY
from app.users import schemas

from app.users.auth import (
    create_access_token,
    ensure_user_from_token,
)
from app.users.crud import check_username, create_user, verify_user
from app.users.schemas import User
from app.authorization import Area, levels_access

from .. import config_options
from ..common import DefaultResponse, DefaultResponseStatus, HTTPError
from ..utils.auth import SignupForm


router = APIRouter()


# Should also check whether mail server is active and available, once implemented
async def check_mail_available() -> bool:
    return config_options.EMAIL_SERVER_AVAILABLE


@router.get("/allowed-areas")
def get_allowed_areas() -> dict[str, list[Area]]:
    return levels_access


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
        current_user = schemas.User.model_validate(check_username(username=username))

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with that username wasn't found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            if verify_user(current_user.id, username=username, email=email):
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
    current_user: User = Depends(ensure_user_from_token),
) -> User:
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    _: User = Depends(ensure_user_from_token),
) -> None:
    response.delete_cookie(key="access_token")
    return


class TokenWithDetails(TypedDict):
    token: str
    max_age: int
    secure: bool


def get_token_from_form(
    form_data: OAuth2PasswordRequestForm = Depends(), remember_me: bool = False
) -> TokenWithDetails:
    user = check_username(form_data.username)

    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="User wasn't found"
        )

    if not verify_user(
        UUID(str(user._id)), user, form_data.username, form_data.password
    ):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Wrong username or password"
        )

    expire_date = timedelta(
        hours=(
            config_options.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS
            if remember_me
            else config_options.ACCESS_TOKEN_EXPIRE_HOURS
        )
    )

    access_token = create_access_token(
        data={"sub": user._id}, expires_delta=expire_date
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
    response: Response, token: TokenWithDetails = Depends(get_token_from_form)
) -> None:
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
    token: TokenWithDetails = Depends(get_token_from_form),
) -> TokenWithDetails:
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
    if (
        form_data.signup_code
        and form_data.signup_code not in config_options.SIGNUP_CODES
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A wrong signup code was entered",
        )
    user_premium = None
    if form_data.signup_code in config_options.SIGNUP_CODES:
        diff = datetime.now(UTC) + config_options.SIGNUP_CODES[form_data.signup_code]
        user_premium = schemas.UserPremium(
            status=True, expire_time=int(diff.timestamp())
        )

    if create_user(
        username=form_data.username,
        password=form_data.password,
        email=form_data.email,
        premium=user_premium,
    ):
        return DefaultResponse(status=DefaultResponseStatus.SUCCESS, msg="User created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists",
        )
