"""Service-layer tests against moto, a local fake of DynamoDB. No real AWS is used."""

import pytest

from app import service
from app.models import FragmentIn, SongIn

ALICE = "alice-sub"
BOB = "bob-sub"


pytestmark = pytest.mark.usefixtures("dynamodb_table")


# --- Songs ---


def test_create_and_get_song():
    created = service.create_song(ALICE, SongIn(title="Blue Door", body="la la"))
    fetched = service.get_song(ALICE, created.id)
    assert fetched == created
    assert fetched.title == "Blue Door"
    assert fetched.body == "la la"


def test_list_songs_returns_newest_first():
    first = service.create_song(ALICE, SongIn(title="First"))
    second = service.create_song(ALICE, SongIn(title="Second"))
    assert [s.id for s in service.list_songs(ALICE)] == [second.id, first.id]


def test_update_song_changes_fields_and_keeps_created_at():
    created = service.create_song(ALICE, SongIn(title="Old", body="old"))
    updated = service.update_song(ALICE, created.id, SongIn(title="New", body="new"))
    assert (updated.title, updated.body) == ("New", "new")
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at
    assert service.get_song(ALICE, created.id) == updated


def test_delete_song_removes_it():
    created = service.create_song(ALICE, SongIn(title="Gone"))
    service.delete_song(ALICE, created.id)
    assert service.list_songs(ALICE) == []
    with pytest.raises(service.NotFoundError):
        service.get_song(ALICE, created.id)


def test_missing_song_raises_not_found():
    with pytest.raises(service.NotFoundError):
        service.get_song(ALICE, "nope")
    with pytest.raises(service.NotFoundError):
        service.update_song(ALICE, "nope", SongIn(title="x"))
    with pytest.raises(service.NotFoundError):
        service.delete_song(ALICE, "nope")


def test_updating_a_missing_song_does_not_create_it():
    with pytest.raises(service.NotFoundError):
        service.update_song(ALICE, "nope", SongIn(title="x"))
    assert service.list_songs(ALICE) == []


# --- Fragments ---


def test_create_and_get_fragment_with_tags():
    created = service.create_fragment(ALICE, FragmentIn(text="a line", tags=["Love"]))
    fetched = service.get_fragment(ALICE, created.id)
    assert fetched == created
    assert fetched.tags == ["love"]


def test_fragment_with_no_tags_round_trips():
    created = service.create_fragment(ALICE, FragmentIn(text="a line"))
    assert service.get_fragment(ALICE, created.id).tags == []


def test_list_fragments_returns_newest_first():
    first = service.create_fragment(ALICE, FragmentIn(text="one"))
    second = service.create_fragment(ALICE, FragmentIn(text="two"))
    assert [f.id for f in service.list_fragments(ALICE)] == [second.id, first.id]


def test_update_fragment():
    created = service.create_fragment(ALICE, FragmentIn(text="old", tags=["a"]))
    updated = service.update_fragment(
        ALICE, created.id, FragmentIn(text="new", tags=["b", "c"])
    )
    assert (updated.text, updated.tags) == ("new", ["b", "c"])
    assert updated.created_at == created.created_at


def test_delete_fragment():
    created = service.create_fragment(ALICE, FragmentIn(text="gone"))
    service.delete_fragment(ALICE, created.id)
    assert service.list_fragments(ALICE) == []


def test_songs_and_fragments_are_listed_separately():
    service.create_song(ALICE, SongIn(title="A song"))
    service.create_fragment(ALICE, FragmentIn(text="A fragment"))
    assert len(service.list_songs(ALICE)) == 1
    assert len(service.list_fragments(ALICE)) == 1


def test_a_song_id_is_not_found_as_a_fragment():
    song = service.create_song(ALICE, SongIn(title="A song"))
    with pytest.raises(service.NotFoundError):
        service.get_fragment(ALICE, song.id)


# --- Ownership: one user must never reach another user's data ---


