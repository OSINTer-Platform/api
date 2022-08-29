from modules.elastic import SearchQuery

from fastapi import Query, Path
from datetime import datetime
from typing import Optional
from pydantic import conlist, constr
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from .routers.auth import get_user_from_token
from .users import User
from .common import HTTPError


# Using wrapper around searchQuery class, to force fastapi to make all arguments query (and not body), by using Query([defaultArgument]) and not just [defaultargument]
@dataclass
class FastapiSearchQuery(SearchQuery):
    limit: int = Query(10_000)
    sort_by: Optional[str] = Query(None)
    sort_order: Optional[str] = Query(None)
    search_term: Optional[str] = Query(None)
    first_date: Optional[datetime] = Query(None)
    last_date: Optional[datetime] = Query(None)
    source_category: Optional[conlist(constr(strip_whitespace=True))] = Query(None)
    ids: Optional[
        conlist(constr(strip_whitespace=True, min_length=20, max_length=20))
    ] = Query(None)
    highlight: bool = Query(False)
    complete: bool = Query(
        False
    )  # For whether the query should only return the necessary information for creating an article object, or all data stored about the article


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
