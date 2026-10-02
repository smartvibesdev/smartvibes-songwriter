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


def test_search_route_validates_its_parameters():
    sign_in_as("alice")
    assert client.get("/search", params={"q": "x" * 101}).status_code == 422
    assert client.get("/search", params={"q": "a", "scope": "nope"}).status_code == 422
    too_many = [("tag", f"t{i}") for i in range(11)]
    assert client.get("/search", params=too_many).status_code == 422


def test_search_with_nothing_to_look_for_returns_empty_results():
    sign_in_as("alice")
    client.post("/songs", json={"title": "River Song"})
    empty = {"songs": [], "fragments": []}
    assert client.get("/search").json() == empty
    assert client.get("/search", params={"q": ""}).json() == empty
    assert client.get("/search", params={"q": "   "}).json() == empty


def test_search_requires_authentication():
    assert client.get("/search", params={"q": "river"}).status_code == 401


# --- Search scope and tags ---


def test_search_route_scope_and_tag_filters():
    sign_in_as("alice")
    client.post("/songs", json={"title": "River Song", "tags": ["Water"]})
    client.post(
        "/fragments", json={"text": "down by the river", "tags": ["water", "calm"]}
    )
    client.post("/fragments", json={"text": "river of cars", "tags": ["city"]})

    songs_only = client.get("/search", params={"q": "river", "scope": "songs"}).json()
    assert len(songs_only["songs"]) == 1
    assert songs_only["fragments"] == []

    fragments_only = client.get(
        "/search", params={"q": "river", "scope": "fragments"}
    ).json()
    assert fragments_only["songs"] == []
    assert len(fragments_only["fragments"]) == 2

    by_tag = client.get("/search", params={"tag": "water"}).json()
    assert len(by_tag["songs"]) == 1
    assert [f["text"] for f in by_tag["fragments"]] == ["down by the river"]

    both_tags = client.get("/search", params=[("tag", "water"), ("tag", "calm")]).json()
    assert both_tags["songs"] == []
    assert len(both_tags["fragments"]) == 1


# --- Tags ---


def test_songs_have_tags_that_are_cleaned_up():
    sign_in_as("alice")
    created = client.post(
        "/songs", json={"title": "Tagged", "tags": ["Rain ", "rain", "ROAD"]}
    )
    assert created.json()["tags"] == ["rain", "road"]
    assert client.get(f"/songs/{created.json()['id']}").json()["tags"] == [
        "rain",
        "road",
    ]


def test_tags_route_counts_tags_across_songs_and_fragments():
    sign_in_as("alice")
    client.post("/songs", json={"title": "A", "tags": ["rain", "road"]})
    client.post("/fragments", json={"text": "x", "tags": ["rain"]})
    client.post("/fragments", json={"text": "y", "tags": ["rain", "night"]})

    assert client.get("/tags").json() == [
        {"tag": "rain", "count": 3},
        {"tag": "night", "count": 1},
        {"tag": "road", "count": 1},
    ]
    assert client.get("/tags", params={"scope": "songs"}).json() == [
        {"tag": "rain", "count": 1},
        {"tag": "road", "count": 1},
    ]
    assert client.get("/tags", params={"scope": "nope"}).status_code == 422


def test_tags_and_search_only_cover_my_items():
    sign_in_as("alice")
    client.post("/fragments", json={"text": "mine", "tags": ["secret"]})
    sign_in_as("bob")
    assert client.get("/tags").json() == []
    assert client.get("/search", params={"tag": "secret"}).json() == {
        "songs": [],
        "fragments": [],
    }
    assert client.get("/fragments/random").json() == []


# --- Random fragments ---


def test_random_fragment_route_returns_one_of_my_fragments():
    sign_in_as("alice")
    ids = {
        client.post("/fragments", json={"text": f"line {i}"}).json()["id"]
        for i in range(3)
    }

    picked = client.get("/fragments/random")
    assert picked.status_code == 200
    assert len(picked.json()) == 1
    assert picked.json()[0]["id"] in ids


def test_random_fragment_route_is_not_mistaken_for_a_fragment_id():
    sign_in_as("alice")
    assert client.get("/fragments/random").status_code == 200
    assert client.get("/fragments/random").json() == []


def test_random_fragment_route_count_tag_and_exclude():
    sign_in_as("alice")
    rain = client.post("/fragments", json={"text": "rain one", "tags": ["rain"]}).json()
    client.post("/fragments", json={"text": "rain two", "tags": ["rain"]})
    client.post("/fragments", json={"text": "sun", "tags": ["sun"]})

    several = client.get("/fragments/random", params={"count": 10}).json()
    assert len(several) == 3
    assert len({f["id"] for f in several}) == 3

    tagged = client.get("/fragments/random", params={"count": 10, "tag": "Rain"}).json()
    assert {f["text"] for f in tagged} == {"rain one", "rain two"}

    for _ in range(10):
        other = client.get(
            "/fragments/random", params={"tag": "rain", "exclude": rain["id"]}
        )
        assert other.json()[0]["text"] == "rain two"

    assert client.get("/fragments/random", params={"count": 0}).status_code == 422
    assert client.get("/fragments/random", params={"count": 11}).status_code == 422


def test_random_fragment_still_returns_the_only_choice_when_it_is_excluded():
    sign_in_as("alice")
    only = client.post("/fragments", json={"text": "alone"}).json()
    picked = client.get("/fragments/random", params={"exclude": only["id"]}).json()
    assert [f["id"] for f in picked] == [only["id"]]


def test_new_routes_require_authentication():
    assert client.get("/tags").status_code == 401
    assert client.get("/fragments/random").status_code == 401
