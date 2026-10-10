"""Tests for the assistant's chat: the prompt, tool handling, the token checkpoint and the route.

Claude is replaced by a script of replies, so nothing here spends tokens. DynamoDB is moto.
"""

import random

import pytest
from fastapi.testclient import TestClient

from app.ai import budget
from app.ai.chat import build_system, chat, numbered
from app.ai.claude import ChatTurn, ToolCall, get_generator
from app.main import app, get_claims
from app.models import ChatContextIn, ChatMessageIn

ALICE = "11111111-1111-4111-8111-111111111111"
client = TestClient(app)

SONG = ChatContextIn(
    page="song",
    title="Stones",
    lyrics="I carried every stone home\npockets heavy, steps too slow\n\nso let the river take them",
)
ASK = [ChatMessageIn(role="user", content="make it better")]


def turn(text="", calls=(), tokens=(100, 50)):
    content = [{"type": "text", "text": text}] if text else []
    content += [
        {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
        for c in calls
    ]

    return ChatTurn(text, list(calls), content, tokens[0], tokens[1])


class ScriptedChat:
    """Answers each call with the next prepared turn, and remembers what it was asked."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls = []

    def chat(self, *, system, messages, tools, max_tokens, temperature):
        self.calls.append(
            {
                "system": system,
                "messages": list(messages),
                "tools": tools,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        return self.turns.pop(0)


@pytest.fixture(autouse=True)
def _env(dynamodb_table, monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "10000")
    monkeypatch.setenv("AI_GLOBAL_DAILY_TOKEN_CAP", "100000")
    yield
    app.dependency_overrides.clear()


def edit(operation, text, start=None, end=None):
    return ToolCall(
        "t1",
        "edit_lyrics",
        {"operation": operation, "text": text, "start_line": start, "end_line": end},
    )


# --- The prompt ---


def test_lyrics_are_numbered_from_one():
    assert numbered("a\nb") == "1: a\n2: b"
    assert numbered("") == "(no lyrics yet)"


def test_song_page_prompt_has_title_lyrics_and_selection():
    context = SONG.model_copy(
        update={
            "selection": "steps too slow",
            "selection_start_line": 2,
            "selection_end_line": 2,
        }
    )
    system = build_system(context, 5, random.Random(1))

    assert "Title: Stones" in system
    assert "2: pockets heavy, steps too slow" in system
    assert "(lines 2 to 2)" in system
    assert "steps too slow" in system


def test_home_page_prompt_has_no_lyrics_and_no_edit_tools():
    generator = ScriptedChat(turn("Hello"))
    chat(ALICE, generator, ASK, ChatContextIn(page="home"), 5)
    call = generator.calls[0]

    assert "not in a song" in call["system"]
    assert [tool["name"] for tool in call["tools"]] == ["lookup_words"]


def test_song_page_has_all_three_tools():
    generator = ScriptedChat(turn("Hello"))
    chat(ALICE, generator, ASK, SONG, 5)

    assert [t["name"] for t in generator.calls[0]["tools"]] == [
        "edit_lyrics",
        "set_title",
        "lookup_words",
    ]


def test_wild_dial_adds_constraints_and_sets_temperature():
    generator = ScriptedChat(turn("ok"))
    chat(ALICE, generator, ASK, SONG, 10)
    call = generator.calls[0]

    assert "Creative constraints" in call["system"]
    assert call["temperature"] == 1

    calm = ScriptedChat(turn("ok"))
    chat(ALICE, calm, ASK, SONG, 0)

    assert "Creative constraints" not in calm.calls[0]["system"]
    assert calm.calls[0]["temperature"] == 0


def test_only_the_latest_messages_are_sent():
    history = [
        ChatMessageIn(role="user" if n % 2 == 0 else "assistant", content=f"m{n}")
        for n in range(19)
    ] + [ChatMessageIn(role="user", content="last")]
    generator = ScriptedChat(turn("ok"))
    chat(ALICE, generator, history, SONG, 5)

    sent = generator.calls[0]["messages"]

    assert len(sent) == 12
    assert sent[-1] == {"role": "user", "content": "last"}


# --- Tools ---


def test_an_edit_is_returned_for_the_page_to_apply():
    generator = ScriptedChat(
        turn("I added a verse.", [edit("append", "new line one\nnew line two")])
    )
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert result.text == "I added a verse."
    assert [(e.operation, e.text) for e in result.edits] == [
        ("append", "new line one\nnew line two")
    ]
    assert len(generator.calls) == 1  # no second call needed


def test_an_edit_without_any_text_still_says_done():
    result = chat(ALICE, ScriptedChat(turn("", [edit("append", "x")])), ASK, SONG, 5)

    assert result.text == "Done."


def test_replace_must_fit_the_lyrics_and_claude_gets_to_retry():
    bad = edit("replace", "x", 9, 10)
    good = ToolCall(
        "t2",
        "edit_lyrics",
        {"operation": "replace", "text": "y", "start_line": 1, "end_line": 1},
    )
    generator = ScriptedChat(turn("", [bad]), turn("Fixed.", [good]))
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert [(e.start_line, e.end_line, e.text) for e in result.edits] == [(1, 1, "y")]
    assert len(generator.calls) == 2
    reply = generator.calls[1]["messages"][-1]["content"][0]
    assert reply["is_error"] is True
    assert "do not fit" in reply["content"]


def test_insert_after_zero_is_the_top():
    call = edit("insert_after", "first", 0)
    result = chat(ALICE, ScriptedChat(turn("ok", [call])), ASK, SONG, 5)

    assert result.edits[0].start_line == 0


def test_set_title():
    call = ToolCall("t1", "set_title", {"title": "  River Stones "})
    result = chat(ALICE, ScriptedChat(turn("Renamed.", [call])), ASK, SONG, 5)

    assert result.title == "River Stones"


def test_lookup_words_runs_here_and_claude_sees_the_answer():
    lookup = ToolCall("t1", "lookup_words", {"word": "stone"})
    generator = ScriptedChat(turn("", [lookup]), turn("Try alone or bone."))
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert result.text == "Try alone or bone."
    assert result.dictionary[0].word == "stone"
    assert "alone" in result.dictionary[0].rhymes
    answer = generator.calls[1]["messages"][-1]["content"][0]
    assert answer["type"] == "tool_result"
    assert "alone" in answer["content"]


def test_lookup_of_something_that_is_not_a_word_is_an_error_for_claude():
    lookup = ToolCall("t1", "lookup_words", {"word": "two words"})
    generator = ScriptedChat(turn("", [lookup]), turn("Sorry."))
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert result.dictionary == []
    assert generator.calls[1]["messages"][-1]["content"][0]["is_error"] is True


def test_a_chat_turn_makes_at_most_three_calls():
    lookup = ToolCall("t1", "lookup_words", {"word": "stone"})
    generator = ScriptedChat(*[turn("", [lookup]) for _ in range(5)])
    chat(ALICE, generator, ASK, SONG, 5)

    assert len(generator.calls) == 3


# --- The token checkpoint ---


def test_every_call_is_paid_for_with_what_it_really_used():
    generator = ScriptedChat(turn("ok", tokens=(300, 100)))
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert (result.input_tokens, result.output_tokens) == (300, 100)
    assert budget.get_usage(ALICE).used == 400
    assert result.usage.used == 400


def test_several_calls_add_up():
    lookup = ToolCall("t1", "lookup_words", {"word": "stone"})
    generator = ScriptedChat(
        turn("", [lookup], tokens=(200, 20)), turn("done", tokens=(260, 30))
    )
    result = chat(ALICE, generator, ASK, SONG, 5)

    assert (result.input_tokens, result.output_tokens) == (460, 50)
    assert budget.get_usage(ALICE).used == 510


def test_a_failed_call_gives_its_reservation_back():
    class Failing:
        def chat(self, **kwargs):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        chat(ALICE, Failing(), ASK, SONG, 5)

    assert budget.get_usage(ALICE).used == 0


def test_a_chat_that_does_not_fit_the_budget_never_calls_claude(monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "500")
    generator = ScriptedChat(turn("ok"))

    with pytest.raises(budget.BudgetExceeded):
        chat(ALICE, generator, ASK, SONG, 5)

    assert generator.calls == []


# --- The route ---


def sign_in(generator):
    app.dependency_overrides[get_claims] = lambda: {"sub": ALICE}
    app.dependency_overrides[get_generator] = lambda: generator


def body(**changes):
    data = {
        "messages": [{"role": "user", "content": "add a verse"}],
        "context": {"page": "song", "title": "Stones", "lyrics": "one\ntwo"},
        "dial": 5,
    }
    data.update(changes)

    return data


def test_route_returns_text_edits_and_budget():
    sign_in(ScriptedChat(turn("Added.", [edit("append", "three")], tokens=(120, 30))))
    response = client.post("/ai/chat", json=body())

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Added."
    assert data["edits"] == [
        {"operation": "append", "start_line": None, "end_line": None, "text": "three"}
    ]
    assert data["tokens"] == {"input": 120, "output": 30}
    assert data["budget"]["used"] == 150


def test_route_needs_sign_in():
    assert client.post("/ai/chat", json=body()).status_code == 401


def test_route_rejects_a_conversation_that_ends_with_the_assistant():
    sign_in(ScriptedChat())
    messages = [{"role": "assistant", "content": "hi"}]

    assert client.post("/ai/chat", json=body(messages=messages)).status_code == 422


def test_route_rejects_an_empty_conversation_and_a_bad_dial():
    sign_in(ScriptedChat())

    assert client.post("/ai/chat", json=body(messages=[])).status_code == 422
    assert client.post("/ai/chat", json=body(dial=11)).status_code == 422


def test_route_says_429_when_the_budget_is_used_up(monkeypatch):
    monkeypatch.setenv("AI_DAILY_TOKEN_BUDGET", "500")
    sign_in(ScriptedChat(turn("ok")))
    response = client.post("/ai/chat", json=body())

    assert response.status_code == 429
    assert "budget" in response.json()["detail"]


# --- The Claude client ---


def test_the_claude_client_sends_tools_and_reads_tool_calls():
    import json

    import httpx2

    from app.ai.claude import MODEL, ClaudeGenerator

    sent = []

    def handler(request):
        sent.append(json.loads(request.content))

        return httpx2.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": MODEL,
                "content": [
                    {"type": "text", "text": "Added a line."},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "edit_lyrics",
                        "input": {"operation": "append", "text": "x"},
                    },
                ],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {"input_tokens": 90, "output_tokens": 20},
            },
        )

    http_client = httpx2.Client(transport=httpx2.MockTransport(handler))
    result = ClaudeGenerator("test-key", http_client=http_client).chat(
        system="Be brief.",
        messages=[{"role": "user", "content": "hi"}],
        tools=[
            {
                "name": "edit_lyrics",
                "description": "d",
                "input_schema": {"type": "object"},
            }
        ],
        max_tokens=100,
        temperature=0.5,
    )

    assert sent[0]["model"] == MODEL
    assert sent[0]["temperature"] == 0.5
    assert sent[0]["tools"][0]["name"] == "edit_lyrics"
    assert result.text == "Added a line."
    assert result.tool_calls == [
        ToolCall("toolu_1", "edit_lyrics", {"operation": "append", "text": "x"})
    ]
    assert result.content[1]["type"] == "tool_use"
    assert (result.input_tokens, result.output_tokens) == (90, 20)
