from typing import Literal, TypeAlias, overload
from uuid import UUID, uuid4

from couchdb import Document, ResourceNotFound
from couchdb.client import ViewResults
from fastapi.encoders import jsonable_encoder
from pydantic import SecretStr

from app import config_options
from app.authorization import expire_premium
from app.secrets import hash_value, verify_hash
from app.users import models, schemas


def check_username(username: str) -> Literal[False] | schemas.User:
    try:
        user = list(models.User.by_username(config_options.couch_conn)[username])[0]
        return schemas.User.model_validate(user)
    except IndexError:
        return False


# Return of db model for user is for use in following crud functions
def verify_user(
    id: UUID,
    user: schemas.User | None = None,
    username: str | None = None,
    password: str | None = None,
    email: str | None = None,
) -> Literal[False] | schemas.User:
    # TODO: Implement rehashing
    if not user:
        user_query = get_item(id, "user")

        if isinstance(user_query, int):
            return False

        user = user_query

    if username and user.username != username:
        return False

    if password and not verify_hash(password, user.hashed_password.get_secret_value()):
        return False

    if (
        email
        and user.hashed_email
        and not verify_hash(email, user.hashed_email.get_secret_value())
    ):
        return False

    return user


# Ensures that usernames are unique
def create_user(
    username: str,
    password: str,
    email: str | None = "",
    id: UUID | None = None,
    premium: schemas.UserPremium | None = None,
) -> bool:
    if check_username(username):
        return False

    if email:
        email_hash = hash_value(email)
    else:
        email_hash = None

    if not id:
        id = uuid4()

    password_hash = hash_value(password)

    user_schema = schemas.User(
        _id=id,
        username=username,
        active=True,
        hashed_password=password_hash,
        hashed_email=email_hash if email_hash else None,
        settings=schemas.UserSettings(),
        payment=schemas.UserPayment(),
        premium=premium if premium else schemas.UserPremium(),
    )

    config_options.couch_conn[str(id)] = user_schema.db_serialize(
        context={"show_secrets": True}
    )

    return True


def remove_user(username: str) -> bool:
    user = check_username(username)

    if user:
        del config_options.couch_conn[str(user.id)]
    else:
        return False

    return True


def update_user(user: schemas.User) -> None:
    user = expire_premium(user)

    config_options.couch_conn[str(user.id)] = user.db_serialize(
        context={"show_secrets": True}
    )


def modify_user_subscription(
    user_id: UUID,
    ids: list[UUID],
    action: Literal["subscribe", "unsubscribe"],
    item_type: Literal["feed", "collection"],
) -> schemas.User | None:
    user = get_item(user_id, "user")

    if isinstance(user, int):
        return None

    if item_type == "feed":
        source = user.feed_ids
    elif item_type == "collection":
        source = user.collection_ids
    else:
        raise NotImplementedError

    if action == "subscribe":
        source = source.union(ids)
    elif action == "unsubscribe":
        source = source.difference(ids)
    else:
        raise NotImplementedError

    if item_type == "feed":
        user.feed_ids = source
    elif item_type == "collection":
        user.collection_ids = source

    config_options.couch_conn[str(user.id)] = user.db_serialize(
        context={"show_secrets": True}
    )

    return user


def create_feed(
    feed_params: schemas.FeedCreate,
    name: str,
    owner: UUID,
    id: UUID | None = None,
    deleteable: bool = True,
) -> schemas.Feed:
    if not id:
        id = uuid4()

    feed = schemas.Feed(
        name=name,
        _id=id,
        deleteable=deleteable,
        owner=owner,
        **feed_params.model_dump(),
    )

    config_options.couch_conn[str(id)] = feed.db_serialize()

    return feed


def create_collection(
    name: str,
    owner: UUID,
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

    if ids:
        collection.ids = ids

    config_options.couch_conn[str(id)] = collection.db_serialize()

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


ItemType: TypeAlias = Literal["feed", "collection", "webhook", "user"]


@overload
def get_item(id: UUID, item_type: Literal["user"]) -> schemas.User | int: ...
@overload
@overload
def get_item(id: UUID, item_type: Literal["feed"]) -> schemas.Feed | int: ...
@overload
def get_item(
    id: UUID, item_type: Literal["collection"]
) -> schemas.Collection | int: ...
@overload
def get_item(id: UUID, item_type: Literal["webhook"]) -> schemas.Webhook | int: ...
@overload
def get_item(
    id: UUID, item_type: tuple[Literal["feed"], Literal["collection"]]
) -> schemas.Feed | schemas.Collection | int: ...
@overload
def get_item(
    id: UUID, item_type: None | tuple[ItemType, ItemType] = ...
) -> schemas.Feed | schemas.Collection | schemas.Webhook | int: ...


def get_item(
    id: UUID, item_type: ItemType | tuple[ItemType, ItemType] | None = None
) -> schemas.Feed | schemas.Collection | schemas.Webhook | schemas.User | int:
    try:
        item: Document = config_options.couch_conn[str(id)]
    except ResourceNotFound:
        return 404

    if item_type:
        if isinstance(item_type, str) and item_type != item["type"]:
            return 404
        elif not item["type"] in item_type:
            return 404

    if item["type"] == "feed":
        return schemas.Feed.model_validate(item)
    elif item["type"] == "collection":
        return schemas.Collection.model_validate(item)
    elif item["type"] == "webhook":
        return schemas.Webhook.model_validate(item)
    elif item["type"] == "user":
        return schemas.User.model_validate(item)
    else:
        return 404


def modify_collection(
    id: UUID,
    contents: set[str],
    user: schemas.User,
    action: Literal["replace", "extend"] = "replace",
) -> int | schemas.Collection:
    item = get_item(id, "collection")

    if isinstance(item, int):
        return item

    collection = schemas.Collection.model_validate(item)

    if collection.owner != user.id:
        return 403

    if action == "replace":
        collection.ids = contents
    elif action == "extend":
        collection.ids.update(contents)

    config_options.couch_conn[str(id)] = collection.db_serialize()

    return collection


def change_item_name(
    id: UUID, new_name: str, user: schemas.User
) -> int | schemas.Collection | schemas.Feed:
    item = get_item(id, ("feed", "collection"))

    if isinstance(item, int):
        return item

    item_schema: schemas.Feed | schemas.Collection = (
        schemas.Feed.model_validate(item)
        if item.type == "feed"
        else schemas.Collection.model_validate(item)
    )

    if item_schema.owner != user.id:
        return 403

    item_schema.name = new_name

    config_options.couch_conn[str(id)] = item_schema.db_serialize()

    return item_schema
