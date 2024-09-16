from typing import Annotated, NoReturn, overload
from typing_extensions import Any, TypeVar
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.common import HTTPError
from app.dependencies import FastapiArticleSearchQuery
from app.authorization import get_source_exclusions
from app.users import crud, schemas
from app.users.auth import ensure_user_from_token
from app.authorization import UserAuthorizer

from ... import config_options

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

WebhookAuthorizer = UserAuthorizer(["webhook"])


@overload
def handle_crud_response(response: int) -> NoReturn: ...
@overload
def handle_crud_response(response: R | int) -> R: ...


def handle_crud_response(response: R | int) -> R:
    if isinstance(response, int):
        raise HTTPException(
            status_code=responses[response]["status_code"],
            detail=responses[response]["detail"],
        )

    return response


def get_query_from_item(
    item_id: UUID, exclusions: Annotated[list[str], Depends(get_source_exclusions)]
) -> FastapiArticleSearchQuery | None:
    item = handle_crud_response(crud.get_item(item_id, ("feed", "collection")))

    if isinstance(
        item, schemas.FeedCreate | schemas.Collection
    ):  # type check needed for mypy
        q = FastapiArticleSearchQuery.from_item(item, exclusions)
        return q
    else:
        return handle_crud_response(404)


def get_own_feed(
    feed_id: UUID, user: Annotated[schemas.User, Depends(ensure_user_from_token)]
) -> schemas.Feed:
    item = handle_crud_response(crud.get_item(feed_id, "feed"))

    if item.owner != user.id:
        handle_crud_response(403)

    return item


def get_own_webhook(
    webhook_id: UUID, user: Annotated[schemas.User, Depends(ensure_user_from_token)]
) -> schemas.Webhook:
    WebhookAuthorizer(user)
    item = handle_crud_response(crud.get_item(webhook_id, "webhook"))

    if item.owner != user.id:
        handle_crud_response(403)

    return item


def update_last_article(feed: schemas.Feed) -> schemas.Feed:
    q = FastapiArticleSearchQuery.from_item(feed, [])
    q.limit = 1

    try:
        article = config_options.es_article_client.query_documents(q, False)[0][0]
        feed.webhooks.last_article = article.id
    except IndexError:
        feed.webhooks.last_article = ""

    return feed
