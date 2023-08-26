from collections.abc import Callable
from uuid import uuid4
import string
import random

from pydantic_factories import ModelFactory
import pytest

from app.users.schemas import FeedCreate

from . import client


class FeedFactory(ModelFactory):
    __model__ = FeedCreate


@pytest.fixture
def auth_user():
    print("Authing!", end=" ")
    test_user = {"username": uuid4().hex, "password": uuid4().hex}

    for endpoint in ["signup", "login"]:
        client.post(f"/auth/{endpoint}", data=test_user)

    assert client.get("/auth/status").status_code == 200

    yield

    client.post("/auth/logout")


@pytest.fixture
def get_feeds() -> Callable[[int], list[FeedCreate]]:
    def _make_feed_list(n: int = 100) -> list[FeedCreate]:
        return [FeedFactory.build() for i in range(n)]

    return _make_feed_list


@pytest.fixture
def get_collections() -> Callable[[int, int], list[list[str]]]:
    def _make_collection_list(n: int = 1000, max_size: int = 100) -> list[list[str]]:
        collection_list = []

        for _ in range(n):
            collection = []

            for _ in range(random.randint(1, max_size)):
                collection.append(
                    "".join(
                        random.choice(string.ascii_uppercase + string.digits)
                        for _ in range(20)
                    )
                )

            collection_list.append(collection)

        return collection_list

    return _make_collection_list
