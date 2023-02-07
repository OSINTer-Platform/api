from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.common import HTTPError
from app.users import crud, schemas
from app.users.auth import get_user_from_token


router = APIRouter()


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {
            "model": HTTPError,
            "description": "Returned when user doesn't own that item",
        },
    },
)
def delete_item(
    item_id: UUID, current_user: schemas.UserBase = Depends(get_user_from_token)
):
    if crud.remove_item(current_user, item_id):
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No item with that name owned by you found",
        )
