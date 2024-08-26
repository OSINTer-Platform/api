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

from .utils import WebhookAuthorizer


router = APIRouter(dependencies=[Depends(WebhookAuthorizer)])


@router.put("/create")
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
