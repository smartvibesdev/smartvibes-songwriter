"""Synonyms and antonyms, from the WordNet data file built by build_word_data.py. No AI, no network."""

import gzip
import json
from functools import lru_cache
from pathlib import Path

from app.words.extras import extra_pronunciations

DATA_FILE = Path(__file__).parent / "wordnet.json.gz"

# Words made by adding an ending count this many times less than the plain word they came from.
INFLECTION_DISCOUNT = 8

PART_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb"}


@lru_cache(maxsize=1)
def _data() -> dict:
    with gzip.open(DATA_FILE, "rt", encoding="utf-8") as file:
        return json.load(file)


def base_forms(word: str) -> list[str]:
    """The word itself, then the plain words it may be an ending of: "stones" -> "stone", "loved" -> "love"."""
    forms = [word]
    endings = [
        ("ies", "y"),
        ("ied", "y"),
        ("ing", ""),
        ("ing", "e"),
        ("ed", ""),
        ("ed", "e"),
        ("es", ""),
        ("s", ""),
        ("er", ""),
        ("est", ""),
    ]

    for ending, replacement in endings:
        stem = word[: -len(ending)] if word.endswith(ending) else ""

        if len(stem) >= 2:
            forms.append(stem + replacement)

        # "running" -> "runn" -> "run"
        if len(stem) >= 3 and stem[-1] == stem[-2]:
            forms.append(stem[:-1])

    return forms


def known_form(word: str) -> str | None:
    """The first of the word's base forms that WordNet knows, or None."""
    words = _data()["words"]

    return next((form for form in base_forms(word) if form in words), None)


def commonness(word: str) -> int:
    """How often the word (or its base form) appears in WordNet's sample text. 0 for rare words."""
    common = _data()["common"]

    # Our extra words are modern and popular, so they count as a little common.
    if word in extra_pronunciations():
        return 1

    own = common.get(word, 0)

    if own > 0:
        return own

    # An ending on a common word ("viewed", "stones") makes a weaker rhyme than a word of its own.
    return (
        max((common.get(form, 0) for form in base_forms(word)), default=0)
        // INFLECTION_DISCOUNT
    )


def is_known_word(word: str) -> bool:
    """True for ordinary words, which keeps names and oddities out of rhyme lists."""
    return known_form(word) is not None or word in extra_pronunciations()


def related_words(word: str) -> tuple[list[dict], list[dict]]:
    """(synonyms, antonyms), each a list of {"part": "noun", "words": [...]}, one per part of speech."""
    form = known_form(word)

    if form is None:
        return [], []

    synonyms = []
    antonyms = []

    for part, similar, opposite in _data()["words"][form]:
        if similar:
            synonyms.append({"part": PART_NAMES[part], "words": similar})

        if opposite:
            antonyms.append({"part": PART_NAMES[part], "words": opposite})

    return synonyms, antonyms
