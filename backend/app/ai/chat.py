"""The assistant's chat: the conversation and the page it is on go to Claude with a few tools.

Claude can use three tools:
  edit_lyrics   change the lyrics (the page applies it, so the user can undo it)
  set_title     change the title (the page applies it)
  lookup_words  rhymes, synonyms and antonyms from our dictionaries (we run it here; it costs no tokens
                by itself, only the model call around it does)

Each call to Claude goes through the token checkpoint on its own (reserve, call, reconcile). A chat
turn makes at most MAX_STEPS calls: more than one only when Claude looked something up or asked for
an edit that did not fit the lyrics, so it needs to see the answer.
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app import words
from app.ai import budget
from app.ai.claude import TextGenerator
from app.ai.prompts import constraints_for, temperature_for
from app.ai.service import estimate_tokens
from app.models import (
    ChatContextIn,
    ChatMessageIn,
    DictionaryOut,
    EditOut,
)

MAX_STEPS = 3
MAX_OUTPUT_TOKENS = 1200
# How much of the conversation is sent each time. Older messages are dropped.
HISTORY_MESSAGES = 12
LOOKUP_LIMITS = {
    "rhymes": 20,
    "near_rhymes": 12,
    "slant_rhymes": 20,
    "synonyms": 15,
    "antonyms": 12,
}

SYSTEM_PROMPT = """You are a songwriting partner inside a songwriting notebook app. You talk with \
the songwriter about the song on screen.

