"""Exact rhymes, near rhymes and syllable counts, from ready-made data (rhymes.json.gz). No AI, no network.

  exact rhyme: the same rhyming part, with a different sound before it (stone, alone, bone).
  near rhyme:  the same vowels, and consonants that are close cousins, such as N and M (stone, home, roam).

The data comes from the CMU Pronouncing Dictionary and our extras, built ahead of time by
build_rhyme_data.py (see phonetics.py for the sound rules), so the first request only reads a file.
"""

import gzip
import json
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).parent / "rhymes.json.gz"
MAX_RESULTS = 150


@lru_cache(maxsize=1)
def _data() -> dict:
    with gzip.open(DATA_FILE, "rt", encoding="utf-8") as file:
        return json.load(file)


def _groups(word: str) -> list[tuple[str, str, str, int]]:
    """The (exact key, near key, whole sound, syllables) of each pronunciation of the word."""
    text = _data()["words"].get(word)

    if text is None:
        return []

    groups = []

    for group in text.split(";"):
        exact_key, near_key, sound, syllables = group.split("|")
        groups.append((exact_key, near_key, sound, int(syllables)))

    return groups


def syllables_of(word: str) -> list[int]:
    """The possible syllable counts of a word (some words have more than one pronunciation)."""
    return sorted({syllables for *_, syllables in _groups(word)})


def _sounds(word: str) -> set[str]:
    return {sound for _, _, sound, _ in _groups(word)}


def _ranked(words: list[str], exclude: set[str], skip_sounds: set[str]) -> list[dict]:
    """The words in their ready-made order, without the excluded ones, each with its syllable count."""
    chosen = []

    for word in words:
        if word in exclude or _sounds(word) & skip_sounds:
            continue

        chosen.append({"word": word, "syllables": syllables_of(word)[0]})

        if len(chosen) == MAX_RESULTS:
            break

    return chosen


def find_rhymes(word: str) -> tuple[bool, list[dict], list[dict]]:
    """(known, exact rhymes, near rhymes). Unknown words are ones the dictionary has no sounds for."""
    groups = _groups(word)

    if groups == []:
        return False, [], []

    data = _data()
    exact_words: list[str] = []
    near_words: list[str] = []

    for exact_key, near_key, _, _ in groups:
        exact_words += data["exact"].get(exact_key, [])
        near_words += data["near"].get(near_key, [])

    # Words that rhyme exactly are not also listed as near. The word and its homophones (same sound,
    # other spelling) are not rhymes of it.
    exact_set = set(exact_words)
    own_sounds = _sounds(word)
    exact = _ranked(list(dict.fromkeys(exact_words)), {word}, own_sounds)
    near = _ranked(list(dict.fromkeys(near_words)), {word} | exact_set, own_sounds)

    return True, exact, near
