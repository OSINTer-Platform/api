from collections.abc import Sequence, Set
from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias, Union
from uuid import UUID, uuid4
from couchdb.mapping import ListField

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.dependencies import ArticleSortBy

from modules.elastic import ArticleSearchQuery


# Used for mapping the _id field of the DB model to the schemas id field
class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ItemBase(ORMBase):
    id: UUID = Field(alias="_id", default_factory=uuid4)
    name: str
    owner: UUID | None = None
    deleteable: bool | None = True


class FeedCreate(BaseModel):
    limit: int | None = 100

    sort_by: ArticleSortBy | None = "publish_date"
    sort_order: Literal["desc", "asc"] = "desc"

    search_term: str | None = None
    highlight: bool | None = False

    first_date: datetime | None = None
    last_date: datetime | None = None

    sources: set[str] = set()

    def to_query(self) -> ArticleSearchQuery:
        return ArticleSearchQuery(
            limit=self.limit if self.limit else 0,
            sort_by=self.sort_by,
            sort_order=self.sort_order,
            search_term=self.search_term,
            highlight=True if self.search_term and self.highlight else False,
            first_date=self.first_date,
            last_date=self.last_date,
            sources=self.sources,
        )

    @field_validator("sources", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


class Feed(ItemBase, FeedCreate):
    type: Literal["feed"] = "feed"


class Collection(ItemBase):
    type: Literal["collection"] = "collection"

    ids: set[str] = set()

    def to_query(self) -> ArticleSearchQuery:
        return ArticleSearchQuery(
            limit=10_000 if len(self.ids) < 10_000 else 0,
            sort_by="publish_date",
            sort_order="desc",
            ids=self.ids,
        )

    @field_validator("ids", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


UserItem: TypeAlias = Annotated[Union[Feed, Collection], Field(discriminator="type")]


class UserBase(ORMBase):
    id: UUID = Field(alias="_id")
    username: str

    active: bool = True


class User(UserBase):
    already_read: UUID | None = None

    feed_ids: set[UUID] = set()
    collection_ids: set[UUID] = set()

    feeds: list[Feed] = []
    collections: list[Collection] = []

    @field_validator("feed_ids", "collection_ids", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


class UserAuth(UserBase):
    hashed_password: str
    hashed_email: str | None


class FullUser(User, UserAuth):
    pass
