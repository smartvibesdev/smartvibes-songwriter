"""Songs and fragments stored in DynamoDB (plan section 5).

This layer knows nothing about HTTP, so the web API and the later MCP server can
share it. Every function takes `user_id` first, and every key is built from it, so
one user's calls can only ever reach that user's partition (`USER#<user_id>`).
"""

import functools
import math
import os
import random
import secrets
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
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

    `scope` limits it to songs or fragments. Each entry says which it is in `kind`. With no
    words and no tags, only the items on the page are read (see `_plain_notebook`); otherwise
    every item has to be read to look inside it.
    """
    if not q.split() and not _normalize_tags(tags):
        return _plain_notebook(user_id, year, sort, page, page_size, scope)

    return _filtered_notebook(user_id, q, tags, year, sort, page, page_size, scope)


def _filtered_notebook(
    user_id: str,
    q: str,
    tags: list[str] | None,
    year: int | None,
    sort: Sort,
    page: int,
    page_size: int,
    scope: Scope,
) -> Page[NotebookEntry]:
    """The mixed list with words or tags: loads every item, then filters, sorts and pages."""
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


# --- The mixed list without words or tags ---
#
# An item's ID starts with the time it was created (see `_new_id`), so DynamoDB keeps a
# user's songs and fragments in date order and can find the newest ones, or all of one year's,
# by key alone. That means this list can be built without reading every item:
#   - the newest (or oldest) keys, enough for the page asked for;
#   - how many items there are in each year, counted by DynamoDB without sending them back
#     (the total, the "all" count and the year buttons all come from these counts);
#   - the full records of just the items on the page.

KINDS = {"song": SONG_PREFIX, "fragment": FRAGMENT_PREFIX}


@functools.cache
def _shared_client() -> Any:
    """One DynamoDB connection, kept for as long as this process lives and used by all the
    parallel calls below. Opening a new connection for every call costs more than the call.
    (Clients, unlike the resources made by `_table`, are safe to share between threads.)
    """
    return boto3.resource(
        "dynamodb", config=Config(max_pool_connections=40)
    ).meta.client


def _in_parallel(calls: list[Callable[[], Any]]) -> list[Any]:
    """Run the calls at the same time and return their results in order."""
    with ThreadPoolExecutor(max_workers=max(len(calls), 1)) as pool:
        futures = [pool.submit(call) for call in calls]

        return [future.result() for future in futures]


def _year_start_key(prefix: str, year: int) -> str:
    """The sort key that comes just before every item created in `year` or later."""
    millis = int(datetime(year, 1, 1, tzinfo=UTC).timestamp() * 1000)

    return f"{prefix}{millis:012x}"


def _year_of_key(prefix: str, sort_key: str) -> int:
    """The year in an item's sort key, which holds the time it was created."""
    millis = int(sort_key.removeprefix(prefix)[:12], 16)

    return datetime.fromtimestamp(millis / 1000, UTC).year


def _key_range(user_id: str, prefix: str, year: int | None) -> dict[str, Any]:
    """The query arguments for all of this user's items of one kind, or only those created in `year`.

    The condition is written as a plain string, not built with `Key(...)`. boto3's builder keeps
    placeholder counters on the client, so parallel queries sharing one client could be given
    the same placeholder names and fail.
    """
    values: dict[str, Any] = {":pk": _pk(user_id)}

    if year is None:
        values[":prefix"] = prefix

        return {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": values,
        }

    values[":low"] = _year_start_key(prefix, year)
    values[":high"] = _year_start_key(prefix, year + 1)

    return {
        "KeyConditionExpression": "PK = :pk AND SK BETWEEN :low AND :high",
        "ExpressionAttributeValues": values,
    }


def _edge_keys(
    user_id: str, prefix: str, year: int | None, newest: bool, count: int
) -> list[str]:
    """The sort keys of the newest (or oldest) `count` items, reading only the keys."""
    query: dict[str, Any] = {
        "TableName": os.environ["TABLE_NAME"],
        **_key_range(user_id, prefix, year),
        "ScanIndexForward": not newest,
        "ProjectionExpression": "SK",
    }
    keys: list[str] = []

    while len(keys) < count:
        query["Limit"] = count - len(keys)
        response = _shared_client().query(**query)
        keys += [item["SK"] for item in response["Items"]]

        if "LastEvaluatedKey" not in response:
            break

        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return keys


