from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic.utils import GetterDict

# Needed, as pydantic would otherwise ignore the _id field from the DB models
class ORMGetter(GetterDict):
    def get(self, key: str, default: Any) -> Any:
        if key == "_id":
            return self._obj._id
        else:
            return super().get(key, default)


# Used for mapping the _id field of the DB model to the schemas id field
class ORMBase(BaseModel):
    def dict(self, *args, **kwargs) -> dict[str, Any]:
        obj = super().dict(*args, **kwargs)

        obj["_id"] = obj.pop("id").hex
        return obj

    class Config:
        orm_mode = True
        getter_dict = ORMGetter


class ItemBase(ORMBase):
    id: UUID = uuid4()
    name: str
    owner: UUID | None = None


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


class UserBase(ORMBase):
    id: UUID
    username: str

    active: bool = True

    feed_ids: set[str] = set()
    collection_ids: set[str] = set()


class User(UserBase):
    feeds: list[Feed] = []
    collections: list[Collection] = []


class UserCreate(UserBase):
    hashed_password: str
    hashed_email: str | None
