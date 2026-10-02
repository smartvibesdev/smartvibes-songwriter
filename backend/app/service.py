"""Songs and fragments stored in DynamoDB (plan section 5).

This layer knows nothing about HTTP, so the web API and the later MCP server can
share it. Every function takes `user_id` first, and every key is built from it, so
one user's calls can only ever reach that user's partition (`USER#<user_id>`).
"""

import os
import random
import secrets
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.models import (
    Fragment,
    FragmentIn,
    Scope,
    SearchResults,
    Song,
    SongIn,
    TagCount,
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


def _list(user_id: str, prefix: str) -> list[dict[str, Any]]:
    """All of this user's items of one kind, newest first."""
    table = _table()
    query = {
        "KeyConditionExpression": Key("PK").eq(_pk(user_id))
        & Key("SK").begins_with(prefix),
        "ScanIndexForward": False,
    }
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


def search(
    user_id: str,
    query: str = "",
    scope: Scope = "both",
    tags: list[str] | None = None,
) -> SearchResults:
    """Keyword and tag search over this user's songs and fragments.

    DynamoDB has no full-text search, so this loads the user's own items and filters
    them in Python. That is fine at a few hundred items per user.

    Every word in `query` must appear somewhere in the item (a song's title, body or
    tags, or a fragment's text or tags). Every tag in `tags` must be on the item.
    `scope` limits the search to songs or fragments. With neither words nor tags,
    nothing matches.
    """
    terms = query.lower().split()
    wanted = _normalize_tags(tags)

    if not terms and not wanted:
        return SearchResults(songs=[], fragments=[])

    songs: list[Song] = []
    fragments: list[Fragment] = []

    if scope in ("both", "songs"):
        songs = [
            song
            for song in list_songs(user_id)
            if _matches(terms, song.title, song.body, *song.tags)
            and _has_all_tags(song.tags, wanted)
        ]

    if scope in ("both", "fragments"):
        fragments = [
            fragment
            for fragment in list_fragments(user_id)
            if _matches(terms, fragment.text, *fragment.tags)
            and _has_all_tags(fragment.tags, wanted)
        ]

    return SearchResults(songs=songs, fragments=fragments)


def list_tags(user_id: str, scope: Scope = "both") -> list[TagCount]:
    """Every tag this user has used, most used first (ties alphabetical)."""
    counts: Counter[str] = Counter()

    if scope in ("both", "songs"):
        for song in list_songs(user_id):
            counts.update(song.tags)

    if scope in ("both", "fragments"):
        for fragment in list_fragments(user_id):
            counts.update(fragment.tags)

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
    only choice.
    """
    pool = list_fragments(user_id)
    wanted = tag.strip().lower() if tag else ""

    if wanted:
        pool = [fragment for fragment in pool if wanted in fragment.tags]

    others = [fragment for fragment in pool if fragment.id != exclude]
    choices = others or pool

    return random.sample(choices, min(count, len(choices)))
