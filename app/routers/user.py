from uuid import UUID
from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED
from app.users import schemas

from app.users.auth import ensure_id_from_token
from app.users.crud import update_user, verify_user

router = APIRouter()


@router.post("/credentials")
def change_credentials(
    id: UUID = Depends(ensure_id_from_token),
    password: str = Body(...),
    new_username: str | None = Body(None),
    new_password: str | None = Body(None),
    new_email: str | None = Body(None),
) -> schemas.User:
    user = verify_user(id, password=password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    updated_response = update_user(id, new_username, new_password, new_email)

    if isinstance(updated_response, tuple):
        raise HTTPException(status_code=updated_response[0], detail=updated_response[1])

    return updated_response
