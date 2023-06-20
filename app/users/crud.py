from typing import Literal
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from couchdb import Document, ResourceNotFound
from couchdb.client import ViewResults
from fastapi.encoders import jsonable_encoder


from . import models, schemas, get_db_conn

ph = PasswordHasher()


def open_db_conn():
    global db_conn
    db_conn = get_db_conn()


try:
    open_db_conn()
except:
    pass


# Return of db model for user is for use in following crud functions
def verify_user(
    username: str,
    password: str | None = None,
    email: str | None = None,
) -> Literal[False] | models.User:
    users: ViewResults = models.User.auth_info(db_conn)[username]
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


def get_full_user_object(username: str, complete: bool = False) -> None | schemas.User:
    users: ViewResults = models.User.by_username(db_conn)[username]

    try:
        user: schemas.User = schemas.User.from_orm(list(users)[0])
    except IndexError:
        return None

    if complete:
        user.feeds = list(get_feeds(user).values())
        user.collections = list(get_collections(user).values())

    return user


# Ensures that usernames are unique
def create_user(
    username: str,
    password: str,
    email: str | None = "",
    id: UUID | None = None,
) -> bool:
    if verify_user(username):
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
    )

    collection = create_collection("Already Read", id, deleteable=False)
    new_user.already_read = collection.id

    new_user.store(db_conn)
    modify_user_subscription(id, set([collection.id]), "subscribe", "collection")

    return True


def remove_user(username: str) -> bool:
    user = verify_user(username)

    if user:
        del db_conn[user._id]

    return True


def modify_user_subscription(
    user_id: UUID,
    ids: set[UUID],
    action: Literal["subscribe", "unsubscribe"],
    item_type: Literal["feed", "collection"],
) -> models.User | None:
    try:
        user: models.User = list(models.User.all(db_conn)[str(user_id)])[0]
    except IndexError:
        return None

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
        user.feed_ids = jsonable_encoder(source)
    elif item_type == "collection":
        user.collection_ids = jsonable_encoder(source)

    user.store(db_conn)

    return user


def create_feed(
    feed_params: schemas.FeedCreate,
    name: str,
    owner: UUID | None = None,
    id: UUID | None = None,
    deleteable=True,
) -> schemas.Feed:
    if not id:
        id = uuid4()

    feed = models.Feed(
        name=name,
        _id=str(id),
        deleteable=deleteable,
        **feed_params.dict(),
    )

    if owner:
        feed.owner = str(owner)

    feed.store(db_conn)

    return schemas.Feed.from_orm(feed)


def create_collection(
    name: str,
    owner: UUID | None = None,
    id: UUID | None = None,
    ids: set[str] | None = None,
    deleteable=True,
) -> schemas.Collection:
    if not id:
        id = uuid4()

    collection = models.Collection(
        name=name,
        owner=str(owner),
        _id=str(id),
        deleteable=deleteable,
    )

    if owner:
        collection.owner = str(owner)
    if ids:
        collection.ids = list(ids)

    collection.store(db_conn)

    return schemas.Collection.from_orm(collection)


def get_feed_list(user: schemas.User) -> list[schemas.ItemBase]:
    all_feeds: ViewResults = models.Feed.get_minimal_info(db_conn)

    # Manually setting a list of keys to retrieve, as the library itself doesn't expose this functionallity
    all_feeds.options["keys"] = jsonable_encoder(user.feed_ids)

    return [schemas.Feed.from_orm(feed) for feed in all_feeds]


def get_feeds(user: schemas.User) -> dict[str, schemas.Feed]:
    all_feeds: ViewResults = models.Feed.all(db_conn)

    all_feeds.options["keys"] = jsonable_encoder(user.feed_ids)

    return {feed._id: schemas.Feed.from_orm(feed) for feed in list(all_feeds)}


def get_collections(user: schemas.User) -> dict[str, schemas.Collection]:
    all_collections: ViewResults = models.Collection.all(db_conn)

    all_collections.options["keys"] = jsonable_encoder(user.collection_ids)

    return {
        collection._id: schemas.Collection.from_orm(collection)
        for collection in all_collections
    }


def get_item(id: UUID) -> schemas.Feed | schemas.Collection | int:
    try:
        item: Document = db_conn[str(id)]
    except ResourceNotFound:
        return 404

    if item["type"] == "feed":
        return schemas.Feed(**dict(item))
    elif item["type"] == "collection":
        return schemas.Collection(**dict(item))
    else:
        return 404


def modify_feed(
    id: UUID, contents: schemas.FeedCreate, user: schemas.UserBase
) -> int | schemas.Feed:
    item: models.Feed | None = models.Feed.load(db_conn, str(id))

    if item is None or item.type != "feed":
        return 404
    elif item.owner != str(user.id):
        return 403

    for k, v in contents.dict(exclude_unset=True).items():
        setattr(item, k, v)

    item.store(db_conn)

    return schemas.Feed.from_orm(item)


def modify_collection(
    id: UUID, contents: set[str], user: schemas.UserBase
) -> int | schemas.Collection:
    item: models.Collection | None = models.Collection.load(db_conn, str(id))

    if item is None or item.type != "collection":
        return 404
    elif item.owner != str(user.id):
        return 403

    item.ids = list(contents)

    item.store(db_conn)

    return schemas.Collection.from_orm(item)


def change_item_name(id: UUID, new_name: str, user: schemas.UserBase) -> int | None:
    item: models.UserItem | None = models.UserItem.load(db_conn, str(id))

    if item is None or not item.type in ["feed", "collection"]:
        return 404
    elif item.owner != str(user.id):
        return 403

    item.name = new_name

    item.store(db_conn)


# Has to verify the user owns the item before deletion
def remove_item(
    user: schemas.UserBase,
    id: UUID,
) -> int | None:
    try:
        item = db_conn[str(id)]
    except ResourceNotFound:
        return

    if item["type"] not in ["feed", "collection"]:
        return 404
    elif item["owner"] != str(user.id):
        return 403
    elif not item["deleteable"]:
        return 422

    del db_conn[str(id)]

    return
