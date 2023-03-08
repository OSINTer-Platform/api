from typing import Literal, cast
from fastapi import Query

from datetime import datetime

from modules.elastic import SearchQuery

from pydantic import constr, conlist

ArticleSortBy = Literal[
    "publish_date", "read_times", "source", "author", "inserted_at", ""
]


class FastapiSearchQuery(SearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        limit: int = Query(10_000),
        sort_by: ArticleSortBy | None = Query(""),
        sort_order: Literal["desc", "asc"] | None = Query("desc"),
        search_term: str | None = Query(None),
        first_date: datetime | None = Query(None),
        last_date: datetime | None = Query(None),
        source_category: list[str] | None = Query(None),
        ids: conlist(
            constr(strip_whitespace=True, min_length=20, max_length=20)
        )  # pyright: ignore
        | None = Query(None),
        highlight: bool = Query(False),
        highlight_symbol: str = Query("**"),
        complete: bool = Query(False),
        cluster_id: int | None = Query(None),
    ):

        super().__init__(
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search_term=search_term,
            first_date=first_date,
            last_date=last_date,
            source_category=source_category,
            ids=cast(list[str], ids),
            highlight=highlight,
            highlight_symbol=highlight_symbol,
            complete=complete,
            cluster_id=cluster_id,
        )
