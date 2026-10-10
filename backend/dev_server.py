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

import boto3
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from moto import mock_aws

from sample_data import write_sample_data

HOST = "127.0.0.1"
PORT = 8000
WEB_APP_ORIGIN = "http://localhost:5173"
TABLE_NAME = "local-preview-table"
USER_ID = "local-preview-user"


class DemoGenerator:
    """Stands in for Claude in the local preview: canned text, no key, no spend.

    It echoes the temperature it was given, so moving the wildness dial is visible.
    """

    def generate(self, *, system, prompt, max_tokens, temperature):
        from app.ai.claude import Generated

        if "song title" in prompt:
            text = "Tin Roof Lullaby"
        elif "lyric fragment" in prompt:
            text = f"the porch light hums a borrowed tune (demo, temperature {temperature})"
        else:
            text = (
                "The kitchen window holds the rain\nlike a letter you forgot to send\n\n"
                f"We sang it slow, we sang it plain\n(demo lyrics, temperature {temperature})"
            )

        return Generated(
            text=text, input_tokens=len(prompt) // 3, output_tokens=len(text) // 3
        )

    def chat(self, *, system, messages, tools, max_tokens, temperature):
        """A canned assistant: enough to see edits, lookups and replies in the local preview."""
        import re

        from app.ai.claude import ToolCall

        last = messages[-1]["content"]

        if isinstance(last, list):  # Claude is answering a tool result
            return self._turn("Here are a few that could work (demo).", [])

        ask = last.lower()
        calls = []
        text = f"(demo reply, temperature {temperature}) I can help with that."

        if "title" in ask and "set_title" in str(tools):
            text = "How about this title?"
            calls = [ToolCall("t1", "set_title", {"title": "Borrowed Light"})]
        elif "improve" in ask or "selected" in ask:
            lines = re.search(r"\(lines (\d+) to (\d+)\)", system)
            start, end = (int(lines[1]), int(lines[2])) if lines else (1, 1)
            text = "I made the image more concrete."
            calls = [
                ToolCall(
                    "e1",
                    "edit_lyrics",
                    {
                        "operation": "replace",
                        "start_line": start,
                        "end_line": end,
                        "text": "a lantern swinging in the window frame",
                    },
                )
            ]
        elif "verse" in ask or "chorus" in ask or "bridge" in ask or "intro" in ask:
            text = "I added a section at the end."
            calls = [
                ToolCall(
                    "e1",
                    "edit_lyrics",
                    {
                        "operation": "append",
                        "text": "the porch light hums a borrowed tune\nand every moth remembers June",
                    },
                )
            ]
        elif "rhyme" in ask or "word" in ask:
            word = re.findall(r"[a-z']+", ask)[-1]
            calls = [ToolCall("l1", "lookup_words", {"word": word})]
            text = ""
        elif "review" in ask:
            text = "Demo review: the images are strong; the tense shifts in the second verse."

        return self._turn(text, calls)

    @staticmethod
    def _turn(text, calls):
        from app.ai.claude import ChatTurn

        content = ([{"type": "text", "text": text}] if text else []) + [
            {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
            for c in calls
        ]

        return ChatTurn(text, calls, content, 300, 60)


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


def add_bulk_data(fragments: int = 5000, songs: int = 300) -> None:
    table = boto3.resource("dynamodb").Table(TABLE_NAME)
    write_sample_data(table, USER_ID, fragments, songs)


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

        from app.ai.claude import get_generator
        from app.main import app, get_claims

        # In AWS, API Gateway checks the token and passes the user's claims in. Here, pretend.
        app.dependency_overrides[get_claims] = lambda: {
            "sub": USER_ID,
            "email": "preview@example.com",
        }

        # AI generation answers with canned text here, so no API key is needed.
        app.dependency_overrides[get_generator] = DemoGenerator

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
