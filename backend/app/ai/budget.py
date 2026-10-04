"""The token checkpoint: every AI call reserves tokens first and reconciles afterwards.

Two counters per UTC day, each a DynamoDB item that expires on its own (the table's `ttl` attribute):
  USER#<id>  / USAGE#<date>   this user's day
  GLOBAL     / USAGE#<date>   everyone's day (the circuit breaker)
Each item holds `used` (tokens really spent) and `committed` (used plus tokens reserved by calls
still running). DynamoDB conditions cannot add numbers, so the check is written against
`committed` alone: reserve only if `committed <= limit - estimate`. A reservation changes both
items in one transaction, so a refusal never leaves one of them changed.
"""

import functools
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

DEFAULT_DAILY_BUDGET = 50_000
DEFAULT_GLOBAL_CAP = 500_000
KEEP_DAYS = 3

GLOBAL_PK = "GLOBAL"


class BudgetExceeded(Exception):
    """The user's daily budget or the global cap cannot cover this call."""

    def __init__(self, scope: str, remaining: int):
        super().__init__(scope)
        self.scope = scope  # "daily" or "global"
        self.remaining = remaining


@dataclass(frozen=True)
class Usage:
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)


def daily_budget() -> int:
    return int(os.environ.get("AI_DAILY_TOKEN_BUDGET", DEFAULT_DAILY_BUDGET))


def global_cap() -> int:
    return int(os.environ.get("AI_GLOBAL_DAILY_TOKEN_CAP", DEFAULT_GLOBAL_CAP))


@functools.cache
def _client() -> Any:
    return boto3.resource("dynamodb").meta.client


def _today(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%d")


def _keys(user_id: str, now: datetime) -> tuple[dict[str, str], dict[str, str]]:
    sort_key = f"USAGE#{_today(now)}"

    return (
        {"PK": f"USER#{user_id}", "SK": sort_key},
        {"PK": GLOBAL_PK, "SK": sort_key},
    )


def _expires_at(now: datetime) -> int:
    return int((now + timedelta(days=KEEP_DAYS)).timestamp())


def _reserve_update(
    key: dict[str, str], estimate: int, limit: int, now: datetime
) -> dict:
    return {
        "Update": {
            "TableName": os.environ["TABLE_NAME"],
            "Key": key,
            "UpdateExpression": "ADD committed :estimate SET #ttl = :expires",
            "ExpressionAttributeNames": {"#ttl": "ttl"},
            "ConditionExpression": "attribute_not_exists(committed) OR committed <= :room",
            "ExpressionAttributeValues": {
                ":estimate": estimate,
                ":room": limit - estimate,
                ":expires": _expires_at(now),
            },
        }
    }


def _adjust_update(key: dict[str, str], used_delta: int, committed_delta: int) -> dict:
    return {
        "Update": {
            "TableName": os.environ["TABLE_NAME"],
            "Key": key,
            "UpdateExpression": "ADD used :used, committed :committed",
            "ExpressionAttributeValues": {
                ":used": used_delta,
                ":committed": committed_delta,
            },
        }
    }


def _read(key: dict[str, str]) -> dict[str, Any]:
    response = _client().get_item(TableName=os.environ["TABLE_NAME"], Key=key)

    return response.get("Item", {})


def get_usage(user_id: str, now: datetime | None = None) -> Usage:
    """How many tokens this user has spent today, and their daily limit."""
    now = now or datetime.now(UTC)
    user_key, _ = _keys(user_id, now)

    return Usage(used=int(_read(user_key).get("used", 0)), limit=daily_budget())


def reserve(user_id: str, estimate: int, now: datetime | None = None) -> None:
    """Set aside `estimate` tokens for one call, or raise BudgetExceeded.

    Checks the user's daily budget and the global cap together; if either cannot cover the
    call, neither counter changes.
    """
    now = now or datetime.now(UTC)
    user_key, global_key = _keys(user_id, now)
    user_limit = daily_budget()
    global_limit = global_cap()

    # A call bigger than a whole limit can never fit. This also matters for the check below: on
    # a fresh day the counter does not exist yet, and a missing counter passes the condition.
    if estimate > user_limit:
        raise BudgetExceeded("daily", user_limit)

    if estimate > global_limit:
        raise BudgetExceeded("global", 0)

    try:
        _client().transact_write_items(
            TransactItems=[
                _reserve_update(user_key, estimate, user_limit, now),
                _reserve_update(global_key, estimate, global_limit, now),
            ]
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "TransactionCanceledException":
            raise

        reasons = error.response.get("CancellationReasons", [])
        user_refused = (
            reasons[0].get("Code") == "ConditionalCheckFailed" if reasons else False
        )

        if user_refused:
            raise BudgetExceeded("daily", get_usage(user_id, now).remaining) from error

        raise BudgetExceeded("global", 0) from error


def reconcile(
    user_id: str, estimate: int, actual: int, now: datetime | None = None
) -> None:
    """After a call: record the tokens really spent and release the reservation."""
    now = now or datetime.now(UTC)
    user_key, global_key = _keys(user_id, now)
    delta = actual - estimate

    _client().transact_write_items(
        TransactItems=[
            _adjust_update(user_key, actual, delta),
            _adjust_update(global_key, actual, delta),
        ]
    )


def release(user_id: str, estimate: int, now: datetime | None = None) -> None:
    """After a call that failed: give the reservation back without counting any spend."""
    reconcile(user_id, estimate, 0, now)
