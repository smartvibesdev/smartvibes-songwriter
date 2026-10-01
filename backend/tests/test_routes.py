"""HTTP route tests: FastAPI test client over moto (a local fake of DynamoDB)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_claims

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_table_and_no_overrides(dynamodb_table):
    yield
    app.dependency_overrides.clear()


def sign_in_as(sub: str) -> None:
    app.dependency_overrides[get_claims] = lambda: {"sub": sub}


# --- Authentication ---


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/songs"),
        ("POST", "/songs"),
        ("GET", "/songs/x"),
        ("PUT", "/songs/x"),
        ("DELETE", "/songs/x"),
        ("GET", "/fragments"),
        ("POST", "/fragments"),
        ("GET", "/fragments/x"),
        ("PUT", "/fragments/x"),
        ("DELETE", "/fragments/x"),
    ],
)
def test_every_data_route_requires_authentication(method, path):
    assert client.request(method, path, json={}).status_code == 401


# --- Songs ---


def test_song_lifecycle():
    sign_in_as("alice")
    created = client.post("/songs", json={"title": "Blue Door", "body": "la la"})
    assert created.status_code == 201
    song = created.json()
    assert song["title"] == "Blue Door"
    assert {"id", "created_at", "updated_at"} <= song.keys()

    assert client.get(f"/songs/{song['id']}").json() == song
    assert [s["id"] for s in client.get("/songs").json()] == [song["id"]]

    updated = client.put(f"/songs/{song['id']}", json={"title": "New", "body": "x"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "New"
    assert updated.json()["created_at"] == song["created_at"]

    assert client.delete(f"/songs/{song['id']}").status_code == 204
    assert client.get(f"/songs/{song['id']}").status_code == 404
    assert client.get("/songs").json() == []


def test_invalid_song_is_rejected_with_422():
    sign_in_as("alice")
    assert client.post("/songs", json={"title": ""}).status_code == 422
    assert client.post("/songs", json={}).status_code == 422
    assert client.get("/songs").json() == []


def test_missing_song_returns_404():
    sign_in_as("alice")
    assert client.get("/songs/nope").status_code == 404
    assert client.put("/songs/nope", json={"title": "x"}).status_code == 404
    assert client.delete("/songs/nope").status_code == 404


# --- Fragments ---


def test_fragment_lifecycle_with_tags():
    sign_in_as("alice")
    created = client.post(
        "/fragments", json={"text": "a line", "tags": ["Love", "love"]}
    )
    assert created.status_code == 201
    fragment = created.json()
    assert fragment["tags"] == ["love"]

    assert client.get(f"/fragments/{fragment['id']}").json() == fragment
    assert [f["id"] for f in client.get("/fragments").json()] == [fragment["id"]]

    updated = client.put(
        f"/fragments/{fragment['id']}", json={"text": "new", "tags": ["a"]}
    )
    assert updated.status_code == 200
    assert (updated.json()["text"], updated.json()["tags"]) == ("new", ["a"])

    assert client.delete(f"/fragments/{fragment['id']}").status_code == 204
    assert client.get(f"/fragments/{fragment['id']}").status_code == 404


def test_invalid_fragment_is_rejected_with_422():
    sign_in_as("alice")
    assert client.post("/fragments", json={"text": " "}).status_code == 422
    too_many_tags = [f"t{i}" for i in range(11)]
    response = client.post("/fragments", json={"text": "ok", "tags": too_many_tags})
    assert response.status_code == 422


# --- Ownership: the user ID comes only from the token ---


def test_other_user_gets_404_and_empty_lists():
    sign_in_as("alice")
    song = client.post("/songs", json={"title": "Mine"}).json()
    fragment = client.post("/fragments", json={"text": "Mine"}).json()

    sign_in_as("bob")
    assert client.get("/songs").json() == []
    assert client.get("/fragments").json() == []
    assert client.get(f"/songs/{song['id']}").status_code == 404
    assert client.get(f"/fragments/{fragment['id']}").status_code == 404
    assert (
        client.put(f"/songs/{song['id']}", json={"title": "Hijacked"}).status_code
        == 404
    )
    assert (
        client.put(
            f"/fragments/{fragment['id']}", json={"text": "Hijacked"}
        ).status_code
        == 404
    )
    assert client.delete(f"/songs/{song['id']}").status_code == 404
    assert client.delete(f"/fragments/{fragment['id']}").status_code == 404

    sign_in_as("alice")
    assert client.get(f"/songs/{song['id']}").json()["title"] == "Mine"
    assert client.get(f"/fragments/{fragment['id']}").json()["text"] == "Mine"


def test_a_user_id_in_the_body_or_query_is_ignored():
    sign_in_as("alice")
    client.post("/songs", json={"title": "Mine"})
    sign_in_as("bob")
    created = client.post(
        "/songs?user_id=alice", json={"title": "Bobs", "user_id": "alice"}
    )
    assert created.status_code == 201
    assert [s["title"] for s in client.get("/songs?user_id=alice").json()] == ["Bobs"]


# --- Through the real Lambda handler ---


def test_create_song_through_lambda_handler():
    """Full path: an API Gateway (HTTP API v2) event with authorizer claims."""
    import json

    from app.main import handler

    event = {
        "version": "2.0",
        "routeKey": "POST /songs",
        "rawPath": "/songs",
        "rawQueryString": "",
        "headers": {
            "host": "example.execute-api.us-east-1.amazonaws.com",
            "content-type": "application/json",
        },
        "requestContext": {
            "http": {"method": "POST", "path": "/songs", "sourceIp": "1.2.3.4"},
            "authorizer": {"jwt": {"claims": {"sub": "alice"}}},
        },
        "body": json.dumps({"title": "Via Lambda"}),
        "isBase64Encoded": False,
    }
    result = handler(event, None)
    assert result["statusCode"] == 201
    assert json.loads(result["body"])["title"] == "Via Lambda"


# --- Search ---


def test_search_route_finds_my_items_only():
    sign_in_as("alice")
    client.post("/songs", json={"title": "River Song"})
    client.post("/fragments", json={"text": "down by the river", "tags": ["water"]})
    found = client.get("/search", params={"q": "river"})
    assert found.status_code == 200
    assert [s["title"] for s in found.json()["songs"]] == ["River Song"]
    assert [f["text"] for f in found.json()["fragments"]] == ["down by the river"]

    sign_in_as("bob")
    assert client.get("/search", params={"q": "river"}).json() == {
        "songs": [],
        "fragments": [],
    }


def test_search_route_validates_the_query():
    sign_in_as("alice")
    assert client.get("/search").status_code == 422
    assert client.get("/search", params={"q": ""}).status_code == 422
    assert client.get("/search", params={"q": "x" * 101}).status_code == 422
    blank = client.get("/search", params={"q": "   "})
    assert blank.status_code == 200
    assert blank.json() == {"songs": [], "fragments": []}


def test_search_requires_authentication():
    assert client.get("/search", params={"q": "river"}).status_code == 401
