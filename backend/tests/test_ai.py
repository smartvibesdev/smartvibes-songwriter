"""Tests for AI generation: prompts and the dial, the token checkpoint, and the routes.

Claude is replaced by a fake, so nothing here spends tokens. DynamoDB is moto, a local fake.
"""

import json
import random
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.ai import budget
from app.ai.claude import (
    MODEL,
    AiNotConfigured,
    AiUnavailable,
    ClaudeGenerator,
    Generated,
    _shared_generator,
    get_generator,
)
from app.ai.prompts import (
    MAX_OUTPUT_TOKENS,
    build_prompt,
    clean_output,
    constraints_for,
    temperature_for,
)
from app.main import app, get_claims

ALICE = "11111111-1111-4111-8111-111111111111"
BOB = "22222222-2222-4222-8222-222222222222"

client = TestClient(app)


class FakeGenerator:
    """Stands in for Claude: records what it was asked and answers with fixed numbers."""

    def __init__(
        self, text="a fine line", input_tokens=100, output_tokens=50, error=None
    ):
        self.calls = []
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.error = error

    def generate(self, *, system, prompt, max_tokens, temperature):
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        if self.error:
            raise self.error

        return Generated(self.text, self.input_tokens, self.output_tokens)


@pytest.fixture(autouse=True)
def _env(dynamodb_table, monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "10000")
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKEN_CAP", "100000")
    yield
    app.dependency_overrides.clear()


def sign_in_as(sub, generator=None):
    app.dependency_overrides[get_claims] = lambda: {"sub": sub}

    if generator is not None:
        app.dependency_overrides[get_generator] = lambda: generator


# --- The dial ---


def test_temperature_runs_zero_to_one_by_seven_then_stays():
    assert temperature_for(0) == 0
    assert temperature_for(7) == 1
    assert temperature_for(8) == temperature_for(10) == 1
    values = [temperature_for(dial) for dial in range(8)]
    assert values == sorted(values)
    assert temperature_for(1) == pytest.approx(1 / 7, abs=0.001)


@pytest.mark.parametrize("dial", range(8))
def test_no_extra_constraints_below_eight(dial):
    assert constraints_for(dial, random.Random(1)) == []


def test_constraints_grow_from_eight_to_ten():
    eight, nine, ten = (constraints_for(dial, random.Random(3)) for dial in (8, 9, 10))

    assert len(eight) == 1
    assert len(nine) == 2
    assert len(ten) == 3
    assert "point of view" in nine[1]
    assert "strange rule" in ten[2]


def test_the_same_random_generator_gives_the_same_prompt():
    first = build_prompt("lyrics", "rain", 10, random.Random(5))
    second = build_prompt("lyrics", "rain", 10, random.Random(5))
    other = build_prompt("lyrics", "rain", 10, random.Random(6))

    assert first == second
    assert first.user != other.user


def test_prompt_uses_the_seed_or_asks_for_something_fresh():
    with_seed = build_prompt("fragment", "  a tin roof in the rain  ", 5)
    without = build_prompt("fragment", "   ", 5)

    assert "a tin roof in the rain" in with_seed.user
    assert "invent something fresh" in without.user
    assert "invent something fresh" not in with_seed.user


def test_dial_zero_asks_for_plain_and_literal():
    assert "plain, literal" in build_prompt("title", "", 0).user
    assert "plain, literal" not in build_prompt("title", "", 1).user


@pytest.mark.parametrize("kind", ["title", "lyrics", "fragment"])
def test_each_kind_has_its_own_output_limit(kind):
    prompt = build_prompt(kind, "", 5)

    assert prompt.max_tokens == MAX_OUTPUT_TOKENS[kind]


def test_titles_are_cut_to_one_unquoted_line():
    assert (
        clean_output("title", '  "Tin Roof Lullaby"\nA second line ')
        == "Tin Roof Lullaby"
    )
    assert clean_output("lyrics", "  line one\n\nline two  ") == "line one\n\nline two"
    assert clean_output("title", "   ") == ""


# --- The token checkpoint ---


def test_reconcile_records_what_was_really_spent():
    budget.reserve(ALICE, 1000)
    budget.reconcile(ALICE, 1000, 400)

    usage = budget.get_usage(ALICE)
    assert (usage.used, usage.limit, usage.remaining) == (400, 10000, 9600)


