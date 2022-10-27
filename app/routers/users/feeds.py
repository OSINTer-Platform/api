from fastapi import APIRouter, Depends, HTTPException, status

from typing import Dict

from ..auth import get_user_from_token

from ...users import User, Feed
from ...common import HTTPError

router = APIRouter()


@router.get("/list", response_model=Dict[str, Feed])
def get_my_feeds(current_user: User = Depends(get_user_from_token)):
    return current_user.get_feeds()


@router.put(
    "/{feed_name}",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict[str, Feed],
)
def create_new_feed(
    feed_name: str, feed: Feed, current_user: User = Depends(get_user_from_token)
):
    feeds = current_user.update_feed_list(feed_name, feed)
    return feeds


@router.delete(
    "/{feed_name}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Feed],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for feed doesn't match any feed for that user.",
        }
    },
)
def remove_existing_feed(
    feed_name: str, current_user: User = Depends(get_user_from_token)
):
    if current_user.update_feed_list(feed_name) is not None:
        return current_user.feeds
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feed with that name found",
        )
