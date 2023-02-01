from typing import Literal
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from couchdb import Database
from couchdb.client import ViewResults

from . import get_db_conn, models

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


