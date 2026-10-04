"""Extra pronunciations for modern words the CMU Pronouncing Dictionary lacks (slang, brands, artists).

They live in extra_pronunciations.txt, in the same format as CMUdict, and are added on top of it.
"""

from functools import lru_cache
from pathlib import Path

EXTRAS_FILE = Path(__file__).parent / "extra_pronunciations.txt"


@lru_cache(maxsize=1)
def extra_pronunciations() -> dict[str, list[tuple[str, ...]]]:
    """{word: [phonemes, ...]} with the word lowercased. A word listed twice gets both sounds."""
    result: dict[str, list[tuple[str, ...]]] = {}

    for line in EXTRAS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line == "" or line.startswith("#"):
            continue

        word, *phonemes = line.split()
        result.setdefault(word.lower(), []).append(tuple(phonemes))

    return result
