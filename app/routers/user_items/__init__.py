from datetime import date
from io import BytesIO
from typing import Annotated, cast
from uuid import UUID

import couchdb
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from app.authorization import UserAuthorizer
from app.common import EsIDList
from app.dependencies import FastapiArticleSearchQuery
from app.users import crud, models, schemas
from app.users.auth import ensure_user_from_request
from app.utils.documents import convert_article_query_to_zip, send_file
from modules.objects import BaseArticle, FullArticle

from ... import config_options
from . import webhooks
from .utils import (
    responses,
    handle_crud_response,
    get_query_from_item,
    get_own_feed,
    update_last_article,
)

ArticleAuthorizer = UserAuthorizer(["articles"])

router = APIRouter()
router.include_router(webhooks.router, tags=["webhooks"], prefix="/webhook")


@router.delete(
    "/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=responses
)
def delete_item(
    item_id: UUID, current_user: schemas.User = Depends(ensure_user_from_request)
) -> None:
    def remove_webhook_attachments(feed: schemas.Feed) -> None:
        webhooks = [
            schemas.Webhook.model_validate(webhook)
            for webhook in models.Webhook.by_feed(config_options.couch_conn)[
                str(feed.id)
            ]
        ]

        if len(webhooks) == 0:
            return

        for webhook in webhooks:
            try:
                webhook.attached_feeds.remove(feed.id)
            except KeyError:
                pass

        config_options.couch_conn.update(
            [webhook.db_serialize() for webhook in webhooks]
        )

    item = crud.get_item(item_id)
    if isinstance(item, int):
        handle_crud_response(item)

    if item.owner != current_user.id:
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            detail="The requested item isn't owned by the authenticated user",
        )

    if isinstance(item, schemas.Feed | schemas.Collection) and not item.deleteable:
        raise HTTPException(
            HTTP_403_FORBIDDEN, detail="The requested item cannot be deleted"
        )

    if isinstance(item, schemas.Feed):
        remove_webhook_attachments(item)

    try:
        del config_options.couch_conn[str(item_id)]
    except couchdb.http.ResourceNotFound:
        raise HTTPException(HTTP_404_NOT_FOUND, "The requested item was not found")


@router.get(
    "/{item_id}/articles",
    response_model_exclude_unset=True,
    dependencies=[Depends(ArticleAuthorizer)],
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
def get_item_contents(item_id: UUID) -> schemas.FeedItemBase:
    return handle_crud_response(crud.get_item(item_id, ("feed", "collection")))


@router.get(
    "/{item_id}/export",
    response_model_exclude_unset=True,
    dependencies=[Depends(ArticleAuthorizer)],
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
    current_user: schemas.User = Depends(ensure_user_from_request),
) -> schemas.Feed | schemas.Collection:
    item: int | schemas.Feed | schemas.Collection = crud.change_item_name(
        item_id, new_name, current_user
    )
    r = cast(schemas.Feed | schemas.Collection, handle_crud_response(item))
    return r


@router.put("/feed/{feed_id}", responses=responses)
def update_feed(
    feed: Annotated[schemas.Feed, Depends(get_own_feed)],
    contents: schemas.FeedCreate,
) -> schemas.Feed:
    specified_contents = contents.model_dump(exclude_unset=True)

    webhooks = [
        schemas.Webhook.model_validate(webhook)
        for webhook in models.Webhook.by_feed(config_options.couch_conn)[str(feed.id)]
    ]

    if (
        len(webhooks) > 0
        and "sort_order" in specified_contents
        and specified_contents["sort_order"] != "desc"
    ):
        raise HTTPException(
            HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change sort_order with webhook(s) attached",
        )

    if (
        len(webhooks) > 0
        and "sort_by" in specified_contents
        and specified_contents["sort_by"] != "publish_date"
    ):
        raise HTTPException(
            HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change sort_by with webhook(s) attached",
        )

    for k, v in specified_contents.items():
        setattr(feed, k, v)

    if len(webhooks) > 0:
        feed = update_last_article(feed)

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()

    return feed


@router.put(
    "/collection/{collection_id}",
    responses=responses,
)
def update_collection(
    collection_id: UUID,
    contents: EsIDList,
    current_user: schemas.User = Depends(ensure_user_from_request),
) -> schemas.Collection:
    return handle_crud_response(
        crud.modify_collection(id=collection_id, contents=contents, user=current_user)
    )
