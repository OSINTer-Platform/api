from typing import TypeVar
from couchdb.mapping import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    IntegerField,
    ListField,
    Mapping,
    TextField,
    ViewDefinition,
    ViewField,
)


class BaseDocument(Document):  # type: ignore[misc]
    _id = TextField()
    _rev = TextField()
    creation_time = TextField()


class User(BaseDocument):
    username = TextField()
    active = BooleanField()

    feed_ids = ListField(TextField())
    collection_ids = ListField(TextField())
    read_articles = ListField(TextField())

    settings = DictField(
        Mapping.build(
            dark_mode=BooleanField(default=True),
            render_external=BooleanField(default=False),
            list_render_mode=TextField(default="large"),
        )
    )

    enterprise = BooleanField(default=False)

    premium = DictField(
        Mapping.build(
            status=BooleanField(default=False),
            expire_time=IntegerField(default=0),
            acknowledged=DictField(default={}),
        )
    )

    payment = DictField(
        Mapping.build(
            stripe_id=TextField(default=""),
            invoice=DictField(
                Mapping.build(
                    last_updated=IntegerField(default=0),
                    action_required=BooleanField(default=False),
                    action_type=TextField(default=""),
                    payment_intent=TextField(default=""),
                    invoice_url=TextField(default=""),
                )
            ),
            subscription=DictField(
                Mapping.build(
                    last_updated=IntegerField(default=0),
                    stripe_product_id=TextField(default=""),
                    stripe_subscription_id=TextField(default=""),
                    state=TextField(default=""),
                    level=TextField(default=""),
                    cancel_at_period_end=BooleanField(default=False),
                    current_period_end=IntegerField(default=0),
                )
            ),
            address=DictField(
                Mapping.build(
                    city=TextField(),
                    country=TextField(),
                    customer_name=TextField(),
                    line1=TextField(),
                    line2=TextField(),
                    postal_code=TextField(),
                    state=TextField(),
                )
            ),
        )
    )

    api_key = TextField()

    hashed_password = TextField()
    hashed_email = TextField()

    type = TextField(default="user")

    # Views
    all = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user") {
                emit(doc._id, doc);
            }
        }""",
    )

    by_username = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user") {
                emit(doc.username, doc)
            }
        }""",
    )

    by_api_key = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user" && doc.api_key) {
                emit(doc.api_key, doc)
            }
        }""",
    )

    by_stripe_id = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user" && doc.payment.stripe_id.length > 0) {
                emit(doc.payment.stripe_id, doc)
            }
        }""",
    )


class Survey(BaseDocument):
    metadata = DictField(
        Mapping.build(
            user_id=TextField(),
            submission_date=DateTimeField(),
        )
    )

    contents = ListField(
        DictField(
            Mapping.build(
                title=TextField(), rating=IntegerField(), feedback=TextField()
            )
        )
    )

    version = IntegerField()
    type = TextField(default="survey")

    # Views
    all = ViewField(
        "surveys",
        """
        function(doc) {
            if(doc.type == "survey") {
                emit(doc._id, doc);
            }
        }""",
    )

    by_user_id = ViewField(
        "surveys",
        """
        function(doc) {
            if(doc.type == "survey") {
                emit(doc.metadata.user_id, doc)
            }
        }""",
    )


class ItemBase(BaseDocument):
    name = TextField()
    owner = TextField()
    type = TextField()


class FeedItemBase(ItemBase):
    deleteable = BooleanField(default=True)


class Feed(FeedItemBase):
    limit = IntegerField()

    sort_by = TextField()
    sort_order = TextField()

    search_term = TextField()
    highlight = BooleanField()

    first_date = TextField()
    last_date = TextField()

    sources = ListField(TextField())

    webhooks = DictField(Mapping.build(last_article=TextField()))

    type = TextField(default="feed")

    # Views
    all = ViewField(
        "feeds",
        """
        function(doc) {
            if(doc.type == "feed") {
                emit(doc._id, doc);
            }
        }""",
    )

    get_minimal_info = ViewField(
        "feeds",
        """
        function(doc) {
            if(doc.type == "feed") {
                emit(doc._id, { name : doc.name, owner : doc.owner} )
            }
        }""",
    )


class Collection(FeedItemBase):
    ids = ListField(TextField())

    type = TextField(default="collection")

    # Views
    all = ViewField(
        "collections",
        """
        function(doc) {
            if(doc.type == "collection") {
                emit(doc._id, doc);
            }
        }""",
    )

    get_minimal_info = ViewField(
        "collections",
        """
        function(doc) {
            if(doc.type == "collection") {
                emit(doc._id, { name : doc.name, owner : doc.owner} )
            }
        }""",
    )


class Webhook(ItemBase):
    url = TextField()
    hook_type = TextField()
    attached_feeds = ListField(TextField())

    type = TextField(default="webhook")

    all = ViewField(
        "webhooks",
        """
        function(doc) {
            if(doc.type == "webhook") {
                emit(doc._id, doc);
            }
        }""",
    )

    by_owner = ViewField(
        "webhooks",
        """
        function(doc) {
            if(doc.type == "webhook") {
                emit(doc.owner, doc)
            }
        }""",
    )

    by_feed = ViewField(
        "webhooks",
        """
        function(doc) {
            if(doc.type == "webhook") {
                for (const id of doc.attached_feeds) {
                    emit(id, doc)
                }
            }
        }""",
    )


DBModels = TypeVar("DBModels", Feed, Collection, User)

views: list[ViewDefinition] = [
    User.all,
    User.by_username,
    User.by_api_key,
    User.by_stripe_id,
    Survey.all,
    Survey.by_user_id,
    Feed.all,
    Feed.get_minimal_info,
    Collection.all,
    Webhook.all,
    Webhook.by_owner,
    Webhook.by_feed,
]
