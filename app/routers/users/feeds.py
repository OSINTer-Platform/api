from fastapi import APIRouter, Depends, HTTPException, status

from typing import List

from ..auth import get_user_from_token

from ...users import User, Feed
from ...common import HTTPError

router = APIRouter()


@router.get("/list", response_model=List[Feed])
def get_my_feeds(current_user: User = Depends(get_user_from_token)):
    return current_user.get_feeds()


@router.put(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=List[Feed],
)
def create_new_feed(feed: Feed, current_user: User = Depends(get_user_from_token)):
    return current_user.update_feed_list(feed=feed)


@router.delete(
    "/remove",
    status_code=status.HTTP_200_OK,
    response_model=List[Feed],
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
    if current_user.update_feed_list(feed_name=feed_name):
        return current_user._serialize_feeds()
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feed with that name found",
        )
