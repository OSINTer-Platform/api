from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.users.auth import create_access_token, verify_auth_data
from app.users.crud import create_user, verify_user
from app.users.schemas import UserBase

from .. import config_options
from ..common import DefaultResponse, DefaultResponseStatus, HTTPError
from ..utils.auth import OAuth2PasswordRequestFormWithEmail


router = APIRouter()


# Should also check whether mail server is active and available, once implemented
async def check_mail_available():
    return config_options.EMAIL_SERVER_AVAILABLE


@router.get("/forgotten-password")
async def check_password_recovery_availability(
    mail_available: bool = Depends(check_mail_available),
):
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
):

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
                pass

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
    current_user: UserBase = Depends(verify_auth_data),
):
    return


@router.post("/logout")
async def logout(
    response: Response,
    current_user: UserBase = Depends(verify_auth_data),
):
    response.delete_cookie(key="access_token")
    return


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
):
    user = verify_auth_data(username=form_data.username, password=form_data.password)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(hours=config_options.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS)
        if remember_me
        else None,
    )

    cookie_options = {
        "key": "access_token",
        "value": f"Bearer {access_token}",
        "httponly": True,
        "samesite": "strict",
        "path": "/",
        "secure": config_options.ENABLE_HTTPS,
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
    if create_user(
        username=form_data.username, password=form_data.password, email=form_data.email
    ):
        return DefaultResponse(status=DefaultResponseStatus.SUCCESS, msg="User created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists",
        )
