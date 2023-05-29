from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.users import models

from ...users import crud, schemas
from ...users.auth import get_full_user

router = APIRouter()


@router.get("/base-list", response_model=list[schemas.ItemBase])
def get_base_of_my_subscribed_feeds(
    current_user: schemas.User = Depends(get_full_user),
):
    return crud.get_feed_list(current_user)


@router.get("/list", response_model=dict[str, schemas.Feed])
def get_my_subscribed_feeds(
    current_user: schemas.User = Depends(get_full_user),
):
    return crud.get_feeds(current_user)


@router.post(
    "/{feed_name}",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, schemas.Feed],
)
def create_feed(
    feed_name: str,
    feed_params: schemas.FeedCreate,
    subscribe: bool = Query(True),
    current_user: schemas.User = Depends(get_full_user),
):
    feed: schemas.Feed = crud.create_feed(
        feed_params=feed_params, name=feed_name, owner=current_user.id
    )

    if subscribe:
        user_obj: models.User | None = crud.modify_user_subscription(
            user_id=current_user.id,
            ids={
                feed.id,
            },
            action="subscribe",
            item_type="feed",
        )

        if not user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user with id {current_user.id} found",
            )

        current_user = schemas.User.from_orm(user_obj)

    return crud.get_feeds(current_user)

@router.put("/subscription/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def subscribe_to_collection(
    feed_id: UUID,
    current_user: schemas.User = Depends(get_full_user),
):
    crud.modify_user_subscription(
        user_id=current_user.id, ids={feed_id}, action="subscribe", item_type="feed"
    )


@router.delete("/subscription/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_from_collection(
    feed_id: UUID,
    current_user: schemas.User = Depends(get_full_user),
):
    crud.modify_user_subscription(
        user_id=current_user.id, ids={feed_id}, action="unsubscribe", item_type="feed"
    )
