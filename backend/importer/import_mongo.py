"""Import fragments from an old MongoDB export into the real `dev` database.

The export is a JSON array of records like
    {"_id": {"$oid": "..."}, "text": "...", "tags": "funny", "owner": {...},
     "createdAt": {"$date": "2021-10-19T04:23:14.290Z"}, "updatedAt": {...}, "__v": 0}

Run from the `backend` folder:

    source .venv/bin/activate
    aws sso login --profile smartvibes-dev
    python -m importer.import_mongo <export.json> --user-id <cognito-sub>         # dry run, writes nothing
    python -m importer.import_mongo <export.json> --user-id <cognito-sub> --yes   # writes

Records that break the app's limits are listed and skipped, never silently dropped. Running it
again overwrites the same items (the ID comes from the creation time and the old `_id`).
See importer/README.md.
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from pydantic import ValidationError

from app.models import FragmentIn
from sample_data import looks_like_user_id
from seed_dev_data import PROFILE, REGION, TABLE_NAME


class BadRecord(Exception):
    """A record that cannot be imported. The message says why."""


def parse_mongo_date(value: Any) -> datetime:
    """A Mongo extended-JSON date ({"$date": "2021-10-19T04:23:14.290Z"}) as a UTC time."""
    try:
        return datetime.fromisoformat(value["$date"]).astimezone(UTC)
    except (KeyError, TypeError, ValueError) as error:
        raise BadRecord(f"unreadable date: {value!r}") from error


def split_tags(value: Any, separator: str) -> list[str]:
    """The export keeps tags in one string ("funny, rhyme"); the app keeps a list."""
    if isinstance(value, list):
        return [str(tag) for tag in value]

    if isinstance(value, str):
        return value.split(separator)

    raise BadRecord(f"unreadable tags: {value!r}")


def fragment_id(created: datetime, mongo_id: str) -> str:
    """An ID built like the app's own (12 hex digits of milliseconds, then 128 bits), but from
    the old creation time and a hash of the old `_id`, so the same record always gets the same ID."""
    digest = hashlib.sha256(mongo_id.encode()).hexdigest()[:32]

    return f"{int(created.timestamp() * 1000):012x}{digest}"


def build_item(record: dict[str, Any], user_id: str, separator: str) -> dict[str, Any]:
    """The DynamoDB item for one export record. Raises BadRecord if it cannot be imported."""
    try:
        mongo_id = record["_id"]["$oid"]
    except (KeyError, TypeError) as error:
        raise BadRecord("no _id") from error

    created = parse_mongo_date(record.get("createdAt"))
    updated = parse_mongo_date(record.get("updatedAt", record.get("createdAt")))

    try:
        fragment = FragmentIn(
            text=record.get("text", ""),
            tags=split_tags(record.get("tags", ""), separator),
        )
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()
        )
        raise BadRecord(problems) from error

    return {
        "PK": f"USER#{user_id}",
        "SK": f"FRAG#{fragment_id(created, mongo_id)}",
        "text": fragment.text,
        "tags": fragment.tags,
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
    }


def build_items(
    records: list[dict[str, Any]], user_id: str, separator: str
) -> tuple[list[dict[str, Any]], list[tuple[int, str, str]]]:
    """Every importable item, and the problems as (position in the file, old _id, reason)."""
    items: list[dict[str, Any]] = []
    problems: list[tuple[int, str, str]] = []

    for position, record in enumerate(records, start=1):
        try:
            items.append(build_item(record, user_id, separator))
        except BadRecord as error:
            mongo_id = (
                (record.get("_id") or {}).get("$oid", "?")
                if isinstance(record, dict)
                else "?"
            )
            problems.append((position, mongo_id, str(error)))

    return items, problems


def write_items(table: Any, items: list[dict[str, Any]]) -> None:
    """Write the items, replacing any with the same key (so re-running does not duplicate)."""
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in items:
            batch.put_item(Item=item)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import fragments from a MongoDB export into dev."
    )
    parser.add_argument("export_file", type=Path, help="the JSON export")
    parser.add_argument(
        "--user-id", required=True, help="the Cognito user ID (sub) who will own them"
    )
    parser.add_argument(
        "--tag-separator",
        default=",",
        help='what separates tags in the export (default ",")',
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="actually write (without this, only the plan is shown)",
    )
    arguments = parser.parse_args()

    if not looks_like_user_id(arguments.user_id):
        print(
            f"'{arguments.user_id}' does not look like a Cognito user ID (a UUID). Nothing was done."
        )
        return 1

    records = json.loads(arguments.export_file.read_text())
    items, problems = build_items(records, arguments.user_id, arguments.tag_separator)

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]

    print(f"AWS account : {account} (profile {PROFILE}, region {REGION})")
    print(f"Table       : {TABLE_NAME}")
    print(f"User        : {arguments.user_id}")
    print(f"File        : {arguments.export_file} ({len(records)} records)")
    print(
        f"Plan        : IMPORT {len(items)} fragments, SKIP {len(problems)} with problems"
    )

    if items:
        dates = sorted(item["created_at"] for item in items)
        tagged = sum(1 for item in items if item["tags"])
        print(f"Dates       : {dates[0][:10]} to {dates[-1][:10]}; {tagged} have tags")

    for position, mongo_id, reason in problems:
        print(f"  skipped record {position} ({mongo_id}): {reason}")

    if not arguments.yes:
        print("\nThis was a dry run. Nothing was written. Add --yes to do it.")
        return 0

    write_items(session.resource("dynamodb").Table(TABLE_NAME), items)
    print(f"\nDone. Wrote {len(items)} fragments.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
