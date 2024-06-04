from typing import Annotated
from typing_extensions import Any, TypeVar
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.common import HTTPError
from app.dependencies import FastapiArticleSearchQuery
from app.authorization import get_source_exclusions
from app.users import crud, schemas
from app.authorization import UserAuthorizer


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
