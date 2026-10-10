"""Word tools: rhymes, near rhymes, syllables, synonyms and antonyms. Dictionaries only: no AI, no tokens."""

import re

from app.models import PartOfSpeechWords, RhymeWord, WordInfo
from app.words import lexicon, rhymes

# Letters, with apostrophes and hyphens allowed inside ("don't", "well-known").
WORD_PATTERN = re.compile(r"^[a-z]+(?:['-][a-z]+)*$")


class NotAWordError(ValueError):
    """The text is not a single word."""


def clean_word(text: str) -> str:
    word = text.strip().lower().replace("’", "'")

    if WORD_PATTERN.match(word) is None:
        raise NotAWordError(text)

    return word


def look_up(text: str) -> WordInfo:
    """Rhymes, near rhymes, syllable counts, synonyms and antonyms for one word."""
    word = clean_word(text)
    known, exact, near, slant = rhymes.find_rhymes(word)
    synonyms, antonyms = lexicon.related_words(word)

    return WordInfo(
        word=word,
        rhymes_known=known,
        syllables=rhymes.syllables_of(word),
        rhymes=[RhymeWord(**item) for item in exact],
        near_rhymes=[RhymeWord(**item) for item in near],
        slant_rhymes=[RhymeWord(**item) for item in slant],
        synonyms=[PartOfSpeechWords(**item) for item in synonyms],
        antonyms=[PartOfSpeechWords(**item) for item in antonyms],
    )