How to work:
- Be brief and concrete. Write the lyrics themselves, not essays about them.
- To write or change lyrics, call edit_lyrics. Use "append" to add new lines at the end, \
"insert_after" (start_line is the line to insert after, 0 for the very top) to add lines in the \
middle, and "replace" (start_line to end_line, both included) to rewrite lines. Line numbers are \
those shown in the lyrics below and always refer to the lyrics as they are NOW; if you make several \
edits in one reply, number them all against the lyrics as shown.
- Put only lyric lines in the text of an edit, with a blank line between sections. No labels like \
"Verse 1", no quotation marks, no explanation.
- To change the title, call set_title.
- For rhymes, near rhymes, synonyms or antonyms, call lookup_words instead of guessing, then pick \
the best few for this song.
- After you edit, write one short sentence saying what you changed and why. Never repeat the \
lyrics back in the chat.
- If the songwriter only asks a question or wants a review, answer in text and do not edit.
- If you are asked to change selected lines but nothing is selected, ask them to select the lines."""

EDIT_TOOL = {
    "name": "edit_lyrics",
    "description": "Change the song's lyrics on the page. The songwriter can undo it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["replace", "insert_after", "append"],
            },
            "start_line": {
                "type": "integer",
                "description": "replace: the first line to replace. insert_after: the line to insert after (0 = top). Not used for append.",
            },
            "end_line": {
                "type": "integer",
                "description": "replace only: the last line to replace (same as start_line for one line).",
            },
            "text": {"type": "string", "description": "The new lyric lines."},
        },
        "required": ["operation", "text"],
    },
}

TITLE_TOOL = {
    "name": "set_title",
    "description": "Change the song's title on the page.",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
    },
}

LOOKUP_TOOL = {
    "name": "lookup_words",
    "description": "Look up one word in the dictionaries: rhymes, near rhymes, synonyms and antonyms.",
    "input_schema": {
        "type": "object",
        "properties": {"word": {"type": "string", "description": "A single word."}},
        "required": ["word"],
    },
}


@dataclass
class ChatResult:
    text: str
    edits: list[EditOut]
    title: str | None
    dictionary: list[DictionaryOut]
    input_tokens: int
    output_tokens: int
    usage: budget.Usage


@dataclass
class _Collected:
    """What the tools asked for over the whole turn."""

    texts: list[str] = field(default_factory=list)
    edits: list[EditOut] = field(default_factory=list)
    title: str | None = None
    dictionary: list[DictionaryOut] = field(default_factory=list)


def numbered(lyrics: str) -> str:
    """The lyrics with a line number in front of each line, so Claude can point at lines."""
    if lyrics == "":
        return "(no lyrics yet)"

    return "\n".join(f"{n}: {line}" for n, line in enumerate(lyrics.split("\n"), 1))


def build_system(context: ChatContextIn, dial: int, rng: random.Random) -> str:
    parts = [SYSTEM_PROMPT]

    if context.page == "song":
        title = context.title or "(untitled)"
        parts.append(f"The songwriter is editing a song.\nTitle: {title}")
        parts.append(f"Lyrics, with line numbers:\n{numbered(context.lyrics)}")

        if context.selection != "":
            start, end = context.selection_start_line, context.selection_end_line
            where = f" (lines {start} to {end})" if start and end else ""
            parts.append(f"Selected by the songwriter{where}:\n{context.selection}")
    else:
        parts.append(
            "The songwriter is on the home page, not in a song, so there are no lyrics to edit. "
            "You can chat, write fragments (short lines to save for later) and look words up."
        )

    constraints = constraints_for(dial, rng)

    if constraints:
        parts.append("Creative constraints for this reply:\n" + "\n".join(constraints))

    return "\n\n".join(parts)


def tools_for(context: ChatContextIn) -> list[dict[str, Any]]:
    if context.page == "song":
        return [EDIT_TOOL, TITLE_TOOL, LOOKUP_TOOL]

    return [LOOKUP_TOOL]


def condense(word: str) -> DictionaryOut:
    """A short dictionary answer: the first few of each kind."""
    info = words.look_up(word)

    def flat(groups: list) -> list[str]:
        return list(dict.fromkeys(w for group in groups for w in group.words))

    return DictionaryOut(
        word=info.word,
        rhymes=[r.word for r in info.rhymes][: LOOKUP_LIMITS["rhymes"]],
        near_rhymes=[r.word for r in info.near_rhymes][: LOOKUP_LIMITS["near_rhymes"]],
        slant_rhymes=[r.word for r in info.slant_rhymes][
            : LOOKUP_LIMITS["slant_rhymes"]
        ],
        synonyms=flat(info.synonyms)[: LOOKUP_LIMITS["synonyms"]],
        antonyms=flat(info.antonyms)[: LOOKUP_LIMITS["antonyms"]],
    )


def _check_edit(
    operation: Any, start: Any, end: Any, text: Any, line_count: int
) -> str | None:
    """Why an edit cannot be applied, or None if it can."""
    if operation not in ("replace", "insert_after", "append") or not isinstance(
        text, str
    ):
        return "Bad edit: operation or text is missing."

    if operation == "append":
        return None

    if not isinstance(start, int) or isinstance(start, bool):
        return "Bad edit: start_line is missing."

    if operation == "insert_after":
        in_range = 0 <= start <= line_count

        return None if in_range else f"Bad edit: the lyrics have {line_count} lines."

    if not isinstance(end, int) or isinstance(end, bool):
        end = start

    if 1 <= start <= end <= line_count:
        return None

    return f"Bad edit: lines {start} to {end} do not fit the {line_count} lyric lines."


def _run_tool(
    name: str, tool_input: dict[str, Any], line_count: int, collected: _Collected
) -> tuple[str, bool]:
    """Do one tool call. Returns (what to tell Claude, whether it was an error)."""
    if name == "lookup_words":
        try:
            found = condense(str(tool_input.get("word", "")))
        except words.NotAWordError:
            return "That is not a single word.", True

        collected.dictionary.append(found)

        return found.model_dump_json(), False

    if name == "set_title":
        title = tool_input.get("title")

        if isinstance(title, str) and title.strip() != "":
            collected.title = title.strip()

            return "Title changed.", False

        return "Bad title.", True

    if name == "edit_lyrics":
        operation = tool_input.get("operation")
        start, end = tool_input.get("start_line"), tool_input.get("end_line")
        text = tool_input.get("text")
        problem = _check_edit(operation, start, end, text, line_count)

        if problem is not None:
            return problem, True

        if operation == "replace" and not isinstance(end, int):
            end = start

        collected.edits.append(
            EditOut(operation=operation, start_line=start, end_line=end, text=text)
        )

        return "Edit applied.", False

    return f"Unknown tool {name}.", True


def chat(
    user_id: str,
    generator: TextGenerator,
    messages: list[ChatMessageIn],
    context: ChatContextIn,
    dial: int,
    rng: random.Random | None = None,
    now: datetime | None = None,
) -> ChatResult:
    """One chat turn. Raises BudgetExceeded before a call to Claude if the budget cannot cover it."""
    rng = rng or random.Random()
    system = build_system(context, dial, rng)
    tools = tools_for(context)
    temperature = temperature_for(dial)
    line_count = len(context.lyrics.split("\n")) if context.lyrics else 0
    conversation: list[dict[str, Any]] = [
        {"role": m.role, "content": m.content} for m in messages[-HISTORY_MESSAGES:]
    ]
    collected = _Collected()
    input_tokens = output_tokens = 0

    for _ in range(MAX_STEPS):
        estimate = estimate_tokens(
            system + json.dumps(tools), json.dumps(conversation), MAX_OUTPUT_TOKENS
        )

        budget.reserve(user_id, estimate, now)

        try:
            turn = generator.chat(
                system=system,
                messages=conversation,
                tools=tools,
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=temperature,
            )
        except Exception:
            budget.release(user_id, estimate, now)
            raise

        budget.reconcile(user_id, estimate, turn.input_tokens + turn.output_tokens, now)
        input_tokens += turn.input_tokens
        output_tokens += turn.output_tokens

        if turn.text:
            collected.texts.append(turn.text)

        results = []
        needs_answer = False

        for call in turn.tool_calls:
            outcome, is_error = _run_tool(call.name, call.input, line_count, collected)
            needs_answer = needs_answer or is_error or call.name == "lookup_words"
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": outcome,
                    "is_error": is_error,
                }
            )

        if turn.tool_calls == [] or needs_answer is False:
            break

        conversation.append({"role": "assistant", "content": turn.content})
        conversation.append({"role": "user", "content": results})

    text = "\n\n".join(collected.texts)

    if text == "" and (collected.edits or collected.title):
        text = "Done."

    return ChatResult(
        text=text,
        edits=collected.edits,
        title=collected.title,
        dictionary=collected.dictionary,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usage=budget.get_usage(user_id, now),
    )
