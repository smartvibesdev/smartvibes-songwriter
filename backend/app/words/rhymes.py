"""Exact rhymes, near rhymes and syllable counts, from the CMU Pronouncing Dictionary. No AI, no network.

A word's sounds are phonemes, such as "stone" = S T OW1 N. The digit on a vowel is its stress (1 is the
strongest). The rhyming part of a word runs from its last stressed vowel to the end: "OW1 N".

  exact rhyme: the same rhyming part, with a different sound before it (stone, alone, bone).
  near rhyme:  the same vowels, and consonants that are close cousins, such as N and M (stone, home, roam).
"""

from collections import defaultdict
from functools import lru_cache

import cmudict

from app.words.lexicon import commonness, is_known_word

MAX_RESULTS = 80

# Consonants that sound alike enough to make a near rhyme when swapped.
SOUND_FAMILIES = [
    {"M", "N", "NG"},
    {"P", "B"},
    {"T", "D"},
    {"K", "G"},
    {"F", "V"},
    {"S", "Z"},
    {"SH", "ZH", "CH", "JH"},
    {"TH", "DH"},
    {"L", "R"},
]
FAMILY_OF = {sound: i for i, family in enumerate(SOUND_FAMILIES) for sound in family}

Phonemes = tuple[str, ...]


def is_vowel(phoneme: str) -> bool:
    return phoneme[-1].isdigit()


def syllable_count(phonemes: Phonemes) -> int:
    return sum(1 for phoneme in phonemes if is_vowel(phoneme))


def stressed_start(phonemes: Phonemes) -> int:
    """Where the rhyming part begins: the last vowel with stress 1 or 2, else the last vowel, else 0."""
    stressed = [i for i, phoneme in enumerate(phonemes) if phoneme[-1] in "12"]

    if stressed:
        return stressed[-1]

    vowels = [i for i, phoneme in enumerate(phonemes) if is_vowel(phoneme)]

    return vowels[-1] if vowels else 0


def rhyming_part(phonemes: Phonemes) -> Phonemes:
    return phonemes[stressed_start(phonemes) :]


def plain(phonemes: Phonemes) -> Phonemes:
    """The phonemes without stress digits, so "OW1" and "OW0" compare as equal."""
    return tuple(phoneme.rstrip("012") for phoneme in phonemes)


def shape_key(part: Phonemes) -> tuple:
    """What near rhymes share: the vowels, and the *family* of each consonant, in order."""
    return tuple(
        phoneme.rstrip("012") if is_vowel(phoneme) else FAMILY_OF.get(phoneme, phoneme)
        for phoneme in part
    )


@lru_cache(maxsize=1)
def _pronunciations() -> dict[str, list[Phonemes]]:
    return {
        word: [tuple(phonemes) for phonemes in options]
        for word, options in cmudict.dict().items()
    }


@lru_cache(maxsize=1)
def _index() -> tuple[dict, dict, dict]:
    """Ordinary words grouped by exact rhyming part, by near-rhyme shape, and by their whole sound."""
    by_exact: dict[Phonemes, set[str]] = defaultdict(set)
    by_shape: dict[tuple, set[str]] = defaultdict(set)
    by_sound: dict[Phonemes, set[str]] = defaultdict(set)

    for word, options in _pronunciations().items():
        if word.isalpha() is False or is_known_word(word) is False:
            continue

        for phonemes in options:
            part = rhyming_part(phonemes)
            by_exact[plain(part)].add(word)
            by_shape[shape_key(part)].add(word)
            by_sound[plain(phonemes)].add(word)

    return by_exact, by_shape, by_sound


def syllables_of(word: str) -> list[int]:
    """The possible syllable counts of a word (some words have more than one pronunciation)."""
    options = _pronunciations().get(word, [])

    return sorted({syllable_count(phonemes) for phonemes in options})


def _ranked(words: set[str], exclude: set[str]) -> list[dict]:
    """Most common words first, then alphabetical, each with its syllable count."""
    chosen = sorted(words - exclude, key=lambda word: (-commonness(word), word))[
        :MAX_RESULTS
    ]

    return [{"word": word, "syllables": syllables_of(word)[0]} for word in chosen]


def find_rhymes(word: str) -> tuple[bool, list[dict], list[dict]]:
    """(known, exact rhymes, near rhymes). Unknown words are ones the dictionary has no sounds for."""
    options = _pronunciations().get(word)

    if options is None:
        return False, [], []

    by_exact, by_shape, by_sound = _index()
    exact: set[str] = set()
    near: set[str] = set()

    for phonemes in options:
        part = rhyming_part(phonemes)
        exact |= by_exact.get(plain(part), set())
        near |= by_shape.get(shape_key(part), set())

    # A word and its homophones (same sound, other spelling) are not rhymes of it.
    exclude = {word}

    for phonemes in options:
        exclude |= by_sound.get(plain(phonemes), set())

    return True, _ranked(exact, exclude), _ranked(near - exact, exclude)
