from typing import TypeVar
from couchdb.mapping import (
    BooleanField,
    DateTimeField,
    Document,
    IntegerField,
    ListField,
    TextField,
    ViewDefinition,
    ViewField,
)


class User(Document):  # type: ignore[misc]
    # UserBase
    _id = TextField()
    username = TextField()
    active = BooleanField()

    already_read = TextField()

    # User
    feed_ids = ListField(TextField())
    collection_ids = ListField(TextField())

    # UserAuth
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
                emit(doc.username, { username : doc.username, active: doc.active, already_read : doc.already_read, feed_ids: doc.feed_ids, collection_ids: doc.collection_ids });
            }
        }""",
    )

    auth_info = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user") {
                emit(doc.username, { username : doc.username, hashed_password : doc.hashed_password, hashed_email : doc.hashed_email, active : doc.active });
            }
        }""",
    )


class ItemBase(Document):  # type: ignore[misc]
    _id = TextField()
    name = TextField()
    owner = TextField()
    type = TextField()
    deleteable = BooleanField(default=True)


class Feed(ItemBase):
    limit = IntegerField()

    sort_by = TextField()
    sort_order = TextField()

    search_term = TextField()
    highlight = BooleanField()

    first_date = DateTimeField()
    last_date = DateTimeField()

    sources = ListField(TextField())

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


class Collection(ItemBase):
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


DBModels = TypeVar("DBModels", Feed, Collection, User)

views: list[ViewDefinition] = [
    User.all,
    User.auth_info,
    User.by_username,
    Feed.all,
    Feed.get_minimal_info,
    Collection.all,
]
