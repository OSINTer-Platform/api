from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from app.dependencies import ArticleSortBy, ArticleSortOrder


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


class Feed(ItemBase, FeedCreate):
    pass


class Collection(ItemBase):
    ids: set[str] = set()


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
