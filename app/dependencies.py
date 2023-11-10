from typing import Literal
from fastapi import HTTPException, Query, status

from datetime import datetime
from app.common import EsIDList

from modules.elastic import ArticleSearchQuery
from app import config_options



class FastapiArticleSearchQuery(ArticleSearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

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
        )
