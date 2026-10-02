"""Run the API on your computer with sample data, to try the web app without AWS.

This runs the real API code on `moto`, an in-memory fake of DynamoDB, with a pretend
signed-in user. Nothing touches AWS and nothing is saved: stop it and the data is gone.

    cd backend && source .venv/bin/activate
    python dev_server.py

Add --big for thousands of generated fragments and songs, spread over several years, to
try the lists, filters and paging at scale.

See "Try the app locally with sample data" in docs/development.md.
"""

import argparse
import os
import random
import secrets
from datetime import UTC, datetime, timedelta

import boto3
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from moto import mock_aws

HOST = "127.0.0.1"
PORT = 8000
WEB_APP_ORIGIN = "http://localhost:5173"
TABLE_NAME = "local-preview-table"
USER_ID = "local-preview-user"

SAMPLE_FRAGMENTS = [
    ("the porch light hums a lullaby for moths", ["night", "porch"]),
    ("we were all headlights and no map", ["highway", "leaving"]),
    ("your coffee going cold beside the unsent letter", ["morning", "letter"]),
    (
        "rain keeps time on the tin roof, every drop a drummer who never learned to stop",
        ["rain", "roof"],
    ),
    ("the radio knew every word I was trying to forget", ["highway", "night"]),
    ("a lighthouse is just a streetlamp with a good story", ["rain"]),
]

SAMPLE_SONGS = [
    (
        "Tin Roof Lullaby",
        "rain keeps time on the tin roof,\nevery drop a drummer who never learned to stop.\n\nso sleep now, sleep now, the storm is only singing",
        ["rain", "night"],
    ),
    (
        "Headlights",
        "we were all headlights and no map,\nsix hours from the place we said we'd never leave.",
        ["highway", "leaving"],
    ),
    ("Unsent", "your coffee going cold beside the unsent letter", ["morning"]),
]


def create_fake_table() -> None:
    boto3.client("dynamodb").create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


def add_sample_data() -> None:
    from app import service
    from app.models import FragmentIn, SongIn

    for title, body, tags in reversed(SAMPLE_SONGS):
        service.create_song(USER_ID, SongIn(title=title, body=body, tags=tags))

    for text, tags in reversed(SAMPLE_FRAGMENTS):
        service.create_fragment(USER_ID, FragmentIn(text=text, tags=tags))


# Word lists for --big. The text is nonsense, only there to fill the screens.
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


def random_time(rng: random.Random) -> datetime:
    """A moment between January 2018 and now."""
    start = datetime(2018, 1, 1, tzinfo=UTC)
    return start + timedelta(
        seconds=rng.randint(0, int((datetime.now(UTC) - start).total_seconds()))
    )


def item_key(moment: datetime, prefix: str) -> tuple[str, str]:
    """An ID and sort key built like the app's, but from the given time."""
    item_id = f"{int(moment.timestamp() * 1000):012x}{secrets.token_hex(16)}"
    return item_id, f"{prefix}{item_id}"


def add_bulk_data(fragments: int = 5000, songs: int = 300) -> None:
    rng = random.Random(7)
    table = boto3.resource("dynamodb").Table(TABLE_NAME)

    with table.batch_writer() as batch:
        for _ in range(fragments):
            moment = random_time(rng)
            _, sort_key = item_key(moment, "FRAG#")
            text = f"the {rng.choice(IMAGES)} {rng.choice(VERBS)} {rng.choice(ENDINGS)}"
            batch.put_item(
                Item={
                    "PK": f"USER#{USER_ID}",
                    "SK": sort_key,
                    "text": text,
                    "tags": rng.sample(TAG_POOL, rng.randint(0, 4)),
                    "created_at": moment.isoformat(),
                    "updated_at": moment.isoformat(),
                }
            )

        for _ in range(songs):
            moment = random_time(rng)
            _, sort_key = item_key(moment, "SONG#")
            lines = [
                f"the {rng.choice(IMAGES)} {rng.choice(VERBS)} {rng.choice(ENDINGS)}"
                for _ in range(rng.randint(4, 14))
            ]
            batch.put_item(
                Item={
                    "PK": f"USER#{USER_ID}",
                    "SK": sort_key,
                    "title": f"{rng.choice(IMAGES).title()} {rng.choice(['Blues', 'Lullaby', 'Waltz', 'Road', 'Letter', 'Hymn'])}",
                    "body": "\n".join(lines),
                    "tags": rng.sample(TAG_POOL, rng.randint(0, 3)),
                    "created_at": moment.isoformat(),
                    "updated_at": moment.isoformat(),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the API locally with sample data."
    )
    parser.add_argument(
        "--big", action="store_true", help="also generate 5,000 fragments and 300 songs"
    )
    arguments = parser.parse_args()

    # Fake credentials and region, so boto3 never looks for (or reaches) real AWS.
    os.environ["AWS_ACCESS_KEY_ID"] = "local-preview"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "local-preview"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["TABLE_NAME"] = TABLE_NAME

    with mock_aws():
        create_fake_table()
        add_sample_data()

        if arguments.big:
            add_bulk_data()

        from app.main import app, get_claims

        # In AWS, API Gateway checks the token and passes the user's claims in. Here, pretend.
        app.dependency_overrides[get_claims] = lambda: {
            "sub": USER_ID,
            "email": "preview@example.com",
        }

        # In AWS, API Gateway adds the CORS headers. Here, the API has to.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[WEB_APP_ORIGIN],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        print(
            f"Local preview API on http://{HOST}:{PORT} with sample data (nothing is saved)."
        )
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
