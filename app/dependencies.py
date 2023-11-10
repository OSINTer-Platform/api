from typing import Literal
from fastapi import Depends, HTTPException, Query, status
from datetime import datetime
from app.users.schemas import Collection, FeedCreate

from modules.elastic import ArticleSearchQuery

from app import config_options
from app.common import EsIDList, ArticleSortBy
from app.users.auth import check_premium


class FastapiArticleSearchQuery(ArticleSearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        limit: int = 0,
        sort_by: ArticleSortBy | None = "",
        sort_order: Literal["desc", "asc"] = "desc",
        search_term: str | None = None,
        semantic_search: str | None = None,
        first_date: datetime | None = None,
        last_date: datetime | None = None,
        sources: set[str] | None = None,
        ids: EsIDList | None = None,
        highlight: bool = False,
        highlight_symbol: str = "**",
        cluster_nr: int | None = None,
    ):
        if semantic_search and not config_options.ELASTICSEARCH_ELSER_PIPELINE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This instance doesn't offer semantic search",
            )

        super().__init__(
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search_term=search_term,
            semantic_search=semantic_search,
            first_date=first_date,
            last_date=last_date,
            sources=sources,
            ids=ids,
            highlight=highlight,
            highlight_symbol=highlight_symbol,
            cluster_nr=cluster_nr,
            custom_exclude_fields=None if premium else ["summary", "similar", "ml"],
        )

    @classmethod
    def from_item(cls, item: FeedCreate | Collection, premium: bool):
        if isinstance(item, FeedCreate):
            return cls(
                limit=item.limit if item.limit else 0,
                sort_by=item.sort_by,
                sort_order=item.sort_order,
                search_term=item.search_term,
                semantic_search=item.semantic_search,
                highlight=True if item.search_term and item.highlight else False,
                first_date=item.first_date,
                last_date=item.last_date,
                sources=item.sources,
                premium=premium,
            )
        elif isinstance(item, Collection):
            return cls(
                limit=10_000 if len(item.ids) < 10_000 else 0,
                sort_by="publish_date",
                sort_order="desc",
                ids=item.ids,
                premium=premium,
            )
        else:
            raise NotImplemented


class FastapiQueryParamsArticleSearchQuery(FastapiArticleSearchQuery):
    def __init__(
        self,
        limit: int = Query(0),
        sort_by: ArticleSortBy | None = Query(""),
        sort_order: Literal["desc", "asc"] = Query("desc"),
        search_term: str | None = Query(None),
        semantic_search: str | None = Query(None),
        first_date: datetime | None = Query(None),
        last_date: datetime | None = Query(None),
        sources: set[str] | None = Query(None),
        ids: EsIDList | None = Query(None),
        highlight: bool = Query(False),
        highlight_symbol: str = Query("**"),
        cluster_nr: int | None = Query(None),
    ):
        super().__init__(
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search_term=search_term,
            semantic_search=semantic_search,
            first_date=first_date,
            last_date=last_date,
            sources=sources,
            ids=ids,
            highlight=highlight,
            highlight_symbol=highlight_symbol,
            cluster_nr=cluster_nr,
        )
