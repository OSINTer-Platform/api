from uuid import uuid4

from fastapi.encoders import jsonable_encoder
import pytest

from app.users.schemas import FeedCreate

from . import client


def create_feed(feed: FeedCreate, name: str) -> tuple[str, dict[str, str]]:
    r = client.post(f"/my/feeds/{name}", json=jsonable_encoder(feed))
    assert r.status_code == 201

    for feed_id, feed_content in r.json().items():
        if feed_content["name"] == name:
            assert feed_content == {
                **jsonable_encoder(feed),
                "_id": feed_id,
                "name": name,
                "owner": feed_content["owner"],
            }

            return feed_id, feed_content

    else:
        assert False


def modify_feed(feed_id: str, feed_content: FeedCreate | dict[str, str]) -> None:
    if isinstance(feed_content, dict):
        content = feed_content
    elif isinstance(feed_content, FeedCreate):
        content = jsonable_encoder(feed_content)
    else:
        raise NotImplementedError

    r = client.put(f"/user-items/feed/{feed_id}", json=content)
    assert r.status_code == 200


def confirm_precense(feed_id: str, feed_content: dict[str, str] | FeedCreate) -> None:
    r = client.get(f"/my/feeds/list")

    assert r.status_code == 200

    if isinstance(feed_content, FeedCreate):
        online_feed = r.json()[feed_id]
        assert online_feed == {
            **jsonable_encoder(feed_content),
            "_id": feed_id,
            "name": online_feed["name"],
            "owner": online_feed["owner"],
        }
    elif isinstance(feed_content, dict):
        assert r.json()[feed_id] == feed_content
    else:
        raise NotImplementedError


def confirm_empty():
    r = client.get("/my/feeds/list")
    assert r.status_code == 200
    assert r.json() == {}


def delete_feed(feed_id: str) -> None:
    r = client.delete(f"/user-items/{feed_id}")

    assert r.status_code == 204


@pytest.fixture
def new_feeds(auth_user, get_feeds):
    feeds: list[FeedCreate] = get_feeds()

    new_feeds: dict[str, dict[str, str]] = {}

    for feed in feeds:
        feed_id, feed_content = create_feed(feed, uuid4().hex)
        new_feeds[feed_id] = feed_content

    yield new_feeds

    for feed_id in new_feeds.keys():
        delete_feed(feed_id)

    confirm_empty()


class TestFeeds:
    def test_empty(self, auth_user):
        confirm_empty()

    def test_feed_creation_and_deletion(self, new_feeds: dict[str, dict[str, str]]):

        for feed_id, feed_content in new_feeds.items():
            confirm_precense(feed_id, feed_content)

    def test_feed_modification(self, get_feeds, new_feeds: dict[str, dict[str, str]]):

        post_mod_feeds: dict[str, FeedCreate] = {}

        for feed_id in new_feeds.keys():
            post_mod_feeds[feed_id] = get_feeds(1)[0]

        for feed_id, feed_content in post_mod_feeds.items():
            modify_feed(feed_id, feed_content)

        for feed_id, feed_content in post_mod_feeds.items():
            confirm_precense(feed_id, feed_content)

    def test_feed_renaming(self, new_feeds: dict[str, dict[str, str]]):

        feed_names: dict[str, str] = {}

        for feed_id in new_feeds.keys():
            feed_names[feed_id] = uuid4().hex

        for feed_id, new_name in feed_names.items():
            r = client.put(f"/user-items/{feed_id}/name?new_name={new_name}")
            assert r.status_code == 200

        r = client.get("/my/feeds/list")
        assert r.status_code == 200
        json = r.json()

        for feed_id, new_name in feed_names.items():
            assert json[feed_id]["name"] == new_name
