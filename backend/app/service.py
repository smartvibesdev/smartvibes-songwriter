"""Songs and fragments stored in DynamoDB (plan section 5).

This layer knows nothing about HTTP, so the web API and the later MCP server can
share it. Every function takes `user_id` first, and every key is built from it, so
one user's calls can only ever reach that user's partition (`USER#<user_id>`).
"""

import math
import os
import random
import secrets
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.models import (
    DEFAULT_PAGE_SIZE,
    Fragment,
    FragmentEntry,
    FragmentIn,
    NotebookEntry,
    Page,
    Scope,
    SearchResults,
    Song,
    SongEntry,
    SongIn,
    Sort,
    TagCount,
    YearCount,
)

SONG_PREFIX = "SONG#"
FRAGMENT_PREFIX = "FRAG#"


class NotFoundError(Exception):
    """The item does not exist for this user (or belongs to someone else)."""


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _new_id() -> str:
    """Time-sortable unique ID: 12 hex digits of milliseconds, then 128 random bits.

    The time prefix keeps lists in creation order. The random part is as large as a
    UUID's, so two IDs colliding is not a practical concern.
    """
    return f"{time.time_ns() // 1_000_000:012x}{secrets.token_hex(16)}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _create(user_id: str, prefix: str, attributes: dict[str, Any]) -> dict[str, Any]:
    item_id = _new_id()
    now = _now()
    item = {
        "PK": _pk(user_id),
        "SK": f"{prefix}{item_id}",
        **attributes,
        "created_at": now,
        "updated_at": now,
    }
    _table().put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    return {**item, "id": item_id}


def _list(
    user_id: str, prefix: str, attributes: list[str] | None = None
) -> list[dict[str, Any]]:
    """All of this user's items of one kind, newest first.

    `attributes` limits which fields DynamoDB sends back (the sort key is always
    included). Asking for less is faster when only a few fields are needed.
    """
    table = _table()
    query: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(_pk(user_id))
        & Key("SK").begins_with(prefix),
        "ScanIndexForward": False,
    }

    if attributes:
        names = {f"#a{i}": name for i, name in enumerate(["SK", *attributes])}
        query["ProjectionExpression"] = ", ".join(names)
        query["ExpressionAttributeNames"] = names

    items: list[dict[str, Any]] = []
    while True:
        page = table.query(**query)
        items.extend(page["Items"])
        if "LastEvaluatedKey" not in page:
            return [{**i, "id": i["SK"].removeprefix(prefix)} for i in items]
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _get(user_id: str, prefix: str, item_id: str) -> dict[str, Any]:
    response = _table().get_item(Key={"PK": _pk(user_id), "SK": f"{prefix}{item_id}"})
    if "Item" not in response:
        raise NotFoundError(item_id)
    return {**response["Item"], "id": item_id}


