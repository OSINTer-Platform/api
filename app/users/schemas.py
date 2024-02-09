from collections.abc import Sequence, Set
from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias, Union
from uuid import UUID, uuid4
from couchdb.mapping import ListField

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.common import ArticleSortBy


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
    semantic_search: str | None = None
    highlight: bool | None = False

    first_date: datetime | None = None
    last_date: datetime | None = None

    sources: set[str] = set()

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

    @field_validator("ids", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


UserItem: TypeAlias = Annotated[Union[Feed, Collection], Field(discriminator="type")]


class UserSettings(ORMBase):
    dark_mode: bool = True
    render_external: bool = False
    list_render_mode: Literal["large"] | Literal["title"] = "large"


class PartialUserSettings(ORMBase):
    dark_mode: bool | None = None
    render_external: bool | None = None
    list_render_mode: Literal["large"] | Literal["title"] | None = None


class User(ORMBase):
    id: UUID = Field(alias="_id")
    username: str

    active: bool = True
    premium: int = 0

    already_read: UUID | None = None

    feed_ids: set[UUID] = set()
    collection_ids: set[UUID] = set()

    feeds: list[Feed] = []
    collections: list[Collection] = []

    settings: UserSettings

    type: Literal["user"] = "user"

    @field_validator("feed_ids", "collection_ids", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


class AuthUser(User):
    hashed_password: str
    hashed_email: str | None
