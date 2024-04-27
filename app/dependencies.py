from typing import Annotated, Literal, Self, Set, TypeAlias
from uuid import UUID
from fastapi import Body, Depends, HTTPException, Query, status
from datetime import datetime

from app.authorization import get_source_exclusions
from app.users.crud import get_full_user_object
from app.users.schemas import AuthUser, Collection, FeedCreate, User

from modules.elastic import ArticleSearchQuery, CVESearchQuery

from app import config_options
from app.common import CVESortBy, EsIDList, ArticleSortBy

SourceExclusions: TypeAlias = Annotated[list[str], Depends(get_source_exclusions)]


class FastapiArticleSearchQuery(ArticleSearchQuery):
    """
    Wrapper around the searchquery class used by the backend to search in elasticsearch
    """

    def __init__(
        self,
        exclusions: SourceExclusions,
        limit: Annotated[int, Body()] = 0,
        sort_by: Annotated[ArticleSortBy | None, Body()] = "",
        sort_order: Annotated[Literal["desc", "asc"], Body()] = "desc",
        search_term: Annotated[str | None, Body()] = None,
        semantic_search: Annotated[str | None, Body()] = None,
        first_date: Annotated[datetime | None, Body()] = None,
        last_date: Annotated[datetime | None, Body()] = None,
        sources: Annotated[set[str] | None, Body()] = None,
        ids: Annotated[EsIDList | None, Body()] = None,
        highlight: Annotated[bool, Body()] = False,
        highlight_symbol: Annotated[str, Body()] = "**",
        cluster_id: Annotated[str | None, Body()] = None,
        cve: Annotated[str | None, Body()] = None,
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
            cve=cve,
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
        cve: str | None = None,
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
            cve=cve,
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
        first_date: Annotated[datetime | None, Body()] = None,
        last_date: Annotated[datetime | None, Body()] = None,
        date_field: Annotated[
            Literal["publish_date", "modified_date"], Body()
        ] = "publish_date",
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
            first_date=first_date,
            last_date=last_date,
            date_field=date_field,
        )


class UserCache:
    def __init__(self) -> None:
        self.user: None | User | AuthUser = None

    def get_user(self: Self, id: UUID) -> User | None:
        if isinstance(self.user, User):
            return self.user

        user = get_full_user_object(id)
        if not isinstance(user, User):
            return None

        self.user = user
        return user

    def get_auth_user(self: Self, id: UUID) -> AuthUser | None:
        if isinstance(self.user, AuthUser):
            return self.user

        user = get_full_user_object(id, auth=True)

        if not isinstance(user, AuthUser):
            return None

        self.user = user
        return user
