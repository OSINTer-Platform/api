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


class User(Document):
    # UserBase
    _id = TextField()
    username = TextField()
    active = BooleanField()

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

    auth_info = ViewField(
        "users",
        """
        function(doc) {
            if(doc.type == "user") {
                emit(doc.username, { username : doc.username, hashed_password : doc.hashed_password, hashed_email : doc.hashed_email, active : doc.active });
            }
        }""",
    )


class Feed(Document):
    _id = TextField()
    name = TextField()

    limit = IntegerField()

    sort_by = TextField()
    sort_order = TextField()

    search_term = TextField()
    highlight = BooleanField()

    first_date = DateTimeField()
    last_date = DateTimeField()

    source_category = ListField(TextField())

    type = TextField(default="feed")
    owner = TextField()

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


class Collection(Document):
    _id = TextField()
    name = TextField()

    ids = ListField(TextField())

    type = TextField(default="collection")
    owner = TextField()

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


views: list[ViewDefinition] = [
    User.all,
    User.auth_info,
    Feed.all,
    Feed.get_minimal_info,
    Collection.all,
]
