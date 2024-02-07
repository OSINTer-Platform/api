from typing import Literal, cast
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from couchdb import Document, ResourceNotFound
from couchdb.client import ViewResults
from fastapi.encoders import jsonable_encoder

from app import config_options
from app.users import models, schemas

ph = PasswordHasher()


def duplicate_document(
    document: models.DBModels,
    document_class: type[models.DBModels],
    contents: schemas.ORMBase,
) -> models.DBModels:
    rev = document.rev
    new_document = document_class(**contents.model_dump(mode="json"))
    new_document._data["_rev"] = rev
    return new_document


def check_username(username: str) -> Literal[False] | models.User:
    try:
        return cast(
            models.User,
            list(models.User.by_username(config_options.couch_conn)[username])[0],
        )
    except IndexError:
        return False


# Return of db model for user is for use in following crud functions
def verify_user(
    id: UUID,
    user: models.User | None = None,
    username: str | None = None,
    password: str | None = None,
    email: str | None = None,
) -> Literal[False] | models.User:
    if not user:
        user = models.User.load(config_options.couch_conn, str(id))

    if not user:
        return False

    if username and user.username != username:
        return False

    # TODO: Implement rehashing
    for raw_value, hashed_value in [
        [password, user.hashed_password],
        [email, user.hashed_email],
    ]:
        if raw_value and hashed_value:
            try:
                ph.verify(hashed_value, raw_value)
            except VerifyMismatchError:
                return False

    return user


def get_full_user_object(id: UUID, complete: bool = False) -> None | schemas.User:
    user: models.User | None = models.User.load(config_options.couch_conn, str(id))

    if not user:
        return None

    user_schema = schemas.User.model_validate(user)

    if complete:
        user_schema.feeds = list(get_feeds(user_schema).values())
        user_schema.collections = list(get_collections(user_schema).values())

    return user_schema


# Ensures that usernames are unique
def create_user(
    username: str,
    password: str,
    email: str | None = "",
    id: UUID | None = None,
    premium: int = 0,
) -> bool:
    if check_username(username):
        return False

    if email:
        email_hash = ph.hash(email)
    else:
        email_hash = None

    if not id:
        id = uuid4()

    password_hash = ph.hash(password)

    new_user = models.User(
        _id=str(id),
        username=username,
        active=True,
        hashed_password=password_hash,
        hashed_email=email_hash,
        premium=premium,
    )

    collection = create_collection("Already Read", id, deleteable=False)
    new_user.already_read = collection.id

    new_user.store(config_options.couch_conn)
    modify_user_subscription(id, set([collection.id]), "subscribe", "collection")

    return True


def remove_user(username: str) -> bool:
    user = check_username(username)

    if user:
        del config_options.couch_conn[str(user.id)]
    else:
        return False

    return True


def update_user(
    id: UUID,
    new_username: str | None = None,
    new_password: str | None = None,
    new_email: str | None = None,
) -> schemas.User | tuple[int, str]:
    user = models.User.load(config_options.couch_conn, str(id))

    if not user:
        return (401, "User was not found")

    user_schema = schemas.AuthUser.model_validate(user)

    if new_username:
        if check_username(new_username):
            return (409, "Username is already taken")
        user_schema.username = new_username

    if new_password:
        user_schema.hashed_password = ph.hash(new_password)

    if new_email:
        user_schema.hashed_email = ph.hash(new_email)

    user = duplicate_document(user, models.User, user_schema)
    user.store(config_options.couch_conn)

    return user_schema


def modify_user_subscription(
    user_id: UUID,
    ids: set[UUID],
    action: Literal["subscribe", "unsubscribe"],
    item_type: Literal["feed", "collection"],
) -> schemas.User | None:
    user = models.User.load(config_options.couch_conn, str(user_id))

    if not user:
        return None

    user_schema = schemas.AuthUser.model_validate(user)

    if item_type == "feed":
        source = user_schema.feed_ids
    elif item_type == "collection":
        source = user_schema.collection_ids
    else:
        raise NotImplementedError

    if action == "subscribe":
        source = source.union(ids)
    elif action == "unsubscribe":
        source.difference_update(ids)
    else:
        raise NotImplementedError

    if item_type == "feed":
        user_schema.feed_ids = source
    elif item_type == "collection":
        user_schema.collection_ids = source

    user = duplicate_document(user, models.User, user_schema)

    user.store(config_options.couch_conn)

    return user_schema