def test_other_user_cannot_see_my_songs_or_fragments():
    song = service.create_song(ALICE, SongIn(title="Mine"))
    fragment = service.create_fragment(ALICE, FragmentIn(text="Mine"))
    assert service.list_songs(BOB) == []
    assert service.list_fragments(BOB) == []
    with pytest.raises(service.NotFoundError):
        service.get_song(BOB, song.id)
    with pytest.raises(service.NotFoundError):
        service.get_fragment(BOB, fragment.id)


def test_other_user_cannot_edit_or_delete_my_items():
    song = service.create_song(ALICE, SongIn(title="Mine"))
    fragment = service.create_fragment(ALICE, FragmentIn(text="Mine"))
    with pytest.raises(service.NotFoundError):
        service.update_song(BOB, song.id, SongIn(title="Hijacked"))
    with pytest.raises(service.NotFoundError):
        service.update_fragment(BOB, fragment.id, FragmentIn(text="Hijacked"))
    with pytest.raises(service.NotFoundError):
        service.delete_song(BOB, song.id)
    with pytest.raises(service.NotFoundError):
        service.delete_fragment(BOB, fragment.id)
    # Alice's data is untouched, and nothing was created in Bob's partition.
    assert service.get_song(ALICE, song.id).title == "Mine"
    assert service.get_fragment(ALICE, fragment.id).text == "Mine"
    assert service.list_songs(BOB) == []
    assert service.list_fragments(BOB) == []


# --- Search ---


def _titles(results):
    return sorted(s.title for s in results.songs)


def _texts(results):
    return sorted(f.text for f in results.fragments)


def test_search_matches_song_title_and_body_ignoring_case():
    service.create_song(ALICE, SongIn(title="Blue Door", body="walking home"))
    service.create_song(ALICE, SongIn(title="Other", body="nothing here"))
    assert _titles(service.search(ALICE, "BLUE")) == ["Blue Door"]
    assert _titles(service.search(ALICE, "walking")) == ["Blue Door"]


def test_search_matches_fragment_text_and_tags():
    service.create_fragment(
        ALICE, FragmentIn(text="rain on glass", tags=["Melancholy"])
    )
    service.create_fragment(ALICE, FragmentIn(text="sunny day"))
    assert _texts(service.search(ALICE, "rain")) == ["rain on glass"]
    assert _texts(service.search(ALICE, "melancholy")) == ["rain on glass"]


def test_search_needs_every_word_but_not_in_the_same_field():
    service.create_song(ALICE, SongIn(title="Blue Door", body="walking home"))
    service.create_song(ALICE, SongIn(title="Blue Sky", body="flying"))
    assert _titles(service.search(ALICE, "blue home")) == ["Blue Door"]
    assert _titles(service.search(ALICE, "blue missing")) == []


def test_search_covers_songs_and_fragments_together():
    service.create_song(ALICE, SongIn(title="River"))
    service.create_fragment(ALICE, FragmentIn(text="down by the river"))
    results = service.search(ALICE, "river")
    assert len(results.songs) == 1
    assert len(results.fragments) == 1


def test_blank_search_returns_nothing():
    service.create_song(ALICE, SongIn(title="River"))
    results = service.search(ALICE, "   ")
    assert results.songs == []
    assert results.fragments == []


def test_search_never_returns_another_users_items():
    service.create_song(ALICE, SongIn(title="Secret river"))
    service.create_fragment(ALICE, FragmentIn(text="secret river"))
    results = service.search(BOB, "river")
    assert results.songs == []
    assert results.fragments == []


# --- Song tags, search scope and tag filters ---


def test_song_tags_round_trip_and_update():
    created = service.create_song(ALICE, SongIn(title="T", tags=["Rain"]))
    assert service.get_song(ALICE, created.id).tags == ["rain"]
    updated = service.update_song(ALICE, created.id, SongIn(title="T", tags=["road"]))
    assert updated.tags == ["road"]


def test_a_song_saved_before_tags_existed_reads_as_untagged():
    import boto3

    boto3.resource("dynamodb").Table("test-table").put_item(
        Item={
            "PK": f"USER#{ALICE}",
            "SK": "SONG#old",
            "title": "Old",
            "body": "",
            "created_at": "2026-10-01T00:00:00+00:00",
            "updated_at": "2026-10-01T00:00:00+00:00",
        }
    )
    assert service.get_song(ALICE, "old").tags == []


