from fastapi import APIRouter, Depends, HTTPException, status

from typing import List

from ..auth import get_user_from_token

from ...users import User, Feed
from ...common import DefaultResponse, DefaultResponseStatus

router = APIRouter(
            dependencies=[Depends(get_user_from_token)]
        )

@router.get("/list", response_model = List[Feed])
def get_my_feeds(current_user: User = Depends(get_user_from_token)):
    return current_user.get_feeds()

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model = DefaultResponse)
def create_new_feed(feed: Feed, current_user: User = Depends(get_user_from_token)):
    if current_user.create_feed(feed):
        return DefaultResponse(DefaultResponseStatus.SUCCESS, "Field created")
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Field with that name already exists"
        )


