from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...common import HTTPError
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
        crud.modify_user_subscription(
            user_id=current_user.id,
            ids={feed.id,},
            action="subscribe",
            item_type="feed"
        )

    return crud.get_feeds(current_user)


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
def delete_feed(
    feed_id: UUID, current_user: schemas.User = Depends(get_full_user)
):
    if crud.remove_item(current_user, feed_id, "feed"):
        return crud.get_feeds(current_user)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No feed with that name owned by you found",
        )
