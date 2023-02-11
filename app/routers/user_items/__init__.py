from typing import Any
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


responses: dict[int, dict[str, Any]] = {
    404: {
        "model": HTTPError,
        "description": "Returned when item doesn't already exist",
        "detail": "No item with that ID found",
        "status_code": status.HTTP_404_NOT_FOUND,
    },
    403: {
        "model": HTTPError,
        "description": "Returned when the user doesn't own that item",
        "detail": "The requested item isn't owned by the authenticated user",
        "status_code": status.HTTP_403_FORBIDDEN,
    },
}


def update_item(
    item_id: UUID,
    contents: schemas.FeedCreate | set[UUID],
    current_user: schemas.UserBase,
):
    if isinstance(contents, schemas.FeedCreate):
        response_code: int | None = crud.modify_feed(
            id=item_id, contents=contents, user=current_user
        )
    elif isinstance(contents, set):
        response_code: int | None = crud.modify_collection(
            id=item_id, contents=contents, user=current_user
        )
    else:
        raise NotImplementedError

    if response_code:
        raise HTTPException(
            status_code=responses[response_code]["status_code"],
            detail=responses[response_code]["detail"],
        )


@router.put("/feed/{feed_id}", responses=responses)  # pyright: ignore
def update_feed(
    feed_id: UUID,
    contents: schemas.FeedCreate,
    current_user: schemas.User = Depends(get_user_from_token),
):
    update_item(feed_id, contents, current_user)


@router.put("/collection/{collection_id}", responses=responses)  # pyright: ignore
def update_collection(
    collection_id: UUID,
    contents: set[UUID],
    current_user: schemas.User = Depends(get_user_from_token),
):
    update_item(collection_id, contents, current_user)
