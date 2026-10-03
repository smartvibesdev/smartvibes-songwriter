"""Put generated sample songs and fragments into the real `dev` database, or remove them.

Why: to see how the app behaves with thousands of items on real DynamoDB, before importing
real notes. Generated items are marked, so `--delete` removes only them.

    cd backend && source .venv/bin/activate
    aws sso login --profile smartvibes-dev
    python seed_dev_data.py --user-id <cognito-sub>                # shows the plan, writes nothing
    python seed_dev_data.py --user-id <cognito-sub> --yes          # writes the sample data
    python seed_dev_data.py --user-id <cognito-sub> --delete --yes # removes it again

Only the `dev` account and table can be used. See "Seed dev with sample data" in
docs/development.md.
"""

import argparse
import sys

import boto3

from sample_data import (
    PRIVATE_WORD,
    count_sample_data,
    delete_sample_data,
    looks_like_user_id,
    write_private_fragment,
    write_sample_data,
)

# The one place this tool will write. Names follow smartvibes-songwriter-<env>-<resource>.
PROFILE = "smartvibes-dev"
REGION = "us-east-1"
TABLE_NAME = "smartvibes-songwriter-dev-table"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add or remove sample data in the dev database."
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="the Cognito user ID (sub) who should own the data",
    )
    parser.add_argument(
        "--fragments", type=int, default=5000, help="how many fragments (default 5000)"
    )
    parser.add_argument(
        "--songs", type=int, default=300, help="how many songs (default 300)"
    )
    parser.add_argument(
        "--other-user-id",
        help="a second user who gets ONE private fragment (to test that users only see their own)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="remove the generated items instead of adding",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="actually do it (without this, only the plan is shown)",
    )
    arguments = parser.parse_args()

    user_ids = [arguments.user_id]

    if arguments.other_user_id:
        user_ids.append(arguments.other_user_id)

    for user_id in user_ids:
        if not looks_like_user_id(user_id):
            print(
                f"'{user_id}' does not look like a Cognito user ID (a UUID). Nothing was done."
            )
            return 1

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    table = session.resource("dynamodb").Table(TABLE_NAME)
    existing = sum(count_sample_data(table, user_id) for user_id in user_ids)

    print(f"AWS account : {account} (profile {PROFILE}, region {REGION})")
    print(f"Table       : {TABLE_NAME}")
    print(f"User        : {arguments.user_id}")

    if arguments.other_user_id:
        print(f"Other user  : {arguments.other_user_id}")

    print(f"Generated items already there for these users: {existing}")

    if arguments.delete:
        print(
            f"Plan        : DELETE the {existing} generated items (real items are not touched)"
        )
    else:
        print(
            f"Plan        : ADD {arguments.fragments} fragments and {arguments.songs} songs, tagged 'sample', to the first user"
        )

        if arguments.other_user_id:
            print(
                f"              ADD 1 fragment containing '{PRIVATE_WORD}' to the other user"
            )

    if not arguments.yes:
        print("\nThis was a dry run. Nothing was written. Add --yes to do it.")
        return 0

    if arguments.delete:
        deleted = sum(delete_sample_data(table, user_id) for user_id in user_ids)
        print(f"\nDeleted {deleted} generated items.")
        return 0

    if arguments.other_user_id:
        write_private_fragment(table, arguments.other_user_id)

    write_sample_data(
        table,
        arguments.user_id,
        arguments.fragments,
        arguments.songs,
        progress=lambda done, total: print(f"  wrote {done} of {total}"),
    )
    print("\nDone. Sign in as that user and open Home.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
