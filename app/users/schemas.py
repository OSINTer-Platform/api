from collections.abc import Sequence, Set
from datetime import datetime, timezone
from typing import Annotated, Any, ClassVar, Literal, TypeAlias, Union
from uuid import UUID, uuid4
from couchdb.mapping import ListField

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FieldSerializationInfo,
    SecretStr,
    field_serializer,
    field_validator,
)
from app.common import ArticleSortBy
from app.connectors import WebhookType


# Used for mapping the _id field of the DB model to the schemas id field
class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DBItemBase(ORMBase):
    id: UUID = Field(alias="_id", default_factory=uuid4)
    rev: str | None = Field(alias="_rev", default=None)
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def db_serialize(
        self,
        *,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        context: dict[str, Any] | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        serialize_as_any: bool = False
    ) -> dict[str, Any]:
        model = self.model_dump(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=True,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

        if model["_rev"] is None:
            del model["_rev"]

        return model


class ItemBase(DBItemBase):
    name: str
    owner: UUID


class FeedItemBase(ItemBase):
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

    @field_validator("sources", mode="before")
    @classmethod
    def convert_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list


class FeedWebhooks(ORMBase):
    last_article: str = ""


class Feed(FeedItemBase, FeedCreate):
    webhooks: FeedWebhooks = FeedWebhooks()
    type: Literal["feed"] = "feed"


class Collection(FeedItemBase):
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
        level: Literal["", "base", "pro"] = ""
        state: Literal["", "active", "past_due", "closed"] = ""

        cancel_at_period_end: bool = False
        current_period_end: int = 0

    stripe_id: str = ""
    invoice: Invoice = Invoice()
    subscription: Subscription = Subscription()


class User(DBItemBase):
    username: str

    active: bool = True

    feed_ids: set[UUID] = set()
    collection_ids: set[UUID] = set()
    read_articles: list[str] = []

    enterprise: bool = False
    premium: UserPremium
    payment: UserPayment
    settings: UserSettings

    api_key: SecretStr | None = None

    hashed_password: SecretStr
    hashed_email: SecretStr | None

    type: Literal["user"] = "user"

    @field_validator("feed_ids", "collection_ids", mode="before")
    @classmethod
    def convert_set_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return set(id_list)

        return id_list

    @field_validator("read_articles", mode="before")
    @classmethod
    def convert_list_proxies(cls, id_list: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(id_list, ListField.Proxy):
            return list(id_list)

        return id_list

    @field_serializer("hashed_password", "hashed_email", "api_key")
    def dump_secrets(
        self, v: SecretStr | None, info: FieldSerializationInfo
    ) -> str | None:
        if v and info.context and info.context.get("show_secrets"):
            return v.get_secret_value()
        elif v:
            return str(v)
        return None


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


class Webhook(ItemBase):
    url: SecretStr

    hook_type: WebhookType
    attached_feeds: set[UUID] = set()

    type: Literal["webhook"] = "webhook"

    @field_validator("attached_feeds", mode="before")
    @classmethod
    def convert_proxies(cls, feeds: Sequence[Any]) -> Set[Any] | Sequence[Any]:
        if isinstance(feeds, ListField.Proxy):
            return set(feeds)

        return feeds

    @field_serializer("url")
    def dump_secrets(self, v: SecretStr, info: FieldSerializationInfo) -> str:
        if info.context and info.context.get("show_secrets"):
            return v.get_secret_value()
        return str(v)