def _count_items(user_id: str, prefix: str, year: int) -> int:
    """How many of this user's items of one kind were created in `year`."""
    query: dict[str, Any] = {
        "TableName": os.environ["TABLE_NAME"],
        **_key_range(user_id, prefix, year),
        "Select": "COUNT",
    }
    total = 0

    while True:
        response = _shared_client().query(**query)
        total += response["Count"]

        if "LastEvaluatedKey" not in response:
            return total

        query["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def _get_records(user_id: str, sort_keys: list[str]) -> dict[str, dict[str, Any]]:
    """The full records for these sort keys, by sort key."""
    table_name = os.environ["TABLE_NAME"]
    records: dict[str, dict[str, Any]] = {}

    for start in range(0, len(sort_keys), 100):
        keys = [
            {"PK": _pk(user_id), "SK": sort_key}
            for sort_key in sort_keys[start : start + 100]
        ]

        while keys:
            response = _shared_client().batch_get_item(
                RequestItems={table_name: {"Keys": keys}}
            )

            for item in response["Responses"].get(table_name, []):
                records[item["SK"]] = item

            keys = response["UnprocessedKeys"].get(table_name, {}).get("Keys", [])

    return records


def _plain_notebook(
    user_id: str,
    year: int | None,
    sort: Sort,
    page: int,
    page_size: int,
    scope: Scope,
) -> Page[NotebookEntry]:
    """One page of songs and fragments together, with no words or tags to look for.

    Gives the same answer as `_filtered_notebook` (apart from the order of two items made
    in the very same millisecond), but reads only the page's items.
    """
    kinds = {
        kind: prefix
        for kind, prefix in KINDS.items()
        if scope == "both" or scope == f"{kind}s"
    }
    newest = sort == "newest"
    wanted = max(page, 1) * page_size

    # Step 1: the keys that could be on this page, and the oldest key (to know the first year).
    kind_list = list(kinds.items())
    key_calls = [
        lambda prefix=prefix: _edge_keys(user_id, prefix, year, newest, wanted)
        for _, prefix in kind_list
    ]
    oldest_calls = [
        lambda prefix=prefix: _edge_keys(user_id, prefix, None, False, 1)
        for _, prefix in kind_list
    ]
    results = _in_parallel(key_calls + oldest_calls)
    page_keys = results[: len(kind_list)]
    oldest = [keys[0] for keys in results[len(kind_list) :] if keys]

    if len(oldest) == 0:
        return Page(
            items=[],
            total=0,
            all_count=0,
            page=1,
            page_size=page_size,
            pages=1,
            years=[],
        )

    first_year = min(
        _year_of_key(prefix, key)
        for (_, prefix), keys in zip(kind_list, results[len(kind_list) :], strict=True)
        for key in keys
    )
    all_years = list(range(first_year, datetime.now(UTC).year + 1))

    # Step 2: how many items there are in each year (this gives every count on the page).
    count_calls = [
        lambda prefix=prefix, y=y: _count_items(user_id, prefix, y)
        for _, prefix in kind_list
        for y in all_years
    ]
    counts = _in_parallel(count_calls)
    year_counts = {
        y: sum(counts[i * len(all_years) + j] for i in range(len(kind_list)))
        for j, y in enumerate(all_years)
    }
    all_count = sum(year_counts.values())
    total = all_count if year is None else year_counts.get(year, 0)
    pages = max(1, math.ceil(total / page_size))

    if page > pages:
        return _plain_notebook(user_id, year, sort, pages, page_size, scope)

    page = max(page, 1)
    first = (page - 1) * page_size

    # Merge the kinds by ID (which starts with the creation time) and cut out this page.
    entries = [
        (kind, prefix, key)
        for (kind, prefix), keys in zip(kind_list, page_keys, strict=True)
        for key in keys
    ]
    entries.sort(key=lambda entry: entry[2].removeprefix(entry[1]), reverse=newest)
    window = entries[first : first + page_size]

    # Step 3: the full records of just the items on the page.
    records = _get_records(user_id, [key for _, _, key in window])
    items: list[SongEntry | FragmentEntry] = []

    for kind, prefix, key in window:
        item = {**records[key], "id": key.removeprefix(prefix)}
        items.append(SongEntry(**item) if kind == "song" else FragmentEntry(**item))

    years = [
        YearCount(year=y, count=year_counts[y])
        for y in sorted(year_counts, reverse=True)
        if year_counts[y] > 0
    ]

    return Page(
        items=items,
        total=total,
        all_count=all_count,
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