def test_search_finds_songs_by_tag_text():
    service.create_song(ALICE, SongIn(title="Plain", body="nothing", tags=["rain"]))
    assert _titles(service.search(ALICE, "rain")) == ["Plain"]


def test_search_scope_limits_the_kinds_returned():
    service.create_song(ALICE, SongIn(title="River"))
    service.create_fragment(ALICE, FragmentIn(text="river"))
    both = service.search(ALICE, "river", scope="both")
    songs = service.search(ALICE, "river", scope="songs")
    fragments = service.search(ALICE, "river", scope="fragments")
    assert (len(both.songs), len(both.fragments)) == (1, 1)
    assert (len(songs.songs), len(songs.fragments)) == (1, 0)
    assert (len(fragments.songs), len(fragments.fragments)) == (0, 1)


def test_search_by_tag_alone_needs_every_tag():
    service.create_fragment(ALICE, FragmentIn(text="one", tags=["rain", "road"]))
    service.create_fragment(ALICE, FragmentIn(text="two", tags=["rain"]))
    assert _texts(service.search(ALICE, tags=["rain"])) == ["one", "two"]
    assert _texts(service.search(ALICE, tags=["Rain", " ROAD "])) == ["one"]
    assert _texts(service.search(ALICE, tags=["rain", "missing"])) == []


def test_search_combines_words_and_tags():
    service.create_fragment(ALICE, FragmentIn(text="blue door", tags=["home"]))
    service.create_fragment(ALICE, FragmentIn(text="blue sky", tags=["air"]))
    assert _texts(service.search(ALICE, "blue", tags=["home"])) == ["blue door"]


def test_search_with_no_words_and_no_tags_returns_nothing():
    service.create_fragment(ALICE, FragmentIn(text="x", tags=["a"]))
    assert service.search(ALICE, "", tags=[]).fragments == []
    assert service.search(ALICE, "  ", tags=["  "]).fragments == []


# --- Tag list ---


def test_list_tags_counts_and_orders_by_use_then_name():
    service.create_song(ALICE, SongIn(title="s", tags=["b", "a"]))
    service.create_fragment(ALICE, FragmentIn(text="f1", tags=["a", "c"]))
    service.create_fragment(ALICE, FragmentIn(text="f2", tags=["a"]))
    pairs = [(t.tag, t.count) for t in service.list_tags(ALICE)]
    assert pairs == [("a", 3), ("b", 1), ("c", 1)]
    assert [(t.tag, t.count) for t in service.list_tags(ALICE, "songs")] == [
        ("a", 1),
        ("b", 1),
    ]
    assert [(t.tag, t.count) for t in service.list_tags(ALICE, "fragments")] == [
        ("a", 2),
        ("c", 1),
    ]


def test_list_tags_is_empty_with_no_tags_and_isolated_by_user():
    service.create_song(ALICE, SongIn(title="s"))
    service.create_fragment(BOB, FragmentIn(text="f", tags=["x"]))
    assert service.list_tags(ALICE) == []


# --- Random fragments ---


def test_random_fragments_returns_distinct_fragments_up_to_count():
    ids = {
        service.create_fragment(ALICE, FragmentIn(text=f"t{i}")).id for i in range(4)
    }
    picked = service.random_fragments(ALICE, count=3)
    assert len(picked) == 3
    assert len({f.id for f in picked}) == 3
    assert {f.id for f in picked} <= ids
    assert len(service.random_fragments(ALICE, count=10)) == 4


def test_random_fragments_is_empty_with_no_fragments_or_no_match():
    assert service.random_fragments(ALICE) == []
    service.create_fragment(ALICE, FragmentIn(text="x", tags=["a"]))
    assert service.random_fragments(ALICE, tag="b") == []


def test_random_fragments_never_returns_another_users_fragments():
    service.create_fragment(ALICE, FragmentIn(text="mine"))
    assert service.random_fragments(BOB) == []