def _replace(
    user_id: str, prefix: str, item_id: str, attributes: dict[str, Any]
) -> dict[str, Any]:
    """Overwrite the editable attributes of an item that must already exist."""
    names = {f"#{name}": name for name in [*attributes, "updated_at"]}
    values = {
        f":{name}": value
        for name, value in {**attributes, "updated_at": _now()}.items()
    }
    assignments = ", ".join(
        f"#{name} = :{name}" for name in [*attributes, "updated_at"]
    )
    try:
        response = _table().update_item(
            Key={"PK": _pk(user_id), "SK": f"{prefix}{item_id}"},
            UpdateExpression=f"SET {assignments}",
            ConditionExpression="attribute_exists(PK)",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise NotFoundError(item_id) from error
        raise
    return {**response["Attributes"], "id": item_id}


def _delete(user_id: str, prefix: str, item_id: str) -> None:
    try:
        _table().delete_item(
            Key={"PK": _pk(user_id), "SK": f"{prefix}{item_id}"},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise NotFoundError(item_id) from error
        raise


# --- Songs ---


def create_song(user_id: str, data: SongIn) -> Song:
    return Song(**_create(user_id, SONG_PREFIX, data.model_dump()))


def list_songs(user_id: str) -> list[Song]:
    return [Song(**item) for item in _list(user_id, SONG_PREFIX)]


def get_song(user_id: str, song_id: str) -> Song:
    return Song(**_get(user_id, SONG_PREFIX, song_id))


def update_song(user_id: str, song_id: str, data: SongIn) -> Song:
    return Song(**_replace(user_id, SONG_PREFIX, song_id, data.model_dump()))


def delete_song(user_id: str, song_id: str) -> None:
    _delete(user_id, SONG_PREFIX, song_id)


# --- Fragments ---


def create_fragment(user_id: str, data: FragmentIn) -> Fragment:
    return Fragment(**_create(user_id, FRAGMENT_PREFIX, data.model_dump()))


def list_fragments(user_id: str) -> list[Fragment]:
    return [Fragment(**item) for item in _list(user_id, FRAGMENT_PREFIX)]


def get_fragment(user_id: str, fragment_id: str) -> Fragment:
    return Fragment(**_get(user_id, FRAGMENT_PREFIX, fragment_id))


def update_fragment(user_id: str, fragment_id: str, data: FragmentIn) -> Fragment:
    return Fragment(
        **_replace(user_id, FRAGMENT_PREFIX, fragment_id, data.model_dump())
    )


def delete_fragment(user_id: str, fragment_id: str) -> None:
    _delete(user_id, FRAGMENT_PREFIX, fragment_id)


# --- Search ---


def _matches(terms: list[str], *parts: str) -> bool:
    """True if every search term appears somewhere in the text (case-insensitive)."""
    text = " ".join(parts).lower()
    return all(term in text for term in terms)


def _has_all_tags(item_tags: list[str], wanted: list[str]) -> bool:
    """True if the item carries every wanted tag."""
    return all(tag in item_tags for tag in wanted)


def _normalize_tags(tags: list[str] | None) -> list[str]:
    """Trim and lowercase tags from a filter, dropping blanks."""
    return [tag.strip().lower() for tag in tags or [] if tag.strip()]


def _year_of(item: dict[str, Any]) -> int:
    """The year an item was created, from its ISO timestamp ("2026-10-01T...")."""
    return int(item["created_at"][:4])


def _query_items(
    user_id: str,
    prefix: str,
    searchable: Callable[[dict[str, Any]], list[str]],
    build: Callable[[dict[str, Any]], Any],
    *,
    q: str,
    tags: list[str] | None,
    year: int | None,
    sort: Sort,
    page: int,
    page_size: int,
) -> Page:
    """Filter, sort and page one kind of item.

    Loads all of the user's items of that kind and works on the raw records, so the
    (slower) model objects are built only for the one page that is returned.
    """
    items = _list(user_id, prefix)
    terms = q.lower().split()
    wanted = _normalize_tags(tags)

    matching = [
        item
        for item in items
        if _matches(terms, *searchable(item))
        and _has_all_tags(item.get("tags", []), wanted)
    ]

    year_counts = Counter(_year_of(item) for item in matching)
    years = [
        YearCount(year=y, count=year_counts[y])
        for y in sorted(year_counts, reverse=True)
    ]

    if year is not None:
        matching = [item for item in matching if _year_of(item) == year]

    matching.sort(
        key=lambda item: (item["created_at"], item["id"]), reverse=(sort == "newest")
    )

    pages = max(1, math.ceil(len(matching) / page_size))
    page = min(max(page, 1), pages)
    first = (page - 1) * page_size

    return Page(
        items=[build(item) for item in matching[first : first + page_size]],
        total=len(matching),
        all_count=len(items),
        page=page,
        page_size=page_size,
        pages=pages,
        years=years,
    )


def query_songs(
    user_id: str,
    q: str = "",
    tags: list[str] | None = None,
    year: int | None = None,
    sort: Sort = "newest",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Page[Song]:
    """One page of this user's songs matching the words, tags and year."""
    return _query_items(
        user_id,
        SONG_PREFIX,
        lambda item: [item["title"], item.get("body", ""), *item.get("tags", [])],
        lambda item: Song(**item),
        q=q,
        tags=tags,
        year=year,
        sort=sort,
        page=page,
        page_size=page_size,
    )


def query_fragments(
    user_id: str,
    q: str = "",
    tags: list[str] | None = None,
    year: int | None = None,
    sort: Sort = "newest",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Page[Fragment]:
    """One page of this user's fragments matching the words, tags and year."""
    return _query_items(
        user_id,
        FRAGMENT_PREFIX,
        lambda item: [item["text"], *item.get("tags", [])],
        lambda item: Fragment(**item),
        q=q,
        tags=tags,
        year=year,
        sort=sort,
        page=page,
        page_size=page_size,
    )


def query_notebook(
    user_id: str,
    q: str = "",
    tags: list[str] | None = None,
    year: int | None = None,
    sort: Sort = "newest",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    scope: Scope = "both",
) -> Page[NotebookEntry]:
    """One page of songs and fragments together, filtered and sorted like the separate lists.

    `scope` limits it to songs or fragments. Each entry says which it is in `kind`.
    """
    entries: list[tuple[str, dict[str, Any]]] = []

    if scope in ("both", "songs"):
        entries += [("song", item) for item in _list(user_id, SONG_PREFIX)]

    if scope in ("both", "fragments"):
        entries += [("fragment", item) for item in _list(user_id, FRAGMENT_PREFIX)]

    terms = q.lower().split()
    wanted = _normalize_tags(tags)

    def words_of(kind: str, item: dict[str, Any]) -> list[str]:
        if kind == "song":
            return [item["title"], item.get("body", ""), *item.get("tags", [])]

        return [item["text"], *item.get("tags", [])]

    matching = [
        (kind, item)
        for kind, item in entries
        if _matches(terms, *words_of(kind, item))
        and _has_all_tags(item.get("tags", []), wanted)
    ]

    year_counts = Counter(_year_of(item) for _, item in matching)
    years = [
        YearCount(year=y, count=year_counts[y])
        for y in sorted(year_counts, reverse=True)
    ]

    if year is not None:
        matching = [(kind, item) for kind, item in matching if _year_of(item) == year]

    matching.sort(
        key=lambda entry: (entry[1]["created_at"], entry[1]["id"]),
        reverse=(sort == "newest"),
    )

    pages = max(1, math.ceil(len(matching) / page_size))
    page = min(max(page, 1), pages)
    first = (page - 1) * page_size

    def build(kind: str, item: dict[str, Any]) -> SongEntry | FragmentEntry:
        if kind == "song":
            return SongEntry(**item)

        return FragmentEntry(**item)

    return Page(
        items=[build(kind, item) for kind, item in matching[first : first + page_size]],
        total=len(matching),
        all_count=len(entries),
        page=page,
        page_size=page_size,
        pages=pages,
        years=years,
    )


def search(
    user_id: str,
    query: str = "",
    scope: Scope = "both",
    tags: list[str] | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> SearchResults:
    """Keyword and tag search over this user's songs and fragments, newest first.

    Every word in `query` must appear somewhere in the item (a song's title, body or
    tags, or a fragment's text or tags). Every tag in `tags` must be on the item.
    `scope` limits the search to songs or fragments. With neither words nor tags,
    nothing matches. Only the first `limit` matches of each kind are returned, along
    with how many matched in all.
    """
    if not query.split() and not _normalize_tags(tags):
        return SearchResults(songs=[], fragments=[])

    songs = None
    fragments = None

    if scope in ("both", "songs"):
        songs = query_songs(user_id, query, tags, page_size=limit)

    if scope in ("both", "fragments"):
        fragments = query_fragments(user_id, query, tags, page_size=limit)

    return SearchResults(
        songs=songs.items if songs else [],
        fragments=fragments.items if fragments else [],
        song_total=songs.total if songs else 0,
        fragment_total=fragments.total if fragments else 0,
    )


def list_tags(user_id: str, scope: Scope = "both") -> list[TagCount]:
    """Every tag this user has used, most used first (ties alphabetical)."""
    counts: Counter[str] = Counter()
    prefixes = {
        "songs": [SONG_PREFIX],
        "fragments": [FRAGMENT_PREFIX],
        "both": [SONG_PREFIX, FRAGMENT_PREFIX],
    }[scope]

    for prefix in prefixes:
        for item in _list(user_id, prefix, ["tags"]):
            counts.update(item.get("tags", []))

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    return [TagCount(tag=tag, count=count) for tag, count in ranked]


def random_fragments(
    user_id: str,
    count: int = 1,
    tag: str | None = None,
    exclude: str | None = None,
) -> list[Fragment]:
    """Up to `count` of this user's fragments, picked at random.

    `tag` limits the pool to fragments with that tag. `exclude` is an ID to avoid (the
    fragment already on screen) so "another one" does not repeat it, unless it is the
    only choice. Only the keys (and tags, when filtering) are read to choose; the chosen
    fragments are then fetched in full.
    """
    wanted = tag.strip().lower() if tag else ""
    pool = _list(user_id, FRAGMENT_PREFIX, ["tags"] if wanted else None)

    if wanted:
        pool = [item for item in pool if wanted in item.get("tags", [])]

    others = [item for item in pool if item["id"] != exclude]
    choices = others or pool
    chosen = random.sample(choices, min(count, len(choices)))

    return [get_fragment(user_id, item["id"]) for item in chosen]
