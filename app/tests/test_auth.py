from uuid import uuid4
from . import client

test_user = {"username": uuid4().hex, "password": uuid4().hex}


def test_signup():
    response = client.post("/auth/signup", data=test_user)
    assert response.status_code == 201
    assert response.json() == {"status": "success", "msg": "User created"}


def test_login():
    assert client.post("/auth/login", data=test_user).status_code == 200


def test_status():
    assert client.get("/auth/status").status_code == 200


def test_logout():
    assert client.post("/auth/logout").status_code == 200
