from fastapi import APIRouter, Depends, HTTPException, status

from typing import List

from ..auth import get_user_from_token

from ...users import User, Feed
from ...common import DefaultResponse, DefaultResponseStatus, HTTPError

router = APIRouter()


@router.get("/list", response_model=List[Feed])
def get_my_feeds(current_user: User = Depends(get_user_from_token)):
    return current_user.get_feeds()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=List[Feed],
    responses={
        409: {
            "model": HTTPError,
            "description": "Returned when feed with supplied name already exists",
        }
    },
)
def create_new_feed(feed: Feed, current_user: User = Depends(get_user_from_token)):
    if current_user.create_feed(feed):

        current_user_feeds = current_user.get_feeds()
        current_user_feeds.append(feed)

        return current_user_feeds
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feed with that name already exists",
        )
