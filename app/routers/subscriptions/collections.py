from typing import cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.common import EsIDList
from app.users.auth import ensure_user_from_token

from ...users import crud, schemas

router = APIRouter()


@router.get("/list")
def get_my_subscribed_collections(
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> dict[str, schemas.Collection]:
    return crud.get_collections(current_user)


@router.post(
    "/{collection_name}",
    status_code=status.HTTP_201_CREATED,
)
def create_collection(
    collection_name: str,
    ids: EsIDList = Body(set()),
    subscribe: bool = Query(True),
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> schemas.Collection:
    collection: schemas.Collection = crud.create_collection(
        name=collection_name, owner=current_user.id, ids=cast(set[str], ids)
    )

    if subscribe:
        user_obj: schemas.User | None = crud.modify_user_subscription(
            user_id=current_user.id,
            ids=[
                collection.id,
            ],
            action="subscribe",
            item_type="collection",
        )

        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user with id {current_user.id} found",
            )

    return collection


@router.put("/subscription/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def subscribe_to_collection(
    collection_id: UUID,
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> None:
    crud.modify_user_subscription(
        user_id=current_user.id,
        ids=[collection_id],
        action="subscribe",
        item_type="collection",
    )


@router.delete("/subscription/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_from_collection(
    collection_id: UUID,
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> None:
    crud.modify_user_subscription(
        user_id=current_user.id,
        ids=[collection_id],
        action="unsubscribe",
        item_type="collection",
    )
