from collections.abc import Callable
from uuid import uuid4

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