def create_feed(
    feed_params: schemas.FeedCreate,
    name: str,
    owner: UUID | None = None,
    id: UUID | None = None,
    deleteable: bool = True,
) -> schemas.Feed:
    if not id:
        id = uuid4()

    feed = schemas.Feed(
        name=name,
        _id=id,
        deleteable=deleteable,
        **feed_params.model_dump(mode="json"),
    )

    if owner:
        feed.owner = owner

    feed_model = models.Feed(**feed.model_dump(mode="json"))
    feed_model.store(config_options.couch_conn)

    return feed


def create_collection(
    name: str,
    owner: UUID | None = None,
    id: UUID | None = None,
    ids: set[str] | None = None,
    deleteable: bool = True,
) -> schemas.Collection:
    if not id:
        id = uuid4()

    collection = schemas.Collection(
        name=name,
        owner=owner,
        _id=id,
        deleteable=deleteable,
    )

    if owner:
        collection.owner = owner
    if ids:
        collection.ids = ids

    collection_model = models.Collection(**collection.model_dump(mode="json"))
    collection_model.store(config_options.couch_conn)

    return collection


def get_feeds(user: schemas.User) -> dict[str, schemas.Feed]:
    all_feeds: ViewResults = models.Feed.all(config_options.couch_conn)

    all_feeds.options["keys"] = jsonable_encoder(user.feed_ids)

    return {feed._id: schemas.Feed.model_validate(feed) for feed in all_feeds}


def get_collections(user: schemas.User) -> dict[str, schemas.Collection]:
    all_collections: ViewResults = models.Collection.all(config_options.couch_conn)

    all_collections.options["keys"] = jsonable_encoder(user.collection_ids)

    return {
        collection._id: schemas.Collection.model_validate(collection)
        for collection in all_collections
    }


def get_item(id: UUID) -> schemas.Feed | schemas.Collection | int:
    try:
        item: Document = config_options.couch_conn[str(id)]
    except ResourceNotFound:
        return 404

    if item["type"] == "feed":
        return schemas.Feed.model_validate(item)
    elif item["type"] == "collection":
        return schemas.Collection.model_validate(item)
    else:
        return 404


def modify_feed(
    id: UUID, contents: schemas.FeedCreate, user: schemas.User
) -> int | schemas.Feed:
    item: models.Feed | None = models.Feed.load(config_options.couch_conn, str(id))

    if item is None or item.type != "feed":
        return 404
    elif item.owner != str(user.id):
        return 403

    for k, v in contents.model_dump(exclude_unset=True, mode="json").items():
        setattr(item, k, v)

    item.store(config_options.couch_conn)

    return schemas.Feed.model_validate(item)


def modify_collection(
    id: UUID,
    contents: set[str],
    user: schemas.User,
    action: Literal["replace", "extend"] = "replace",
) -> int | schemas.Collection:
    item: models.Collection | None = models.Collection.load(
        config_options.couch_conn, str(id)
    )

    if item is None or item.type != "collection":
        return 404
    elif item.owner != str(user.id):
        return 403

    if action == "replace":
        item.ids = list(contents)
    elif action == "extend":
        item.ids.extend(list(contents))  # pyright: ignore

    item.store(config_options.couch_conn)

    return schemas.Collection.model_validate(item)


def change_item_name(id: UUID, new_name: str, user: schemas.User) -> int | None:
    item: models.ItemBase | None = models.ItemBase.load(
        config_options.couch_conn, str(id)
    )

    if item is None or not item.type in ["feed", "collection"]:
        return 404
    elif item.owner != str(user.id):
        return 403

    item.name = new_name

    item.store(config_options.couch_conn)

    return None


# Has to verify the user owns the item before deletion
def remove_item(
    user: schemas.User,
    id: UUID,
) -> int | None:
    try:
        item = config_options.couch_conn[str(id)]
    except ResourceNotFound:
        return None

    if item["type"] not in ["feed", "collection"]:
        return 404
    elif item["owner"] != str(user.id):
        return 403
    elif not item["deleteable"]:
        return 422

    del config_options.couch_conn[str(id)]

    return None
