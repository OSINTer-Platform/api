from typing import Literal, TypeAlias, cast, overload
from uuid import UUID, uuid4

from argon2.exceptions import VerifyMismatchError
from couchdb import Document, ResourceNotFound
from couchdb.client import ViewResults
from fastapi.encoders import jsonable_encoder

from app import config_options
from app.authorization import expire_premium
from app.users import models, schemas


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
                config_options.hasher.verify(hashed_value, raw_value)
            except VerifyMismatchError:
                return False
        elif raw_value:
            return False

    return user


def get_full_user_object(
    id: UUID, auth: bool = False
) -> None | schemas.User | schemas.AuthUser:
    user: models.User | None = models.User.load(config_options.couch_conn, str(id))

    if not user:
        return None

    user_schema: schemas.AuthUser | schemas.User
    if auth:
        user_schema = schemas.AuthUser.model_validate(user)
    else:
        user_schema = schemas.User.model_validate(user)

    return user_schema


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
        email_hash = config_options.hasher.hash(email)
    else:
        email_hash = None

    if not id:
        id = uuid4()

    password_hash = config_options.hasher.hash(password)

    user_schema = schemas.AuthUser(
        _id=id,
        username=username,
        active=True,
        hashed_password=password_hash,
        hashed_email=email_hash,
        settings=schemas.UserSettings(),
        payment=schemas.UserPayment(),
        premium=premium if premium else schemas.UserPremium(),
    )

    config_options.couch_conn[str(id)] = user_schema.db_serialize()

    return True


def remove_user(username: str) -> bool:
    user = check_username(username)

    if user:
        del config_options.couch_conn[str(user.id)]
    else:
        return False

    return True


def update_user(user: schemas.User | schemas.AuthUser) -> None:
    db_user = {}

    if type(user) is schemas.User:
        user_model = cast(
            models.User, models.User.load(config_options.couch_conn, str(user.id))
        )

        db_user = schemas.AuthUser.model_validate(user_model).db_serialize()

    user = expire_premium(user)

    config_options.couch_conn[str(user.id)] = {
        **db_user,
        **user.db_serialize(),
    }


def modify_user_subscription(
    user_id: UUID,
    ids: list[UUID],
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
        for id in ids:
            if not id in source:
                source.append(id)
    elif action == "unsubscribe":
        source = [id for id in source if id not in ids]
    else:
        raise NotImplementedError

    if item_type == "feed":
        user_schema.feed_ids = source
    elif item_type == "collection":
        user_schema.collection_ids = source

    config_options.couch_conn[str(user_schema.id)] = user_schema.db_serialize()

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
        **feed_params.db_serialize(),
    )

    if owner:
        feed.owner = owner

    feed_model = models.Feed(**feed.db_serialize())
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

    collection_model = models.Collection(**collection.db_serialize())
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


ItemType: TypeAlias = Literal["feed", "collection", "webhook"]


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
) -> schemas.Feed | schemas.Collection | schemas.Webhook | int:
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
    else:
        return 404


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
