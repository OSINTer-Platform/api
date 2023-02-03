from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.common import HTTPError
from app.users import crud, schemas
from app.users.auth import get_full_user


router = APIRouter()


@router.delete(
    "/{feed_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, schemas.Feed],
    responses={
        403: {
            "model": HTTPError,
            "description": "Returned when user doesn't own that feed",
        },
    },
)
def delete_feed(feed_id: UUID, current_user: schemas.User = Depends(get_full_user)):
    if crud.remove_item(current_user, feed_id):
        return crud.get_feeds(current_user)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No feed with that name owned by you found",
        )
