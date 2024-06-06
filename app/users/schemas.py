from collections.abc import Sequence, Set
from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias, Union
from uuid import UUID, uuid4
from couchdb.mapping import ListField

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from app.common import ArticleSortBy
from app.connectors import WebhookType


class Base(BaseModel):
    def db_serialize(
        self,
        *,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        context: dict[str, Any] | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        serialize_as_any: bool = False
    ) -> dict[str, Any]:
        return self.model_dump(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )


# Used for mapping the _id field of the DB model to the schemas id field
class ORMBase(Base):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DBItemBase(ORMBase):
    id: UUID = Field(alias="_id", default_factory=uuid4)
    rev: str = Field(alias="_rev", default="")


class ItemBase(DBItemBase):
    name: str
    owner: UUID | None = None
    deleteable: bool | None = True


class FeedCreate(Base):
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


class FeedWebhooks(ORMBase):
    hooks: list[UUID] = []
    last_article: str = ""


class Feed(ItemBase, FeedCreate):
    webhooks: FeedWebhooks = FeedWebhooks()
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


class UserPremium(ORMBase):
    status: bool = False
    expire_time: int = 0
    acknowledged: dict[str, bool] = {}


class UserSettings(ORMBase):
    dark_mode: bool = True
    render_external: bool = False
    list_render_mode: Literal["large"] | Literal["title"] = "large"


class PartialUserSettings(ORMBase):
    dark_mode: bool | None = None
    render_external: bool | None = None
    list_render_mode: Literal["large"] | Literal["title"] | None = None


class UserPayment(ORMBase):
    class Invoice(ORMBase):
        last_updated: int = 0
        action_required: bool = False
        action_type: Literal["", "authenticate", "update"] = ""
        payment_intent: str = ""
        invoice_url: str = ""

    class Subscription(ORMBase):
        last_updated: int = 0
        stripe_product_id: str = ""
        stripe_subscription_id: str = ""
        level: Literal["", "pro"] = ""
        state: Literal["", "active", "past_due", "closed"] = ""

        cancel_at_period_end: bool = False
        current_period_end: int = 0

    stripe_id: str = ""
    invoice: Invoice = Invoice()
    subscription: Subscription = Subscription()


class User(DBItemBase):
    username: str

    active: bool = True

    feed_ids: list[UUID] = []
    collection_ids: list[UUID] = []
    read_articles: list[str] = []

    premium: UserPremium
    payment: UserPayment
    settings: UserSettings

    type: Literal["user"] = "user"

    @field_validator("feed_ids", "collection_ids", "read_articles", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return list(id_list)

        return id_list



class AuthUser(User):
    hashed_password: str
    hashed_email: str | None


class SurveySection(BaseModel):
    title: str
    rating: int
    feedback: str


class SurveyMetaData(BaseModel):
    user_id: UUID
    submission_date: datetime


class Survey(DBItemBase):
    contents: list[SurveySection]
    version: int
    metadata: SurveyMetaData
    type: Literal["survey"] = "survey"


class Webhook(DBItemBase):
    name: str
    owner: UUID
    url: SecretStr

    hook_type: WebhookType

    type: Literal["webhook"] = "webhook"
