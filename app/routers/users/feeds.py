from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_user_from_token

from ...users import User, Feed

router = APIRouter(
            dependencies=[Depends(get_user_from_token)]
        )

@router.get("/list")
def get_my_feeds(current_user: User = Depends(get_user_from_token)):
    return current_user.get_feeds()

@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_new_feed(feed: Feed, current_user: User = Depends(get_user_from_token)):
    if current_user.create_feed(feed):
        return {"status" : "success", "msg" : "Field created"}
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Field with that name already exists"
        )


