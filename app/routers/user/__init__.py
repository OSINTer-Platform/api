from typing import Literal, cast
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from app.users import schemas

from app.users.auth import (
    ensure_id_from_token,
    get_auth_user_from_token,
    get_user_from_token,
)
from app.users.crud import check_username, update_user, verify_user
from app import config_options

router = APIRouter()


@router.get("/")
async def get_auth_status(
    current_user: schemas.User = Depends(get_user_from_token),
) -> schemas.User:
    return current_user


@router.post("/credentials")
def change_credentials(
    id: UUID = Depends(ensure_id_from_token),
    password: str = Body(...),
    new_username: str | None = Body(None),
    new_password: str | None = Body(None),
    new_email: str | None = Body(None),
) -> schemas.User:
    user = verify_user(id, password=password)
    if not user or not user.rev:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    rev = cast(str, user.rev)
    user_schema = schemas.AuthUser.model_validate(user)

    if new_username:
        if check_username(new_username):
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Username is already taken",
            )
        user_schema.username = new_username

    if new_password:
        user_schema.hashed_password = config_options.hasher.hash(new_password)
    if new_email:
        user_schema.hashed_email = config_options.hasher.hash(new_email)

    update_user(user_schema, rev)

    return user_schema


@router.post("/settings")
def change_settings(
    settings: schemas.PartialUserSettings,
    user: schemas.User = Depends(get_auth_user_from_token),
) -> schemas.User:
    user.settings = user.settings.model_copy(
        update=settings.model_dump(exclude_unset=True)
    )
    update_user(user)
    return user


@router.post("/signup-code")
def submit_signup_code(
    code: dict[Literal["code"], str] = Body(),
    user: schemas.User = Depends(get_auth_user_from_token),
) -> schemas.User:
    if user.premium > 0:
        return user

    premium = (
        bool(config_options.SIGNUP_CODE) and config_options.SIGNUP_CODE == code["code"]
    )

    if premium:
        user.premium = 1
    else:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A wrong signup code was entered",
        )

    update_user(user)
    return user
