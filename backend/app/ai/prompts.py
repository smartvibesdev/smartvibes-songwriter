"""Turns a request (kind, seed text, wildness dial) into a prompt, and the dial into a temperature.

The dial runs 0 to 10. Claude's temperature runs 0 to 1, and some models reject it, so:
  0       temperature 0 and a plain, literal instruction
  1 to 7  temperature rises evenly from 0 to 1
  8 to 10 temperature 1, plus constraints that grow with the dial (random seed words, an
          unusual point of view, a strange rule), in the spirit of Oblique Strategies
"""

import random
from dataclasses import dataclass
from typing import Literal

Kind = Literal["title", "lyrics", "fragment"]

DIAL_MIN = 0
DIAL_MAX = 10
MAX_SEED_LENGTH = 2000

# The most Claude may write for each kind. These also bound what one request can cost.
MAX_OUTPUT_TOKENS: dict[str, int] = {"title": 40, "fragment": 150, "lyrics": 1000}

SEED_WORDS = [
    "lantern", "harbor", "gravel", "orchard", "telegraph", "moth", "porcelain", "tide",
    "railway", "ember", "attic", "compass", "salt", "violin", "thunder", "ladder",
    "mirror", "cathedral", "ferry", "wheat", "chimney", "glacier", "radio", "lighthouse",
    "marble", "bonfire", "windowsill", "sparrow", "quarry", "umbrella", "meadow", "anchor",
    "cobweb", "carousel", "kerosene", "dust", "velvet", "freight", "ember", "pocketknife",
    "overpass", "lullaby", "ash", "peppermint", "driftwood", "cellar", "monsoon", "kite",
    "tin roof", "bus stop", "laundromat", "satellite", "wishbone", "thistle", "static", "yarn",
]  # fmt: skip

VIEWPOINTS = [
    "the point of view of an old house",
    "the point of view of someone leaving a town for the last time",
    "the point of view of the weather",
    "the point of view of a child who misunderstands what the grown-ups say",
    "the point of view of a traveling stranger",
    "the point of view of an object left behind",
    "the point of view of someone talking to their future self",
]

STRANGE_RULES = [
    "include one line that contradicts the line before it",
    "use no word longer than two syllables",
    "make every line a question",
    "name one color that does not belong in the scene",
    "end on an image, never on a feeling",
    "hide a number somewhere in the text",
    "let one line repeat with a single changed word",
]

KIND_INSTRUCTIONS: dict[str, str] = {
    "title": "Write one song title: a few words, no quotation marks.",
    "fragment": "Write one short lyric fragment of one or two lines, the kind a songwriter "
    "jots down to use later.",
    "lyrics": "Write original song lyrics: two verses and a chorus. Separate sections with "
    "a blank line. Label nothing.",
}

SYSTEM_PROMPT = (
    "You are a songwriting partner. Reply with only the requested text. No preamble, no "
    "explanation, no markdown, no quotation marks around the whole answer."
)


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str
    max_tokens: int
    temperature: float


def temperature_for(dial: int) -> float:
    """The temperature for a dial value: 0 at 0, rising evenly to 1 at 7, then staying at 1."""
    return round(min(dial, 7) / 7, 3)


def constraints_for(dial: int, rng: random.Random) -> list[str]:
    """Extra instructions for the top of the dial. None below 8."""
    if dial < 8:
        return []

    word_count = {8: 2, 9: 4, 10: 6}[dial]
    words = ", ".join(rng.sample(SEED_WORDS, word_count))
    lines = [f"Work in these words, even if they seem unrelated: {words}."]

    if dial >= 9:
        lines.append(f"Write from {rng.choice(VIEWPOINTS)}.")

    if dial >= 10:
        lines.append(f"Follow this strange rule: {rng.choice(STRANGE_RULES)}.")

    return lines


def build_prompt(
    kind: Kind, seed: str, dial: int, rng: random.Random | None = None
) -> Prompt:
    """The full prompt for one request."""
    rng = rng or random.Random()
    parts = [KIND_INSTRUCTIONS[kind]]
    seed = seed.strip()

    if seed:
        parts.append(f"Start from this idea or text:\n{seed}")
    else:
        parts.append("No seed was given, so invent something fresh.")

    if dial == 0:
        parts.append("Keep it plain, literal and predictable.")

    parts.extend(constraints_for(dial, rng))

    return Prompt(
        system=SYSTEM_PROMPT,
        user="\n\n".join(parts),
        max_tokens=MAX_OUTPUT_TOKENS[kind],
        temperature=temperature_for(dial),
    )


def clean_output(kind: Kind, text: str) -> str:
    """Tidy what the model wrote: trim it, and for a title keep one line without quotes."""
    text = text.strip()

    if kind == "title":
        text = text.splitlines()[0].strip().strip("\"'“”‘’").strip() if text else ""

    return text
