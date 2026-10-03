"""The plain mixed list (no words or tags) reads only what it needs. It must give the same answer
as the version that loads everything, so each test compares the two on the same data."""

import boto3
import pytest

from app import service
from sample_data import write_sample_data

ALICE = "11111111-1111-4111-8111-111111111111"
BOB = "22222222-2222-4222-8222-222222222222"

pytestmark = pytest.mark.usefixtures("dynamodb_table")


def table():
    return boto3.resource("dynamodb").Table("test-table")


def both_ways(user_id, **options):
    """The same request answered by the fast path and by the load-everything path."""
    arguments = {
        "year": None,
        "sort": "newest",
        "page": 1,
        "page_size": 20,
        "scope": "both",
        **options,
    }
    fast = service._plain_notebook(user_id, **arguments)
    slow = service._filtered_notebook(user_id, q="", tags=[], **arguments)

    return fast, slow


def same(fast, slow):
    assert [entry.id for entry in fast.items] == [entry.id for entry in slow.items]
    assert [entry.kind for entry in fast.items] == [entry.kind for entry in slow.items]
    assert fast.items == slow.items
    assert (fast.total, fast.all_count, fast.page, fast.pages) == (
        slow.total,
        slow.all_count,
        slow.page,
        slow.pages,
    )
    assert fast.years == slow.years


@pytest.fixture
def busy_user(dynamodb_table):
    write_sample_data(table(), ALICE, fragments=230, songs=40)
    write_sample_data(table(), BOB, fragments=25, songs=5, seed=99)


@pytest.mark.usefixtures("busy_user")
@pytest.mark.parametrize("sort", ["newest", "oldest"])
@pytest.mark.parametrize("scope", ["both", "songs", "fragments"])
def test_every_page_matches_the_load_everything_answer(sort, scope):
    for page in (1, 2, 5, 14):
        same(*both_ways(ALICE, sort=sort, scope=scope, page=page))


@pytest.mark.usefixtures("busy_user")
def test_each_year_matches_the_load_everything_answer():
    years = [entry.year for entry in service.query_notebook(ALICE).years]

    assert len(years) > 3

    for year in years:
        same(*both_ways(ALICE, year=year))
        same(*both_ways(ALICE, year=year, page=2, page_size=7, sort="oldest"))


@pytest.mark.usefixtures("busy_user")
def test_pages_past_the_end_show_the_last_page():
    fast, slow = both_ways(ALICE, page=999)

    same(fast, slow)
    assert fast.page == fast.pages


@pytest.mark.usefixtures("busy_user")
def test_a_year_with_nothing_is_empty():
    fast, slow = both_ways(ALICE, year=1999)

    same(fast, slow)
    assert fast.items == []


@pytest.mark.usefixtures("busy_user")
def test_other_users_items_never_appear():
    fast, _ = both_ways(BOB, page_size=100)

    assert fast.total == 30
    assert len(fast.items) == 30
    assert not {entry.id for entry in fast.items} & {
        entry.id for entry in service.query_notebook(ALICE, page_size=100).items
    }


def test_a_user_with_no_items_gets_an_empty_page():
    fast, slow = both_ways(ALICE)

    same(fast, slow)
    assert (fast.total, fast.pages, fast.years) == (0, 1, [])


def test_items_made_through_the_service_appear_newest_first():
    first = service.create_fragment(ALICE, service.FragmentIn(text="first"))
    song = service.create_song(ALICE, service.SongIn(title="second", body="la"))
    last = service.create_fragment(ALICE, service.FragmentIn(text="third"))

    page = service.query_notebook(ALICE)

    assert [entry.id for entry in page.items] == [last.id, song.id, first.id]
    assert [entry.kind for entry in page.items] == ["fragment", "song", "fragment"]
    assert (page.total, page.all_count) == (3, 3)


def test_key_conditions_are_plain_strings_so_parallel_queries_cannot_collide():
    # boto3's Key(...) builder keeps placeholder counters that threads sharing a client would
    # race on, which once failed CI with "Query condition missed key schema element: PK".
    for year in (None, 2024):
        arguments = service._key_range(ALICE, "FRAG#", year)

        assert isinstance(arguments["KeyConditionExpression"], str)
        assert arguments["ExpressionAttributeValues"][":pk"] == f"USER#{ALICE}"
