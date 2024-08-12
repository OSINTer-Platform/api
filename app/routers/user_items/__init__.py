from datetime import date
from io import BytesIO
from typing import Annotated, cast
from uuid import UUID

from couchdb.client import ViewResults
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_403_FORBIDDEN

from app.authorization import UserAuthorizer, WebhookLimits, get_webhook_limits
from app.common import EsIDList
from app.dependencies import FastapiArticleSearchQuery
from app.users import crud, models, schemas
from app.users.auth import ensure_user_from_token
from app.utils.documents import convert_article_query_to_zip, send_file
from modules.objects import BaseArticle, FullArticle

from ... import config_options
from . import webhooks
from .utils import (
    responses,
    handle_crud_response,
    get_query_from_item,
    get_own_feed,
    get_own_webhook,
    update_last_article,
)

ArticleAuthorizer = UserAuthorizer(["articles"])

router = APIRouter()
router.include_router(webhooks.router, tags=["webhooks"], prefix="/webhook")


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
def get_item_contents(item_id: UUID) -> schemas.ItemBase:
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
    current_user: schemas.User = Depends(ensure_user_from_token),
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

    for k, v in contents.model_dump(exclude_unset=True).items():
        setattr(feed, k, v)

    if len(feed.webhooks.hooks) > 0:
        feed = update_last_article(feed)

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()

    return feed


@router.put("/feed/{feed_id}/webhook", responses=responses, tags=["webhooks"])
def add_webhook_to_feed(
    feed: Annotated[schemas.Feed, Depends(get_own_feed)],
    webhook: Annotated[schemas.Webhook, Depends(get_own_webhook)],
    webhook_limits: Annotated[WebhookLimits, Depends(get_webhook_limits)],
) -> schemas.Feed:
    if webhook.id in feed.webhooks.hooks:
        return feed

    webhook_feeds_view: ViewResults = models.Feed.by_webhook(config_options.couch_conn)
    webhook_feeds_view.options["key"] = str(webhook.id)
    webhook_feeds = [schemas.Feed.model_validate(feed) for feed in webhook_feeds_view]

    if (
        webhook_limits["max_feeds_per_hook"]
        and len(webhook_feeds) + 1 >= webhook_limits["max_feeds_per_hook"]
    ):
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            f"User is only allowed {webhook_limits['max_feeds_per_hook']} feeds on every webhook",
        )

    feed.webhooks.hooks.add(webhook.id)
    webhook.attached_feeds = [feed.id for feed in webhook_feeds]

    if len(feed.webhooks.hooks) == 1:
        feed = update_last_article(feed)

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()
    config_options.couch_conn[str(webhook.id)] = webhook.db_serialize(
        context={"show_secrets": True}
    )

    return feed


@router.delete("/feed/{feed_id}/webhook", responses=responses, tags=["webhooks"])
def remove_webhook_from_feed(
    feed: Annotated[schemas.Feed, Depends(get_own_feed)],
    webhook: Annotated[schemas.Webhook, Depends(get_own_webhook)],
) -> schemas.Feed:
    if webhook.id not in feed.webhooks.hooks:
        return feed

    feed.webhooks.hooks.remove(webhook.id)
    webhook.attached_feeds = [id for id in webhook.attached_feeds if id != feed.id]

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()
    config_options.couch_conn[str(webhook.id)] = webhook.db_serialize(
        context={"show_secrets": True}
    )

    return feed


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
