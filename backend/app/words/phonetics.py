"""Sound rules shared by the rhyme data builder (build_rhyme_data.py) and the tests.

A word's sounds are phonemes, such as "stone" = S T OW1 N. The digit on a vowel is its stress (1 is the
strongest). The rhyming part of a word runs from its last stressed vowel to the end: "OW1 N".
"""

Phonemes = tuple[str, ...]

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
FAMILY_OF = {
    sound: f"~{i}" for i, family in enumerate(SOUND_FAMILIES) for sound in family
}


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


def exact_key(phonemes: Phonemes) -> str:
    """What exact rhymes share: the rhyming part, without stress digits."""
    return " ".join(plain(rhyming_part(phonemes)))


def near_key(phonemes: Phonemes) -> str:
    """What near rhymes share: the vowels, and the *family* of each consonant, in order."""
    return " ".join(
        phoneme.rstrip("012") if is_vowel(phoneme) else FAMILY_OF.get(phoneme, phoneme)
        for phoneme in rhyming_part(phonemes)
    )


def sound_key(phonemes: Phonemes) -> str:
    """The whole word's sound, so homophones (night, knight) can be told apart from rhymes."""
    return " ".join(plain(phonemes))
