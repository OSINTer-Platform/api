from datetime import date
from enum import Enum
from typing import Dict, List

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)

from modules.elastic import SearchQuery
from modules.objects import BaseArticle

from ... import config_options
from ...common import EsIDList, HTTPError
from ...dependencies import get_collection_ids
from ...users import User
from ...utils.documents import convert_ids_to_zip, send_file
from ..auth import get_user_from_token

router = APIRouter()


@router.get("/list", response_model=Dict[str, List[str]])
def get_my_collections(current_user: User = Depends(get_user_from_token)):
    return current_user.get_collections()


@router.put(
    "/{collection_name}",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict[str, List[str]],
)
def create_new_collection(
    collection_name: str,
    current_user: User = Depends(get_user_from_token),
    ids: EsIDList = Body([]),
):
    current_user.modify_collections("add", collection_name, ids)
    return current_user.collections


@router.delete(
    "/{collection_name}",
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
    clear = "clear"


@router.post(
    "/{collection_name}/{mod_action}",
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
    ids: EsIDList = Query([]),
    current_user: User = Depends(get_user_from_token),
):
    if current_user.modify_collections(mod_action.value, collection_name, ids=ids):
        return current_user.collections
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found no collection with given name",
        )


@router.get(
    "/{collection_name}",
    response_model=List[BaseArticle],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when supplied name for collection doesn't match any feed for that user",
        },
    },
)
def get_collection_contents(
    collection_ids: EsIDList = Depends(get_collection_ids),
):

    return (
        config_options.es_article_client.query_documents(
            SearchQuery(limit=10_000, ids=collection_ids, complete=False)
        )
        if collection_ids
        else []
    )


@router.get(
    "/{collection_name}/export",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned either if supplied name doesn't match any collection for current user, or if no articles from the collection was found",
        },
        204: {
            "description": "Returned when collection is empty",
        },
    },
)
async def download_collection_contents(
    collection_name: str = Path(...),
    collection_ids: EsIDList = Depends(get_collection_ids),
):
    if not collection_ids:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return send_file(
        file_name=f"OSINTer-{collection_name.replace(' ', '-').replace('/', '-')}-articles-{date.today()}.zip",
        file_content=await convert_ids_to_zip(collection_ids),
        file_type="application/zip",
    )
