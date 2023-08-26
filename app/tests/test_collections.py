from uuid import uuid4
from fastapi.encoders import jsonable_encoder
import pytest

from app.users.schemas import Collection

from . import client


def create_collection(content: list[str], name: str) -> tuple[str, Collection]:
    r = client.post(f"/my/collections/{name}", json=content)
    assert r.status_code == 201

    for collection_id, collection_content in r.json().items():
        if collection_content["name"] == name:
            collection = Collection(**collection_content)
            assert collection.ids == set(content)

            return collection_id, collection
    else:
        assert False


def modify_collection(id: str, collection: Collection | list[str]) -> None:
    if isinstance(collection, Collection):
        r = client.put(f"/user-items/collection/{id}", json=list(collection.ids))
    elif isinstance(collection, list):
        r = client.put(f"/user-items/collection/{id}", json=collection)
    else:
        raise NotImplementedError

    assert r.status_code == 200


def confirm_content(id: str, content: list[str]) -> None:
    r = client.get("/my/collections/list")
    assert r.status_code == 200

    assert set(r.json()[id]["ids"]) == set(content)


def confirm_presence(id: str, collection: Collection) -> None:
    r = client.get(f"/my/collections/list")
    assert r.status_code == 200

    online_collection = Collection(**r.json()[id])

    assert online_collection.dict() == collection.dict()


def confirm_empty() -> None:
    r = client.get("/my/collections/list")
    assert r.status_code == 200
    assert r.json() == {}


def delete_collection(collection_id: str) -> None:
    r = client.delete(f"/user-items/{collection_id}")
    assert r.status_code == 204


@pytest.fixture
def new_collections(auth_user, get_collections):
    collections: list[list[str]] = get_collections()

    new_collections: dict[str, Collection] = {}

    for content in collections:
        id, collection = create_collection(content, uuid4().hex)
        new_collections[id] = collection

    yield new_collections

    for id in new_collections.keys():
        delete_collection(id)


class TestCollections:
    def test_empty(self, auth_user):
        confirm_empty()

    def test_collection_creation_and_deletion(
        self, new_collections: dict[str, Collection]
    ):
        for id, collection in new_collections.items():
            confirm_presence(id, collection)

    def test_collection_modification(
        self, new_collections: dict[str, Collection], get_collections
    ):
        post_mod_collections: dict[str, list[str]] = {}

        for id in new_collections.keys():
            post_mod_collections[id] = get_collections(n=1)[0]

        for id, collection in post_mod_collections.items():
            modify_collection(id, collection)

        for id, collection in post_mod_collections.items():
            confirm_content(id, collection)

    def test_collection_renaming(self, new_collections: dict[str, Collection]):
        collection_names: dict[str, str] = {}

        for id in new_collections.keys():
            collection_names[id] = uuid4().hex

        for id, new_name in collection_names.items():
            r = client.put(f"/user-items/{id}/name?new_name={new_name}")
            assert r.status_code == 200

        r = client.get("/my/collections/list")
        assert r.status_code == 200
        json = r.json()

        for id, new_name in collection_names.items():
            assert json[id]["name"] == new_name
