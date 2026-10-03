"""Tests for the MongoDB importer, on moto (a local fake of DynamoDB)."""

import boto3
import pytest

from app import service
from importer.import_mongo import (
    BadRecord,
    build_item,
    build_items,
    fragment_id,
    parse_mongo_date,
    write_items,
)

USER = "11111111-1111-4111-8111-111111111111"


def record(
    oid="aaaaaaaaaaaaaaaaaaaaaaaa",
    text="line one \nline two",
    tags="",
    created="2021-10-19T04:23:14.290Z",
):
    return {
        "_id": {"$oid": oid},
        "text": text,
        "tags": tags,
        "owner": {"$oid": "bbbbbbbbbbbbbbbbbbbbbbbb"},
        "createdAt": {"$date": created},
        "updatedAt": {"$date": created},
        "__v": 0,
    }


def test_a_record_becomes_an_item_with_its_original_dates():
    item = build_item(record(tags="Funny, rhyme ,funny"), USER, ",")

    assert item["PK"] == f"USER#{USER}"
    assert item["SK"].startswith("FRAG#")
    assert item["text"] == "line one \nline two"
    assert item["tags"] == ["funny", "rhyme"]
    assert item["created_at"] == "2021-10-19T04:23:14.290000+00:00"


def test_empty_tags_become_an_empty_list():
    assert build_item(record(tags=""), USER, ",")["tags"] == []


def test_the_separator_can_be_changed():
    assert build_item(record(tags="a b"), USER, " ")["tags"] == ["a", "b"]


def test_the_id_is_stable_and_sorts_by_creation_time():
    created = parse_mongo_date({"$date": "2021-10-19T04:23:14.290Z"})
    later = parse_mongo_date({"$date": "2021-10-20T00:00:00.000Z"})

    assert fragment_id(created, "abc") == fragment_id(created, "abc")
    assert fragment_id(created, "abc") != fragment_id(created, "abd")
    assert fragment_id(created, "zzz") < fragment_id(later, "aaa")
    assert len(fragment_id(created, "abc")) == 44


@pytest.mark.parametrize(
    "bad",
    [
        record(text=""),
        record(text="x" * 2001),
        record(tags="a,b,c,d,e,f,g,h,i,j,k"),
        record(tags="x" * 31),
        record(created="not a date"),
        {"text": "no id", "createdAt": {"$date": "2021-10-19T04:23:14.290Z"}},
    ],
)
def test_records_that_break_a_limit_are_rejected(bad):
    with pytest.raises(BadRecord):
        build_item(bad, USER, ",")


def test_problems_are_reported_with_their_position():
    items, problems = build_items(
        [record(), record(text=""), record(oid="c" * 24)], USER, ","
    )

    assert len(items) == 2
    assert [(position, mongo_id) for position, mongo_id, _ in problems] == [
        (2, "a" * 24)
    ]


@pytest.mark.usefixtures("dynamodb_table")
def test_imported_fragments_appear_in_the_app_newest_first_and_a_second_run_adds_nothing():
    table = boto3.resource("dynamodb").Table("test-table")
    records = [
        record(oid="1" * 24, text="oldest", created="2020-01-05T10:00:00.000Z"),
        record(
            oid="2" * 24,
            text="middle",
            created="2021-06-01T10:00:00.000Z",
            tags="funny",
        ),
        record(oid="3" * 24, text="newest", created="2022-07-10T10:00:00.000Z"),
    ]
    items, _ = build_items(records, USER, ",")

    write_items(table, items)
    write_items(table, items)

    page = service.query_notebook(USER)
    assert [entry.text for entry in page.items] == ["newest", "middle", "oldest"]
    assert [(entry.year, entry.count) for entry in page.years] == [
        (2022, 1),
        (2021, 1),
        (2020, 1),
    ]
    assert page.total == 3
    assert service.query_fragments(USER, tags=["funny"]).total == 1
