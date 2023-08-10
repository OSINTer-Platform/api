from typing import Literal
from fastapi import Query

from datetime import datetime
from app.common import EsIDList

from modules.elastic import SearchQuery

ArticleSortBy = Literal[
    "publish_date", "read_times", "source", "author", "inserted_at", ""
]


class FastapiSearchQuery(SearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        limit: int = Query(0),
        sort_by: ArticleSortBy | None = Query(""),
        sort_order: Literal["desc", "asc"] | None = Query("desc"),
        search_term: str | None = Query(None),
        first_date: datetime | None = Query(None),
        last_date: datetime | None = Query(None),
        source_category: set[str] | None = Query(None),
        ids: EsIDList | None = Query(None),
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
            ids=ids,
            highlight=highlight,
            highlight_symbol=highlight_symbol,
            complete=complete,
            cluster_id=cluster_id,
        )
