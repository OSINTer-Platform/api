from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from typing import Dict, List
from pydantic import conlist, constr

from enum import Enum

from ..auth import get_user_from_token

from ...users import User
from ...common import HTTPError
from ...dependencies import get_collection_IDs
from ...utils.documents import send_file, convert_ids_to_zip

from modules.objects import BaseArticle
from modules.elastic import searchQuery
from ... import config_options

from datetime import date

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
        422: {
            "model": HTTPError,
            "description": "Returned when user tries to delete either the Read Later or Already Read collection (not removable)",
        },
    },
)
def remove_existing_collection(
    collection_name: str, current_user: User = Depends(get_user_from_token)
):
    if collection_name == "Read Later" or collection_name == "Already Read":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'The "{collection_name}" collection cannot be remove',
        )

    if current_user.modify_collections("remove", collection_name):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found no collection with given name",
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
    if current_user.modify_collections(mod_action.value, collection_name, IDs=IDs):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found no collection with given name",
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
            detail="Found no collection with given name",
        )


@router.get(
    "/get-contents/{collection_name}",
    response_model=List[BaseArticle],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for collection doesn't match any feed for that user",
        },
    },
)
def get_collection_contents(
    collection_IDs: conlist(
        constr(strip_whitespace=True, min_length=20, max_length=20),
        unique_items=True,
    ) = Depends(get_collection_IDs),
):

    return config_options.esArticleClient.queryDocuments(
        searchQuery(limit=10_000, IDs=collection_IDs, complete=False)
    )["documents"]


@router.get(
    "/download/{collection_name}",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned either if supplied name doesn't match any collection for current user, or if no articles from the collection was found",
        },
    },
)
async def download_collection_contents(
    collection_name: str = Path(...),
    collection_IDs: conlist(
        constr(strip_whitespace=True, min_length=20, max_length=20),
        unique_items=True,
    ) = Depends(get_collection_IDs),
):
    return send_file(
        file_name=f"OSINTer-{collection_name.replace(' ', '-').replace('/', '-')}-articles-{date.today()}.zip",
        file_content=await convert_ids_to_zip(collection_IDs),
        file_type="application/zip",
    )
