from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel


class ItemBase(BaseModel):
    _id: UUID = uuid4()
    name: str
    owner: UUID | None = None

    class Config:
        orm_mode = True


class FeedCreate(BaseModel):
    limit: int | None = None

    sort_by: str | None = None
    sort_order: str | None = None

    search_term: str | None = None
    highlight: bool | None = None

    first_date: datetime | None = None
    last_date: datetime | None = None

    source_category: list[str] | None = None


class Feed(ItemBase, FeedCreate):
    pass


class Collection(ItemBase):
    items: list[str] = []


class UserBase(BaseModel):
    _id: UUID = uuid4()
    username: str

    active: bool = True

    feed_ids: list[str] = []
    collection_ids: list[str] = []

    class Config:
        orm_mode = True


class User(UserBase):
    feeds: list[Feed] = []
    collections: list[Collection] = []


class UserCreate(UserBase):
    hashed_password: str
    hashed_email: str | None
