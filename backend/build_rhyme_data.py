"""Builds app/words/rhymes.json.gz, the ready-made rhyme data the API loads, from CMUdict and our extras.

Run it after changing app/words/extra_pronunciations.txt, or app/words/wordnet.json.gz (the data file
that decides which words count as ordinary), and commit the result:

    python build_rhyme_data.py

Doing this work ahead of time keeps the Lambda fast: it only reads this file, and does not parse CMUdict
or sort 100,000 words on the first request. cmudict is needed only here, not in the Lambda.

The output is one JSON object:
  "words": {word: "exact|near|sound|syllables;..."}  one group per pronunciation, for every word
  "exact": {exact key: [words]}  ordinary words only, most common first, at most KEEP per key
  "near":  {near key: [words]}   the same, for near rhymes
  "extras_hash": a fingerprint of the extras file, so a test can tell the data is out of date
"""

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cmudict

from app.words import phonetics
from app.words.extras import EXTRAS_FILE, extra_pronunciations
from app.words.lexicon import commonness, is_known_word

OUTPUT = Path(__file__).parent / "app" / "words" / "rhymes.json.gz"
KEEP = 400


def extras_hash() -> str:
    return hashlib.sha256(EXTRAS_FILE.read_bytes()).hexdigest()


def all_pronunciations() -> dict[str, list[tuple[str, ...]]]:
    """CMUdict plus our extras, which only fill gaps."""
    words = {
        word: [tuple(phonemes) for phonemes in options]
        for word, options in cmudict.dict().items()
    }

    for word, options in extra_pronunciations().items():
        words.setdefault(word, options)

    return words


def build() -> dict:
    pronunciations = all_pronunciations()
    words: dict[str, str] = {}
    exact: dict[str, set[str]] = defaultdict(set)
    near: dict[str, set[str]] = defaultdict(set)

    for word, options in pronunciations.items():
        groups = []

        for phonemes in options:
            keys = (
                phonetics.exact_key(phonemes),
                phonetics.near_key(phonemes),
                phonetics.sound_key(phonemes),
            )
            syllables = str(phonetics.syllable_count(phonemes))
            groups.append("|".join([*keys, syllables]))

            if word.isalpha() and is_known_word(word):
                exact[keys[0]].add(word)
                near[keys[1]].add(word)

        words[word] = ";".join(dict.fromkeys(groups))

    def ranked(group: set[str]) -> list[str]:
        return sorted(group, key=lambda word: (-commonness(word), word))[:KEEP]

    return {
        "words": words,
        "exact": {key: ranked(group) for key, group in exact.items()},
        "near": {key: ranked(group) for key, group in near.items()},
        "extras_hash": extras_hash(),
    }


def main() -> None:
    payload = build()

    with gzip.open(OUTPUT, "wt", encoding="utf-8", compresslevel=9) as out:
        json.dump(payload, out, separators=(",", ":"))

    print(
        f"{len(payload['words']):,} words, {len(payload['exact']):,} rhyme endings; "
        f"wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)"
    )


if __name__ == "__main__":
    main()
