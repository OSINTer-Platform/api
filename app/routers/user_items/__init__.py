from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.common import HTTPError
from app.users import crud, schemas
from app.users.auth import verify_auth_data


router = APIRouter()


@router.delete(
    "/{feed_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {
            "model": HTTPError,
            "description": "Returned when user doesn't own that feed",
        },
    },
)
def delete_feed(
    feed_id: UUID, current_user: schemas.UserBase = Depends(verify_auth_data)
):
    if crud.remove_item(current_user, feed_id):
        return
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No feed with that name owned by you found",
        )
