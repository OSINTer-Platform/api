from datetime import UTC, datetime
from typing import Annotated, Literal, cast
from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import SecretStr
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from app.secrets import hash_value
from app.users import schemas

from app.users.auth import (
    get_id_from_token,
    ensure_auth_user_from_token,
    ensure_user_from_token,
)
from app.users.crud import check_username, update_user, verify_user
from app import config_options
from app.users.auth import authentication_exception

from .payment import router as payment_router

router = APIRouter()
router.include_router(payment_router, tags=["payment"])


@router.get("/")
async def get_auth_status(
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> schemas.User:
    return current_user


@router.post("/credentials")
def change_credentials(
    id: UUID | None = Depends(get_id_from_token),
    password: str = Body(...),
    new_username: str | None = Body(None),
    new_password: str | None = Body(None),
    new_email: str | None = Body(None),
) -> schemas.User:
    if not id:
        raise authentication_exception
    user = verify_user(id, password=password)
    if not user:
        raise authentication_exception

    user_schema = schemas.User.model_validate(user)

    if new_username:
        if check_username(new_username):
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="Username is already taken",
            )
        user_schema.username = new_username

    if new_password:
        user_schema.hashed_password = hash_value(new_password)
    if new_email:
        user_schema.hashed_email = hash_value(new_email)

    update_user(user_schema)

    return user_schema


@router.post("/settings")
def change_settings(
    settings: schemas.PartialUserSettings,
    user: schemas.User = Depends(ensure_auth_user_from_token),
) -> schemas.User:
    user.settings = user.settings.model_copy(
        update=settings.model_dump(exclude_unset=True)
    )
    update_user(user)
    return user


@router.post("/signup-code")
def submit_signup_code(
    code: dict[Literal["code"], str] = Body(),
    user: schemas.User = Depends(ensure_auth_user_from_token),
) -> schemas.User:
    if user.premium.status:
        return user

    if code["code"] in config_options.SIGNUP_CODES:
        diff = datetime.now(UTC) + config_options.SIGNUP_CODES[code["code"]]
        user.premium.status = True
        user.premium.expire_time = int(diff.timestamp())
    else:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A wrong signup code was entered",
        )

    update_user(user)
    return user


@router.post("/acknowledge-premium")
def acknowledge_premium(
    user: Annotated[schemas.User, Depends(ensure_user_from_token)],
    field: Annotated[str, Body()],
    status: Annotated[bool, Body()],
) -> schemas.User:
    user.premium.acknowledged[field] = status
    update_user(user)
    return user


@router.put("/read-articles")
def update_read_articles(
    user: Annotated[schemas.User, Depends(ensure_user_from_token)],
    article_ids: Annotated[list[str], Body()],
) -> schemas.User:
    user.read_articles = article_ids
    update_user(user)
    return user
