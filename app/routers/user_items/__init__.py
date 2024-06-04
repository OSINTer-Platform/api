from datetime import date
from io import BytesIO
from typing import Annotated
from typing_extensions import Any, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.common import EsIDList, HTTPError
from app.dependencies import FastapiArticleSearchQuery
from app.authorization import get_source_exclusions
from app.users import crud, schemas
from app.users.auth import ensure_user_from_token
from app.utils.documents import convert_article_query_to_zip, send_file
from modules.objects import BaseArticle, FullArticle

from ... import config_options
from .utils import (
    responses,
    handle_crud_response,
    get_query_from_item,
)


router = APIRouter()


@router.delete(
    "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=responses
)
def delete_item(
    item_id: UUID, current_user: schemas.User = Depends(ensure_user_from_token)
) -> None:
    return handle_crud_response(crud.remove_item(current_user, item_id))


@router.get(
    "/{item_id}/articles",
    response_model_exclude_unset=True,
)
def get_item_articles(
    search_query: FastapiArticleSearchQuery = Depends(get_query_from_item),
    complete: bool = Query(False),
) -> list[BaseArticle] | list[FullArticle]:
    return config_options.es_article_client.query_documents(search_query, complete)[0]


@router.get(
    "/{item_id}/content",
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
    response_model=schemas.UserItem,
)
def get_item_contents(item_id: UUID) -> schemas.ItemBase:
    return handle_crud_response(crud.get_item(item_id, ("feed", "collection")))


@router.get(
    "/{item_id}/export",
    response_model_exclude_unset=True,
)
def export_item_articles(
    search_query: FastapiArticleSearchQuery = Depends(get_query_from_item),
) -> StreamingResponse:
    zip_file: BytesIO = convert_article_query_to_zip(search_query)

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Item-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@router.put("/{item_id}/name", responses=responses)
def update_item_name(
    item_id: UUID,
    new_name: str,
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> None:
    return handle_crud_response(crud.change_item_name(item_id, new_name, current_user))


@router.put("/feed/{feed_id}", responses=responses)
def update_feed(
    feed_id: UUID,
    contents: schemas.FeedCreate,
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> schemas.Feed:
    return handle_crud_response(
        crud.modify_feed(id=feed_id, contents=contents, user=current_user)
    )


@router.put(
    "/collection/{collection_id}",
    responses=responses,
)
def update_collection(
    collection_id: UUID,
    contents: EsIDList,
    current_user: schemas.User = Depends(ensure_user_from_token),
) -> schemas.Collection:
    return handle_crud_response(
        crud.modify_collection(id=collection_id, contents=contents, user=current_user)
    )
