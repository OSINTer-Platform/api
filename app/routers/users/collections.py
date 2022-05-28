from fastapi import APIRouter, Depends, HTTPException, status, Query

from typing import Dict, List
from pydantic import conlist, constr

from enum import Enum

from ..auth import get_user_from_token

from ...users import User
from ...common import HTTPError

router = APIRouter()


@router.get("/list", response_model=Dict[str, List[str]])
def get_my_collections(current_user: User = Depends(get_user_from_token)):
    return current_user.get_collections()


@router.post(
    "/create/{collection_name}",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict[str, List[str]],
    responses={
        409: {
            "model": HTTPError,
            "description": "Returned when collection with the supplied name already exist",
        }
    },
)
def create_new_collection(
    collection_name: str, current_user: User = Depends(get_user_from_token)
):
    if current_user.modify_collections("add", collection_name):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection with that name already exists",
        )


@router.delete(
    "/remove/{collection_name}",
    response_model=Dict[str, List[str]],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for collection doesn't match any feed for that user",
        },
        422 : {
            "model" : HTTPError,
            "description" : "Returned when user tries to delete Read Later collection (not removable)"
        }
    },
)
def remove_existing_collection(
    collection_name: str, current_user: User = Depends(get_user_from_token)
):
    if collection_name == "Read Later":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='The "Read Later" collection cannot be remove',
        )

    if current_user.modify_collections("remove", collection_name):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collection with that name found",
        )


class ModAction(str, Enum):
    extend = "extend"
    subtract = "subtract"


@router.post(
    "/modify/{collection_name}/{mod_action}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, List[str]],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for collection doesn't match any feed for that user",
        }
    },
)
def modify_collection(
    collection_name: str,
    mod_action: ModAction,
    IDs: conlist(constr(strip_whitespace=True, min_length=20, max_length=20)) = Query(
        ...
    ),
    current_user: User = Depends(get_user_from_token),
):
    if current_user.modify_collections(mod_action.value, collection_name, IDs = IDs):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collection with that name found",
        )


@router.post(
    "/clear/{collection_name}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, List[str]],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for collection doesn't match any feed for that user",
        }
    },
)
def clear_collection(
    collection_name: str,
    current_user: User = Depends(get_user_from_token),
):
    if current_user.modify_collections("clear", collection_name):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collection with that name found",
        )
