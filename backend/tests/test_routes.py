"""HTTP route tests: FastAPI test client over moto (a local fake of DynamoDB)."""

from datetime import UTC, datetime

import boto3
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
    assert [s["id"] for s in client.get("/songs").json()["items"]] == [song["id"]]

    updated = client.put(f"/songs/{song['id']}", json={"title": "New", "body": "x"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "New"
    assert updated.json()["created_at"] == song["created_at"]

    assert client.delete(f"/songs/{song['id']}").status_code == 204
    assert client.get(f"/songs/{song['id']}").status_code == 404
    assert client.get("/songs").json()["items"] == []


def test_invalid_song_is_rejected_with_422():
    sign_in_as("alice")
    assert client.post("/songs", json={"title": ""}).status_code == 422
    assert client.post("/songs", json={}).status_code == 422
    assert client.get("/songs").json()["items"] == []


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
    assert [f["id"] for f in client.get("/fragments").json()["items"]] == [
        fragment["id"]
    ]

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
    assert client.get("/songs").json()["items"] == []
    assert client.get("/fragments").json()["items"] == []
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
    assert [s["title"] for s in client.get("/songs").json()["items"]] == ["Bobs"]


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
    bobs = client.get("/search", params={"q": "river"}).json()
    assert (bobs["songs"], bobs["fragments"]) == ([], [])
    assert (bobs["song_total"], bobs["fragment_total"]) == (0, 0)


def test_search_route_validates_its_parameters():
    sign_in_as("alice")
    assert client.get("/search", params={"q": "x" * 101}).status_code == 422
    assert client.get("/search", params={"q": "a", "scope": "nope"}).status_code == 422
    too_many = [("tag", f"t{i}") for i in range(11)]
    assert client.get("/search", params=too_many).status_code == 422


def test_search_with_nothing_to_look_for_returns_empty_results():
    sign_in_as("alice")
    client.post("/songs", json={"title": "River Song"})
    empty = {"songs": [], "fragments": [], "song_total": 0, "fragment_total": 0}
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
    secret = client.get("/search", params={"tag": "secret"}).json()
    assert (secret["songs"], secret["fragments"]) == ([], [])
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


# --- Paged lists ---


def _add_fragments(count: int, **fields) -> list[dict]:
    return [
        client.post("/fragments", json={"text": f"line {i}", **fields}).json()
        for i in range(count)
    ]


def test_fragment_list_is_paged_newest_first_with_totals():
    sign_in_as("alice")
    made = _add_fragments(45)
    first = client.get("/fragments").json()
    assert (
        first["total"],
        first["all_count"],
        first["page"],
        first["pages"],
        first["page_size"],
    ) == (45, 45, 1, 3, 20)
    assert [f["id"] for f in first["items"]] == [f["id"] for f in reversed(made)][:20]

    last = client.get("/fragments", params={"page": 3}).json()
    assert len(last["items"]) == 5
    assert [f["id"] for f in last["items"]] == [f["id"] for f in reversed(made)][40:]


def test_list_page_beyond_the_end_returns_the_last_page():
    sign_in_as("alice")
    _add_fragments(25)
    far = client.get("/fragments", params={"page": 99}).json()
    assert (far["page"], far["pages"], len(far["items"])) == (2, 2, 5)


def test_list_sort_oldest_first():
    sign_in_as("alice")
    made = _add_fragments(3)
    oldest = client.get("/fragments", params={"sort": "oldest"}).json()["items"]
    assert [f["id"] for f in oldest] == [f["id"] for f in made]


def test_list_filters_by_words_and_tags_and_reports_totals():
    sign_in_as("alice")
    client.post(
        "/fragments", json={"text": "rain on glass", "tags": ["rain", "window"]}
    )
    client.post("/fragments", json={"text": "rain on tin", "tags": ["rain"]})
    client.post("/fragments", json={"text": "sunny day", "tags": ["sun"]})

    by_tag = client.get("/fragments", params=[("tag", "rain")]).json()
    assert (by_tag["total"], by_tag["all_count"]) == (2, 3)

    both = client.get("/fragments", params=[("tag", "rain"), ("tag", "window")]).json()
    assert [f["text"] for f in both["items"]] == ["rain on glass"]

    by_words = client.get("/fragments", params={"q": "tin"}).json()
    assert [f["text"] for f in by_words["items"]] == ["rain on tin"]


def test_list_year_filter_and_year_counts():
    sign_in_as("alice")
    old = client.post("/fragments", json={"text": "old one"}).json()
    client.post("/fragments", json={"text": "new one"})
    this_year = datetime.now(UTC).year

    # Make one fragment look like it was written in 2019.
    boto3.resource("dynamodb").Table("test-table").update_item(
        Key={"PK": "USER#alice", "SK": f"FRAG#{old['id']}"},
        UpdateExpression="SET created_at = :c",
        ExpressionAttributeValues={":c": "2019-05-01T00:00:00+00:00"},
    )

    everything = client.get("/fragments").json()
    assert [(y["year"], y["count"]) for y in everything["years"]] == [
        (this_year, 1),
        (2019, 1),
    ]

    only_2019 = client.get("/fragments", params={"year": 2019}).json()
    assert [f["text"] for f in only_2019["items"]] == ["old one"]
    # The year list ignores the year filter, so the other years stay visible.
    assert len(only_2019["years"]) == 2

    # The oldest fragment sorts by its created_at, not by when its ID was made.
    oldest_first = client.get("/fragments", params={"sort": "oldest"}).json()["items"]
    assert [f["text"] for f in oldest_first] == ["old one", "new one"]


def test_song_list_is_paged_and_filterable():
    sign_in_as("alice")
    for i in range(23):
        client.post(
            "/songs",
            json={"title": f"Song {i}", "tags": ["even" if i % 2 == 0 else "odd"]},
        )
    first = client.get("/songs").json()
    assert (first["total"], first["pages"], len(first["items"])) == (23, 2, 20)
    evens = client.get("/songs", params=[("tag", "even")]).json()
    assert evens["total"] == 12


def test_list_parameters_are_validated():
    sign_in_as("alice")
    assert client.get("/fragments", params={"page": 0}).status_code == 422
    assert client.get("/fragments", params={"page_size": 101}).status_code == 422
    assert client.get("/fragments", params={"sort": "sideways"}).status_code == 422
    assert client.get("/fragments", params={"year": "abc"}).status_code == 422
    assert client.get("/fragments", params={"q": "x" * 101}).status_code == 422
    assert client.get("/fragments", params={"surprise": "1"}).status_code == 422
    too_many = [("tag", f"t{i}") for i in range(11)]
    assert client.get("/fragments", params=too_many).status_code == 422


def test_search_returns_a_limited_first_batch_with_full_totals():
    sign_in_as("alice")
    _add_fragments(30, tags=["bulk"])
    found = client.get("/search", params={"tag": "bulk", "scope": "fragments"}).json()
    assert len(found["fragments"]) == 20
    assert found["fragment_total"] == 30


# --- Mixed list of songs and fragments (Home) ---


def test_notebook_mixes_songs_and_fragments_newest_first_with_a_kind_on_each():
    sign_in_as("alice")
    song = client.post("/songs", json={"title": "A Song", "tags": ["rain"]}).json()
    fragment = client.post(
        "/fragments", json={"text": "a fragment", "tags": ["rain"]}
    ).json()

    both = client.get("/notebook").json()
    assert [(e["kind"], e["id"]) for e in both["items"]] == [
        ("fragment", fragment["id"]),
        ("song", song["id"]),
    ]
    assert (both["total"], both["all_count"], both["pages"]) == (2, 2, 1)
    assert both["items"][0]["text"] == "a fragment"
    assert both["items"][1]["title"] == "A Song"


def test_notebook_scope_limits_the_kinds_and_counts():
    sign_in_as("alice")
    client.post("/songs", json={"title": "A Song"})
    client.post("/fragments", json={"text": "one"})
    client.post("/fragments", json={"text": "two"})

    songs = client.get("/notebook", params={"scope": "songs"}).json()
    assert [e["kind"] for e in songs["items"]] == ["song"]
    assert (songs["total"], songs["all_count"]) == (1, 1)

    fragments = client.get("/notebook", params={"scope": "fragments"}).json()
    assert [e["kind"] for e in fragments["items"]] == ["fragment", "fragment"]

    assert client.get("/notebook", params={"scope": "nope"}).status_code == 422


def test_notebook_filters_by_words_tags_year_and_pages():
    sign_in_as("alice")
    for i in range(15):
        client.post(
            "/songs",
            json={"title": f"Song {i}", "tags": ["even" if i % 2 == 0 else "odd"]},
        )
    for i in range(15):
        client.post(
            "/fragments",
            json={"text": f"line {i}", "tags": ["even" if i % 2 == 0 else "odd"]},
        )

    first = client.get("/notebook").json()
    assert (first["total"], first["pages"], len(first["items"])) == (30, 2, 20)

    evens = client.get("/notebook", params=[("tag", "even")]).json()
    assert evens["total"] == 16
    assert {e["kind"] for e in evens["items"]} == {"song", "fragment"}

    words = client.get("/notebook", params={"q": "song 7"}).json()
    assert [e["title"] for e in words["items"]] == ["Song 7"]

    this_year = datetime.now(UTC).year
    assert client.get("/notebook", params={"year": this_year}).json()["total"] == 30
    assert client.get("/notebook", params={"year": 1999}).json()["total"] == 0


def test_notebook_only_shows_my_items_and_requires_a_login():
    sign_in_as("alice")
    client.post("/songs", json={"title": "Mine"})
    client.post("/fragments", json={"text": "mine"})
    sign_in_as("bob")
    bobs = client.get("/notebook").json()
    assert (bobs["items"], bobs["total"], bobs["all_count"]) == ([], 0, 0)

    app.dependency_overrides.clear()
    assert client.get("/notebook").status_code == 401
