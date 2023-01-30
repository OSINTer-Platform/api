from dataclasses import dataclass

from fastapi import Path, Query
from fastapi import Depends, HTTPException, status

from modules.elastic import SearchQuery

from .common import EsIDList
from .routers.auth import get_user_from_token
from .users import User


# Using wrapper around searchQuery class, to force fastapi to make all arguments query (and not body), by using Query([defaultArgument]) and not just [defaultargument]
@dataclass
class FastapiSearchQuery(SearchQuery):
    source_category: list[str] | None = Query(None)
    ids: EsIDList | None = Query(None)


def get_collection_ids(
    collection_name: str = Path(...), current_user: User = Depends(get_user_from_token)
):
    try:
        collection_ids = current_user.get_collections()[collection_name]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Found no collection with given name",
        )

    return collection_ids
