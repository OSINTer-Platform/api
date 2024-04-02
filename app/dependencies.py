from typing import Annotated, Literal, Self, Set, TypeAlias
from fastapi import Body, Depends, HTTPException, Query, status
from datetime import datetime
from app.authorization import Area, get_allowed_areas
from app.users.schemas import Collection, FeedCreate

from modules.elastic import ArticleSearchQuery, CVESearchQuery

from app import config_options
from app.common import CVESortBy, EsIDList, ArticleSortBy


def get_source_exclusions(
    allowed_areas: Annotated[list[Area], Depends(get_allowed_areas)]
) -> list[str]:
    areas_to_fields: dict[Area, str] = {
        "map": "ml.coordinates",
        "cluster": "ml.cluster",
        "similar": "similar",
        "summary": "summary",
    }

    return [v for k, v in areas_to_fields.items() if not k in allowed_areas]


SourceExclusions: TypeAlias = Annotated[list[str], Depends(get_source_exclusions)]


class FastapiArticleSearchQuery(ArticleSearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        exclusions: SourceExclusions,
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
        cluster_id: str | None = None,
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
            cluster_id=cluster_id,
            custom_exclude_fields=exclusions,
        )

    @classmethod
    def from_item(cls, item: FeedCreate | Collection, exclusions: list[str]) -> Self:
        if isinstance(item, FeedCreate):
            return cls(
                exclusions=exclusions,
                limit=item.limit if item.limit else 0,
                sort_by=item.sort_by,
                sort_order=item.sort_order,
                search_term=item.search_term,
                semantic_search=item.semantic_search,
                highlight=True if item.search_term and item.highlight else False,
                first_date=item.first_date,
                last_date=item.last_date,
                sources=item.sources,
            )
        elif isinstance(item, Collection):
            return cls(
                exclusions=exclusions,
                limit=10_000 if len(item.ids) < 10_000 else 0,
                sort_by="publish_date",
                sort_order="desc",
                ids=item.ids,
            )
        else:
            raise NotImplemented


class FastapiQueryParamsArticleSearchQuery(FastapiArticleSearchQuery):
    def __init__(
        self,
        exclusions: SourceExclusions,
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
        cluster_id: str | None = Query(None),
    ):
        super().__init__(
            exclusions=exclusions,
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
            cluster_id=cluster_id,
        )


class FastapiCVESearchQuery(CVESearchQuery):
    def __init__(
        self,
        limit: Annotated[int, Body()] = 0,
        sort_by: Annotated[CVESortBy | None, Body()] = "document_count",
        sort_order: Annotated[Literal["desc", "asc"], Body()] = "desc",
        search_term: Annotated[str | None, Body()] = None,
        cves: Annotated[Set[str] | None, Body()] = None,
        ids: Annotated[EsIDList | None, Body()] = None,
        highlight: Annotated[bool, Body()] = False,
        highlight_symbol: Annotated[str, Body()] = "**",
    ):
        super().__init__(
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search_term=search_term,
            cves=cves,
            ids=ids,
            highlight=highlight,
            highlight_symbol=highlight_symbol,
        )
