from enum import Enum
from typing import cast
from fastapi import Query

from datetime import datetime

from modules.elastic import SearchQuery

from pydantic import constr, conlist

class StrEnum(str, Enum):
    def __str__(self) -> str:
            return self.value

class ArticleSortBy(StrEnum):
    PublishDate = "publish_date"
    TimesRead = "read_times"
    Source = "source"
    Author = "author"
    TimeOfScraping = "inserted_at"
    BestMatch = None


class ArticleSortOrder(StrEnum):
    Descending = "desc"
    Ascending = "asc"


class FastapiSearchQuery(SearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        limit: int = Query(10_000),
        sort_by: ArticleSortBy | None = Query(ArticleSortBy.BestMatch),
        sort_order: ArticleSortOrder | None = Query(ArticleSortOrder.Descending),
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
            sort_by=sort_by.value if sort_by else None,
            sort_order=sort_order.value if sort_order else None,
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