def test_a_running_call_counts_against_the_budget():
    budget.reserve(ALICE, 6000)

    with pytest.raises(budget.BudgetExceeded) as refusal:
        budget.reserve(ALICE, 6000)

    assert refusal.value.scope == "daily"


def test_releasing_a_reservation_frees_the_room():
    budget.reserve(ALICE, 6000)
    budget.release(ALICE, 6000)
    budget.reserve(ALICE, 6000)

    assert budget.get_usage(ALICE).used == 0


def test_a_single_call_bigger_than_the_whole_budget_is_refused():
    with pytest.raises(budget.BudgetExceeded) as refusal:
        budget.reserve(ALICE, 10001)

    assert refusal.value.scope == "daily"


def test_refusal_reports_how_much_is_left():
    budget.reserve(ALICE, 9000)
    budget.reconcile(ALICE, 9000, 9000)

    with pytest.raises(budget.BudgetExceeded) as refusal:
        budget.reserve(ALICE, 2000)

    assert refusal.value.remaining == 1000


def test_each_user_has_their_own_budget():
    budget.reserve(ALICE, 10000)
    budget.reconcile(ALICE, 10000, 10000)
    budget.reserve(BOB, 5000)

    assert budget.get_usage(BOB).used == 0
    assert budget.get_usage(ALICE).remaining == 0


def test_the_global_cap_stops_everyone(monkeypatch):
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKEN_CAP", "1000")
    budget.reserve(ALICE, 600)

    with pytest.raises(budget.BudgetExceeded) as refusal:
        budget.reserve(BOB, 600)

    assert refusal.value.scope == "global"


def test_a_global_refusal_leaves_the_users_own_counter_unchanged(monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "700")
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKEN_CAP", "1000")
    budget.reserve(ALICE, 600)

    with pytest.raises(budget.BudgetExceeded):
        budget.reserve(BOB, 600)

    budget.release(ALICE, 600)
    # If the failed attempt had counted against Bob, 600 + 600 would now exceed his 700.
    budget.reserve(BOB, 600)


def test_each_day_starts_fresh():
    today = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    budget.reserve(ALICE, 9000, today)
    budget.reconcile(ALICE, 9000, 9000, today)

    tomorrow = today + timedelta(days=1)
    assert budget.get_usage(ALICE, today).remaining == 1000
    assert budget.get_usage(ALICE, tomorrow).remaining == 10000
    budget.reserve(ALICE, 9000, tomorrow)


# --- The routes ---


def test_generate_returns_text_tokens_and_the_budget_left():
    fake = FakeGenerator(text='"Tin Roof Lullaby"', input_tokens=120, output_tokens=8)
    sign_in_as(ALICE, fake)

    response = client.post(
        "/ai/generate", json={"kind": "title", "seed": "rain", "dial": 7}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Tin Roof Lullaby"
    assert (body["kind"], body["dial"], body["temperature"]) == ("title", 7, 1.0)
    assert body["tokens"] == {"input": 120, "output": 8}
    assert body["budget"] == {"used": 128, "limit": 10000, "remaining": 9872}
    assert fake.calls[0]["temperature"] == 1.0
    assert fake.calls[0]["max_tokens"] == MAX_OUTPUT_TOKENS["title"]
    assert "rain" in fake.calls[0]["prompt"]


def test_usage_starts_at_zero_and_grows_after_a_call():
    sign_in_as(ALICE, FakeGenerator())

    assert client.get("/ai/usage").json() == {
        "used": 0,
        "limit": 10000,
        "remaining": 10000,
    }

    client.post("/ai/generate", json={"kind": "fragment"})

    assert client.get("/ai/usage").json()["used"] == 150


def test_the_default_dial_is_five():
    fake = FakeGenerator()
    sign_in_as(ALICE, fake)

    body = client.post("/ai/generate", json={"kind": "lyrics"}).json()

    assert body["dial"] == 5
    assert body["temperature"] == pytest.approx(5 / 7, abs=0.001)


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "poem"},
        {},
        {"kind": "title", "dial": 11},
        {"kind": "title", "dial": -1},
        {"kind": "title", "seed": "x" * 2001},
    ],
)
def test_bad_requests_are_rejected_before_any_tokens_are_reserved(payload):
    fake = FakeGenerator()
    sign_in_as(ALICE, fake)

    assert client.post("/ai/generate", json=payload).status_code == 422
    assert fake.calls == []
    assert client.get("/ai/usage").json()["used"] == 0


