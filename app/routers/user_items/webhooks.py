from typing import Annotated
from couchdb.client import ViewResults
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import SecretStr
from starlette.status import HTTP_403_FORBIDDEN, HTTP_422_UNPROCESSABLE_ENTITY

from app import config_options
from app.authorization import WebhookLimits, get_webhook_limits
from app.connectors import WebhookType, connectors
from app.users import schemas, models
from app.users.auth import ensure_user_from_token

from .utils import (
    WebhookAuthorizer,
    get_own_feed,
    get_own_webhook,
    responses,
    update_last_article,
)


router = APIRouter(dependencies=[Depends(WebhookAuthorizer)])


@router.post("/create")
async def create_webhook(
    webhook_name: Annotated[str, Body()],
    url: Annotated[str, Body()],
    webhook_type: Annotated[WebhookType, Body()],
    user: Annotated[schemas.User, Depends(ensure_user_from_token)],
    webhook_limits: Annotated[WebhookLimits, Depends(get_webhook_limits)],
) -> schemas.Webhook:
    if webhook_limits["max_count"]:
        webhook_view: ViewResults = models.Webhook.by_owner(config_options.couch_conn)
        webhook_view.options["key"] = str(user.id)

        if len(webhook_view) >= webhook_limits["max_count"]:
            raise HTTPException(
                HTTP_403_FORBIDDEN,
                f"User is only allowed {webhook_limits['max_count']} webhooks",
            )

    if not await connectors[webhook_type]["validate"](url):
        raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, "Webhook url is invalid")

    webhook = schemas.Webhook(
        name=webhook_name, owner=user.id, url=SecretStr(url), hook_type=webhook_type
    )

    config_options.couch_conn[str(webhook.id)] = webhook.db_serialize(
        context={"show_secrets": True}
    )

    return webhook


@router.get("/list")
def list_webhooks(
    user: Annotated[schemas.User, Depends(ensure_user_from_token)]
) -> list[schemas.Webhook]:
    webhook_view: ViewResults = models.Webhook.by_owner(config_options.couch_conn)
    webhook_view.options["key"] = str(user.id)

    return [schemas.Webhook.model_validate(doc) for doc in webhook_view]


@router.put("/webhook/{webhook_id}/feed", responses=responses, tags=["webhooks"])
def attach_webhook_to_feed(
    feed: Annotated[schemas.Feed, Depends(get_own_feed)],
    webhook: Annotated[schemas.Webhook, Depends(get_own_webhook)],
    webhook_limits: Annotated[WebhookLimits, Depends(get_webhook_limits)],
) -> schemas.Feed:
    if feed.sort_by != "publish_date" or feed.sort_order != "desc":
        raise HTTPException(
            HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Feed need to be sorted by publish date descending when attaching webhook",
        )

    if feed.id in webhook.attached_feeds:
        return feed

    webhook_feeds = [
        schemas.Feed.model_validate(feed)
        for feed in models.Feed.by_webhook(config_options.couch_conn)[str(webhook.id)]
    ]

    if (
        webhook_limits["max_feeds_per_hook"]
        and len(webhook_feeds) + 1 >= webhook_limits["max_feeds_per_hook"]
    ):
        raise HTTPException(
            HTTP_403_FORBIDDEN,
            f"User is only allowed {webhook_limits['max_feeds_per_hook']} feeds on every webhook",
        )

    webhook.attached_feeds = {feed.id for feed in webhook_feeds}

    if len(models.Webhook.by_feed(config_options.couch_conn)[str(feed.id)]) == 1:
        feed = update_last_article(feed)

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()
    config_options.couch_conn[str(webhook.id)] = webhook.db_serialize(
        context={"show_secrets": True}
    )

    return feed


@router.delete("/webhook/{webhook_id}/feed", responses=responses, tags=["webhooks"])
def detach_webhook_from_feed(
    feed: Annotated[schemas.Feed, Depends(get_own_feed)],
    webhook: Annotated[schemas.Webhook, Depends(get_own_webhook)],
) -> schemas.Feed:
    if feed.id in webhook.attached_feeds:
        return feed

    webhook.attached_feeds = {id for id in webhook.attached_feeds if id != feed.id}

    config_options.couch_conn[str(feed.id)] = feed.db_serialize()
    config_options.couch_conn[str(webhook.id)] = webhook.db_serialize(
        context={"show_secrets": True}
    )

    return feed
