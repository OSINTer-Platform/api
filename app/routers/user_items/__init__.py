from datetime import date
from io import BytesIO
from typing_extensions import Any, TypeVar
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.common import EsIDList, HTTPError
from app.users import crud, schemas
from app.users.auth import get_user_from_token
from app.utils.documents import convert_query_to_zip, send_file
from modules.elastic import ArticleSearchQuery
from modules.objects import BaseArticle, FullArticle

from ... import config_options


router = APIRouter()


responses: dict[int | str, dict[str, Any]] = {
    404: {
        "model": HTTPError,
        "description": "Returned when item doesn't already exist",
        "detail": "No item with that ID found",
        "status_code": status.HTTP_404_NOT_FOUND,
    },
    403: {
        "model": HTTPError,
        "description": "Returned when the user doesn't own that item",
        "detail": "The requested item isn't owned by the authenticated user",
        "status_code": status.HTTP_403_FORBIDDEN,
    },
    422: {
        "model": HTTPError,
        "description": "Returned when user tries to delete items that are not deleteable",
        "detail": "The specified feed or collection is marked as non-deleteable",
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
    },
}


R = TypeVar("R")


def handle_crud_response(response: R | int) -> R:
    if isinstance(response, int):
        raise HTTPException(
            status_code=responses[response]["status_code"],
            detail=responses[response]["detail"],
        )

    return response


def get_query_from_item(item_id: UUID) -> ArticleSearchQuery | None:
    item: schemas.Feed | schemas.Collection | int = crud.get_item(item_id)

    if isinstance(item, int):
        handle_crud_response(item)
        return None

    elif not isinstance(item, schemas.Feed | schemas.Collection):
        handle_crud_response(404)
        return None

    q = item.to_query()

    return q


@router.delete(
    "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=responses
)
def delete_item(
    item_id: UUID, current_user: schemas.UserBase = Depends(get_user_from_token)
) -> None:
    return handle_crud_response(crud.remove_item(current_user, item_id))


@router.get(
    "/{item_id}/articles",
    response_model_exclude_unset=True,
)
def get_item_articles(
    search_query: ArticleSearchQuery = Depends(get_query_from_item),
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
    return handle_crud_response(crud.get_item(item_id))


@router.get(
    "/{item_id}/export",
    response_model_exclude_unset=True,
)
def export_item_articles(
    search_query: ArticleSearchQuery = Depends(get_query_from_item),
) -> StreamingResponse:
    zip_file: BytesIO = convert_query_to_zip(search_query)

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Item-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@router.put("/{item_id}/name", responses=responses)
def update_item_name(
    item_id: UUID,
    new_name: str,
    current_user: schemas.UserBase = Depends(get_user_from_token),
) -> None:
    return handle_crud_response(crud.change_item_name(item_id, new_name, current_user))


@router.put("/feed/{feed_id}", responses=responses)
def update_feed(
    feed_id: UUID,
    contents: schemas.FeedCreate,
    current_user: schemas.UserBase = Depends(get_user_from_token),
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
    current_user: schemas.UserBase = Depends(get_user_from_token),
) -> schemas.Collection:
    return handle_crud_response(
        crud.modify_collection(id=collection_id, contents=contents, user=current_user)
    )


@router.get(
    "/standard/feeds",
    response_model_exclude_none=True,
)
def get_standard_items() -> dict[str, schemas.Feed]:
    standard_user: schemas.User = cast(
        schemas.User, crud.get_full_user_object("OSINTer")
    )
    return crud.get_feeds(standard_user)
