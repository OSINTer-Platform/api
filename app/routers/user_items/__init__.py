from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.common import EsID, HTTPError
from app.users import crud, schemas
from app.users.auth import get_user_from_token


router = APIRouter()


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


def handle_crud_response(response_code: int | None):
    if response_code:
        raise HTTPException(
            status_code=responses[response_code]["status_code"],
            detail=responses[response_code]["detail"],
        )


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
    return handle_crud_response(crud.remove_item(current_user, item_id))


@router.put("/{item_id}/name", responses=responses)  # pyright: ignore
def update_item_name(
    item_id: UUID,
    new_name: str,
    current_user: schemas.User = Depends(get_user_from_token),
):
    crud.change_item_name(item_id, new_name, current_user)


@router.put("/feed/{feed_id}", responses=responses)  # pyright: ignore
def update_feed(
    feed_id: UUID,
    contents: schemas.FeedCreate,
    current_user: schemas.User = Depends(get_user_from_token),
):
    return handle_crud_response(
        crud.modify_feed(id=feed_id, contents=contents, user=current_user)
    )


@router.put("/collection/{collection_id}", responses=responses)  # pyright: ignore
def update_collection(
    collection_id: UUID,
    contents: set[EsID],
    current_user: schemas.User = Depends(get_user_from_token),
):
    return handle_crud_response(
        crud.modify_collection(
            id=collection_id, contents=cast(set[str], contents), user=current_user
        )
    )
