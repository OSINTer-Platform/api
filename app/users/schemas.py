from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from app.dependencies import ArticleSortBy

from modules.elastic import SearchQuery


# Used for mapping the _id field of the DB model to the schemas id field
class ORMBase(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True


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

    source_category: list[str] = []

    def to_query(self):
        return SearchQuery(
            limit=self.limit if self.limit else 0,
            sort_by=self.sort_by,
            sort_order=self.sort_order,
            search_term=self.search_term,
            highlight=True if self.search_term and self.highlight else False,
            first_date=self.first_date,
            last_date=self.last_date,
            source_category=self.source_category,
        )


class Feed(ItemBase, FeedCreate):
    type: Literal["feed"] = "feed"


class Collection(ItemBase):
    type: Literal["collection"] = "collection"

    ids: set[str] = set()

    def to_query(self):
        return SearchQuery(
            limit=10_000 if len(self.ids) < 10_000 else 0,
            sort_by="publish_date",
            sort_order="desc",
            ids=list(self.ids),
        )


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


class UserAuth(UserBase):
    hashed_password: str
    hashed_email: str | None
