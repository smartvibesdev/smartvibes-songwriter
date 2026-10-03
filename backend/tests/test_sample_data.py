"""Tests for the generated sample data, on moto (a local fake of DynamoDB)."""

import boto3
import pytest

from app import service
from app.models import FragmentIn, SongIn
from sample_data import (
    PRIVATE_WORD,
    count_sample_data,
    delete_sample_data,
    looks_like_user_id,
    write_private_fragment,
    write_sample_data,
)

ALICE = "11111111-1111-4111-8111-111111111111"
BOB = "22222222-2222-4222-8222-222222222222"

pytestmark = pytest.mark.usefixtures("dynamodb_table")


def table():
    return boto3.resource("dynamodb").Table("test-table")


def test_generated_items_load_through_the_normal_service_layer():
    write_sample_data(table(), ALICE, fragments=40, songs=6)

    everything = service.query_notebook(ALICE, page_size=100)
    assert (everything.total, everything.all_count) == (46, 46)
    assert len(service.query_fragments(ALICE).items) == 20
    assert service.query_songs(ALICE).total == 6
    assert all(song.title and song.body for song in service.query_songs(ALICE).items)


def test_generated_items_are_spread_over_years_and_have_tags():
    write_sample_data(table(), ALICE, fragments=300, songs=20)

    page = service.query_fragments(ALICE)
    years = [entry.year for entry in page.years]
    assert min(years) >= 2018
    assert len(years) > 3
    assert len(service.list_tags(ALICE)) > 10


def test_every_generated_item_is_marked_as_sample():
    write_sample_data(table(), ALICE, fragments=10, songs=2)
    assert count_sample_data(table(), ALICE) == 12


def test_every_generated_item_has_the_sample_tag():
    write_sample_data(table(), ALICE, fragments=10, songs=3)

    sample_tag = service.list_tags(ALICE)[0]
    assert (sample_tag.tag, sample_tag.count) == ("sample", 13)
    assert all("sample" in item.tags for item in service.query_fragments(ALICE).items)
    assert all("sample" in item.tags for item in service.query_songs(ALICE).items)


def test_private_fragment_is_found_by_its_word_for_its_owner_only():
    write_sample_data(table(), ALICE, fragments=20, songs=2)
    write_private_fragment(table(), BOB)

    assert service.search(BOB, PRIVATE_WORD).fragment_total == 1
    assert service.search(ALICE, PRIVATE_WORD).fragment_total == 0
    assert count_sample_data(table(), BOB) == 1


def test_the_same_seed_gives_the_same_text():
    write_sample_data(table(), ALICE, fragments=15, songs=0, seed=3)
    write_sample_data(table(), BOB, fragments=15, songs=0, seed=3)
    alice = sorted(f.text for f in service.query_fragments(ALICE, page_size=100).items)
    bob = sorted(f.text for f in service.query_fragments(BOB, page_size=100).items)
    assert alice == bob


def test_delete_removes_only_generated_items_for_that_user():
    write_sample_data(table(), ALICE, fragments=30, songs=5)
    write_sample_data(table(), BOB, fragments=7, songs=1)
    my_fragment = service.create_fragment(ALICE, FragmentIn(text="written by hand"))
    my_song = service.create_song(ALICE, SongIn(title="Also by hand"))

    assert delete_sample_data(table(), ALICE) == 35

    assert count_sample_data(table(), ALICE) == 0
    assert service.get_fragment(ALICE, my_fragment.id).text == "written by hand"
    assert service.get_song(ALICE, my_song.id).title == "Also by hand"
    assert service.query_notebook(ALICE).total == 2
    # Bob's generated items are untouched.
    assert count_sample_data(table(), BOB) == 8


def test_delete_with_nothing_to_delete_does_nothing():
    assert delete_sample_data(table(), ALICE) == 0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (ALICE, True),
        ("b41804d8-e041-700a-afd7-182de83e46d7", True),
        ("", False),
        ("alice", False),
        ("USER#" + ALICE, False),
        (ALICE + "x", False),
        (" " + ALICE, False),
    ],
)
def test_user_id_check(text, expected):
    assert looks_like_user_id(text) is expected
