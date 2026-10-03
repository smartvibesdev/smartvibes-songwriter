"""Generated songs and fragments, for trying the app at scale.

The text is nonsense built from word lists. It only has to look, and weigh, something like
real notes. This is used by `dev_server.py` (a fake local database) and by `seed_dev_data.py`
(the real `dev` table). Every generated item carries `sample: True`, so it can be found and
removed later without touching anything the owner wrote.
"""

import random
import re
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from boto3.dynamodb.conditions import Attr, Key

# Word lists. The text is nonsense, only there to fill the screens.
IMAGES = [
    "porch light",
    "tin roof",
    "highway",
    "river",
    "kitchen window",
    "streetlamp",
    "old radio",
    "paper boat",
    "morning train",
    "empty church",
    "gravel road",
    "last bus",
    "garden gate",
    "winter coat",
    "harbor",
    "county fair",
]
VERBS = [
    "hums",
    "waits",
    "remembers",
    "forgets",
    "carries",
    "breaks",
    "keeps time with",
    "sings to",
    "leaves behind",
    "turns toward",
]
ENDINGS = [
    "the weather",
    "your name",
    "a slow goodbye",
    "every promise",
    "the whole town",
    "what we meant",
    "the dark",
    "somebody's grandmother",
    "a borrowed song",
    "the long way home",
]
SONG_TITLE_ENDINGS = ["Blues", "Lullaby", "Waltz", "Road", "Letter", "Hymn"]
TAG_POOL = [
    "rain",
    "night",
    "highway",
    "leaving",
    "morning",
    "letter",
    "porch",
    "roof",
    "family",
    "water",
    "city",
    "train",
    "winter",
    "summer",
    "memory",
    "church",
    "radio",
    "hook",
    "bridge",
    "chorus",
    "verse",
    "title",
    "love",
    "loss",
    "road",
    "window",
    "river",
    "smoke",
    "gold",
    "quiet",
    "storm",
    "garden",
    "kitchen",
    "coffee",
    "ghost",
    "moth",
    "lighthouse",
    "harbor",
    "county",
    "gravel",
    "paper",
    "heart",
    "bus",
    "dance",
    "wedding",
    "funeral",
    "birthday",
    "phone",
    "mirror",
    "ocean",
    "mountain",
    "desert",
    "snow",
    "fire",
    "bones",
    "stars",
    "moon",
    "sun",
    "wind",
    "bird",
]

# Every generated item carries this tag, so it is easy to see and filter in the app.
SAMPLE_TAG = "sample"

# A Cognito user ID ("sub") is a UUID.
_USER_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def looks_like_user_id(text: str) -> bool:
    """True if `text` looks like a Cognito user ID, to catch typos before writing anything."""
    return bool(_USER_ID.match(text))


def _line(rng: random.Random) -> str:
    return f"the {rng.choice(IMAGES)} {rng.choice(VERBS)} {rng.choice(ENDINGS)}"


def fragment_text(rng: random.Random) -> str:
    """One to three clauses: mostly short, sometimes longer, like real scraps."""
    clauses = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]

    return ", ".join(_line(rng) for _ in range(clauses))


def song_body(rng: random.Random) -> str:
    """Two to six stanzas of three to six lines, separated by blank lines."""
    stanzas = []

    for _ in range(rng.randint(2, 6)):
        stanzas.append("\n".join(_line(rng) for _ in range(rng.randint(3, 6))))

    return "\n\n".join(stanzas)


def random_time(rng: random.Random) -> datetime:
    """A moment between January 2018 and now."""
    start = datetime(2018, 1, 1, tzinfo=UTC)
    seconds = int((datetime.now(UTC) - start).total_seconds())

    return start + timedelta(seconds=rng.randint(0, seconds))


def item_key(moment: datetime, prefix: str) -> str:
    """A sort key built like the app's own, from the given time, so ordering stays right."""
    item_id = f"{int(moment.timestamp() * 1000):012x}{secrets.token_hex(16)}"

    return f"{prefix}{item_id}"


def write_sample_data(
    table: Any,
    user_id: str,
    fragments: int,
    songs: int,
    seed: int = 7,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    """Write generated fragments and songs into this user's partition.

    `progress(done, total)` is called now and then, if given.
    """
    rng = random.Random(seed)
    total = fragments + songs
    done = 0

    with table.batch_writer() as batch:
        for _ in range(fragments):
            moment = random_time(rng)
            batch.put_item(
                Item={
                    "PK": f"USER#{user_id}",
                    "SK": item_key(moment, "FRAG#"),
                    "text": fragment_text(rng),
                    "tags": [SAMPLE_TAG, *rng.sample(TAG_POOL, rng.randint(0, 4))],
                    "created_at": moment.isoformat(),
                    "updated_at": moment.isoformat(),
                    "sample": True,
                }
            )
            done += 1

            if progress and done % 500 == 0:
                progress(done, total)

        for _ in range(songs):
            moment = random_time(rng)
            title = f"{rng.choice(IMAGES).title()} {rng.choice(SONG_TITLE_ENDINGS)}"
            batch.put_item(
                Item={
                    "PK": f"USER#{user_id}",
                    "SK": item_key(moment, "SONG#"),
                    "title": title,
                    "body": song_body(rng),
                    "tags": [SAMPLE_TAG, *rng.sample(TAG_POOL, rng.randint(0, 3))],
                    "created_at": moment.isoformat(),
                    "updated_at": moment.isoformat(),
                    "sample": True,
                }
            )
            done += 1

    if progress:
        progress(total, total)


# A word that appears nowhere else, so searching for it shows whether another user's item leaks.
PRIVATE_WORD = "zanzibarquokka"


def write_private_fragment(table: Any, user_id: str) -> None:
    """Write one fragment containing PRIVATE_WORD for this user, to test that users only see their own."""
    moment = datetime.now(UTC)
    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": item_key(moment, "FRAG#"),
            "text": f"{PRIVATE_WORD} belongs to this user only",
            "tags": [SAMPLE_TAG, "private-test"],
            "created_at": moment.isoformat(),
            "updated_at": moment.isoformat(),
            "sample": True,
        }
    )


def count_sample_data(table: Any, user_id: str) -> int:
    """How many generated items this user has."""
    query = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}"),
        "FilterExpression": Attr("sample").eq(True),
        "Select": "COUNT",
    }
    count = 0

    while True:
        page = table.query(**query)
        count += page["Count"]

        if "LastEvaluatedKey" not in page:
            return count

        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def delete_sample_data(table: Any, user_id: str) -> int:
    """Delete this user's generated items, and only those. Returns how many were removed."""
    query = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}"),
        "FilterExpression": Attr("sample").eq(True),
        "ProjectionExpression": "PK, SK",
    }
    deleted = 0

    with table.batch_writer() as batch:
        while True:
            page = table.query(**query)

            for item in page["Items"]:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                deleted += 1

            if "LastEvaluatedKey" not in page:
                return deleted

            query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
