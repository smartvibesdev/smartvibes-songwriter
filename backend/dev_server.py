"""Run the API on your computer with sample data, to try the web app without AWS.

This runs the real API code on `moto`, an in-memory fake of DynamoDB, with a pretend
signed-in user. Nothing touches AWS and nothing is saved: stop it and the data is gone.

    cd backend && source .venv/bin/activate
    python dev_server.py

See "Try the app locally with sample data" in docs/development.md.
"""

import os

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


def main() -> None:
    # Fake credentials and region, so boto3 never looks for (or reaches) real AWS.
    os.environ["AWS_ACCESS_KEY_ID"] = "local-preview"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "local-preview"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["TABLE_NAME"] = TABLE_NAME

    with mock_aws():
        create_fake_table()
        add_sample_data()

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
