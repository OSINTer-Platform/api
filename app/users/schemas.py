from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from app.dependencies import ArticleSortBy, ArticleSortOrder

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


class FeedCreate(BaseModel):
    limit: int | None = 100

    sort_by: ArticleSortBy | None = ArticleSortBy.PublishDate
    sort_order: ArticleSortOrder | None = ArticleSortOrder.Descending

    search_term: str | None = None
    highlight: bool | None = False

    first_date: datetime | None = None
    last_date: datetime | None = None

    source_category: list[str] = []

    class Config:
        use_enum_values = True

    def to_query(self):
        return SearchQuery(
            limit=self.limit if self.limit else 0,
            sort_by=str(self.sort_by) if self.sort_by else None,
            sort_order=str(self.sort_order) if self.sort_order else None,
            search_term=self.search_term,
            highlight=True if self.search_term and self.highlight else False,
            first_date=self.first_date,
            last_date=self.last_date,
            source_category=self.source_category,
        )


class Feed(ItemBase, FeedCreate):
    pass


class Collection(ItemBase):
    ids: set[str] = set()

    def to_query(self):
        return SearchQuery(
            limit=10_000 if len(self.ids) < 10_000 else 0,
            sort_by=ArticleSortBy.PublishDate.value,
            sort_order=ArticleSortOrder.Descending.value,
            ids=list(self.ids),
        )


class UserBase(ORMBase):
    id: UUID = Field(alias="_id")
    username: str

    active: bool = True


class User(UserBase):
    feed_ids: set[UUID] = set()
    collection_ids: set[UUID] = set()

    feeds: list[Feed] = []
    collections: list[Collection] = []


class UserAuth(UserBase):
    hashed_password: str
    hashed_email: str | None
