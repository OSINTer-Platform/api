from typing import Literal
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from couchdb import Database, ResourceConflict
from couchdb.client import ViewResults

from . import get_db_conn, models, schemas

ph = PasswordHasher()

db_conn: Database = get_db_conn()


# Return of db model for user is for use in following crud functions
def verify_user(
    username: str,
    password: str | None = None,
    email: str | None = None,
) -> Literal[False] | models.User:

    users: ViewResults = models.User.get_minimal_info(db_conn)[username]
    try:
        user: models.User = list(users)[0]
    except IndexError:
        return False

    if user.username != username:
        return False

    # TODO: Implement rehashing
    for raw_value, hashed_value in [
        [password, user.hashed_password],
        [email, user.hashed_email],
    ]:
        if raw_value:
            try:
                ph.verify(hashed_value, raw_value)
            except VerifyMismatchError:
                return False

    return user


# Ensures that usernames are unique
def create_user(
    username: str,
    password: str,
    email: str | None = "",
) -> bool:
    if verify_user(username):
        return False

    if email:
        email_hash = ph.hash(email)
    else:
        email_hash = None

    password_hash = ph.hash(password)

    new_user = models.User(
        _id=uuid4().hex,
        username=username,
        active=True,
        hashed_password=password_hash,
        hashed_email=email_hash,
    )

    new_user.store(db_conn)

    return True


def remove_user(username: str) -> bool:
    user = verify_user(username)

    if user:
        del db_conn[user._id]

    return True


def modify_user_subscription(
    user_id: UUID,
    ids: list[str],
    action: Literal["subscribe", "unsubscribe"],
    item_type: Literal["feed", "collection"],
) -> bool:

    try:
        user: models.User = list(models.User.all(db_conn)[user_id.hex])[0]
    except IndexError:
        return False

    user_schema = schemas.User.from_orm(user)

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
        user.feed_ids = list(source)
    elif item_type == "collection":
        user.collection_ids = list(source)

    user.store(db_conn)

    return True


def create_feed(
    feed_params: schemas.FeedCreate,
    name: str,
    owner: UUID | None = None,
) -> schemas.Feed:

    feed = models.Feed(
        **feed_params.dict(exclude_none=True), name=name, _id=uuid4().hex
    )

    if owner:
        feed.owner = owner

    feed.store(db_conn)

    return schemas.Feed.from_orm(feed)


def create_collection(
    name: str,
    owner: UUID | None = None,
    ids: list[str] | None = None,
) -> schemas.Collection:

    collection = models.Collection(name=name, _id=uuid4().hex)

    if owner:
        collection.owner = owner
    if ids:
        collection.ids = ids

    collection.store(db_conn)

    return schemas.Collection.from_orm(collection)


def get_feed_list(user: schemas.UserBase) -> list[schemas.ItemBase]:
    all_feeds: ViewResults = models.Feed.get_minimal_info(db_conn)

    # Manually setting a list of keys to retrieve, as the library itself doesn't expose this functionallity
    all_feeds.options["keys"] = user.feed_ids

    return [schemas.Feed.from_orm(feed) for feed in all_feeds]


def get_feeds(user: schemas.UserBase) -> dict[str, schemas.Feed]:
    all_feeds: ViewResults = models.Feed.all(db_conn)

    # Manually setting a list of keys to retrieve, as the library itself doesn't expose this functionallity
    all_feeds.options["keys"] = user.feed_ids

    return {feed._id: schemas.Feed.from_orm(feed) for feed in list(all_feeds)}


# Has to verify the user owns the item before deletion
def remove_item(
    user: schemas.UserBase,
    id: str,
    item_type: Literal["feed", "collection"],
) -> bool:
    if item_type == "feed":
        source = models.Feed
    elif item_type == "collection":
        source = models.Collection

    try:
        item: models.Collection | models.Feed = list(
            source.get_minimal_info(db_conn)[id]
        )[0]
    except IndexError:
        # Indicates that the item no longer exists
        return True

    if item.owner != user.id.hex:
        return False

    try:
        db_conn.delete(item)
    except ResourceConflict:
        return False

    return True