def test_generate_needs_a_signed_in_user():
    assert client.post("/ai/generate", json={"kind": "title"}).status_code == 401
    assert client.get("/ai/usage").status_code == 401


def test_an_empty_budget_gives_429_and_never_calls_claude(monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "100")
    fake = FakeGenerator()
    sign_in_as(ALICE, fake)

    response = client.post("/ai/generate", json={"kind": "lyrics"})

    assert response.status_code == 429
    assert "midnight UTC" in response.json()["detail"]
    assert fake.calls == []


def test_the_global_cap_gives_429_with_its_own_message(monkeypatch):
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKEN_CAP", "100")
    sign_in_as(ALICE, FakeGenerator())

    response = client.post("/ai/generate", json={"kind": "fragment"})

    assert response.status_code == 429
    assert "everyone" in response.json()["detail"]


def test_a_failed_call_costs_nothing_and_frees_the_reservation():
    sign_in_as(ALICE, FakeGenerator(error=AiUnavailable("boom")))

    response = client.post("/ai/generate", json={"kind": "lyrics"})

    assert response.status_code == 502
    assert client.get("/ai/usage").json()["used"] == 0
    # The reservation was released, so the whole budget is available again.
    budget.reserve(ALICE, 10000)


def test_without_an_api_key_the_route_says_ai_is_not_set_up(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_SECRET_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _shared_generator.cache_clear()
    sign_in_as(ALICE)

    response = client.post("/ai/generate", json={"kind": "title"})

    assert response.status_code == 503
    with pytest.raises(AiNotConfigured):
        get_generator()


def test_one_users_calls_do_not_use_up_another_users_budget(monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "400")
    fake = FakeGenerator(input_tokens=100, output_tokens=100)
    sign_in_as(ALICE, fake)
    client.post("/ai/generate", json={"kind": "title"})
    client.post("/ai/generate", json={"kind": "title"})

    sign_in_as(BOB, fake)

    assert client.get("/ai/usage").json()["used"] == 0
    assert client.post("/ai/generate", json={"kind": "title"}).status_code == 200


# --- The real Claude client, with the network replaced by a stub ---


def claude_with_stub(handler):
    """A ClaudeGenerator whose HTTP requests go to `handler` instead of the internet."""
    http_client = httpx2.Client(transport=httpx2.MockTransport(handler))

    return ClaudeGenerator("test-key", http_client=http_client)


def message_response(text="a fine line", input_tokens=12, output_tokens=3):
    return httpx2.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": MODEL,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        },
    )


def test_the_claude_client_sends_the_request_shape_the_api_expects():
    sent = []

    def handler(request):
        sent.append(request)

        return message_response("Tin Roof Lullaby", input_tokens=40, output_tokens=6)

    generated = claude_with_stub(handler).generate(
        system="Be brief.", prompt="Write a title.", max_tokens=40, temperature=0.5
    )

    body = json.loads(sent[0].content)
    assert body["model"] == MODEL
    assert body["max_tokens"] == 40
    assert body["system"] == "Be brief."
    assert body["messages"] == [{"role": "user", "content": "Write a title."}]
    assert body["temperature"] == 0.5
    assert sent[0].headers["x-api-key"] == "test-key"
    assert (generated.text, generated.input_tokens, generated.output_tokens) == (
        "Tin Roof Lullaby",
        40,
        6,
    )


def test_the_claude_client_sends_temperature_zero_too():
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))

        return message_response()

    claude_with_stub(handler).generate(
        system="s", prompt="p", max_tokens=10, temperature=0.0
    )

    assert sent[0]["temperature"] == 0.0


def test_a_provider_error_becomes_ai_unavailable():
    def handler(request):
        return httpx2.Response(
            400,
            json={
                "type": "error",
                "error": {"type": "invalid_request_error", "message": "no"},
            },
        )

    with pytest.raises(AiUnavailable):
        claude_with_stub(handler).generate(
            system="s", prompt="p", max_tokens=10, temperature=0.5
        )
