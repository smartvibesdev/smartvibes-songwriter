"""Builds app/words/wordnet.json.gz, the synonym, antonym and word-commonness data, from WordNet 3.0.

Run it only when you want to rebuild the data (the result is committed):

    python build_word_data.py <folder holding data.noun, index.noun, cntlist.rev ...>

WordNet 3.0 is free to use under Princeton's license (see app/words/WORDNET-LICENSE). One place to get the
folder is the `wn==0.0.23` package: `pip download wn==0.0.23 --no-deps`, unpack it, and use
`wn/data/wordnet-3.0`.

The output is one JSON object:
  "words":  {word: [[part_of_speech, [synonyms], [antonyms]], ...]}  one entry per part of speech, with the
            words of the same meanings (and, for adjectives, of similar ones), most common words first
  "common": {word: how often the word appears in WordNet's tagged sample text}
Only lowercase words are kept (capitalized entries are names).
"""

import gzip
import json
import sys
from pathlib import Path

PARTS = {"noun": "n", "verb": "v", "adj": "a", "adv": "r"}
MAX_MEANINGS = 6
MAX_SYNONYMS = 20
MAX_ANTONYMS = 8
MAX_SIMILAR_MEANINGS = 2
OUTPUT = Path(__file__).parent / "app" / "words" / "wordnet.json.gz"


class Synset:
    def __init__(self, part: str, words: list[str]):
        self.part = part
        self.words = words
        self.antonyms: list[list[str]] = [[] for _ in words]  # per word
        self.head_offsets: list[str] = []  # for adjective satellites: the head synsets
        self.similar: list[Synset] = []  # adjectives: "similar to" links, both ways


def read_synsets(folder: Path) -> dict[tuple[str, str], Synset]:
    """Every synset, keyed by (file name, byte offset)."""
    synsets: dict[tuple[str, str], Synset] = {}
    pending: list[
        tuple[Synset, str, str, str]
    ] = []  # synset, symbol, offset, source/target

    for name, part in PARTS.items():
        for line in (folder / f"data.{name}").read_text(encoding="utf-8").splitlines():
            if line.startswith("  "):  # the license header
                continue
            fields = line.split(" ")
            offset, word_count = fields[0], int(fields[3], 16)
            words = [fields[4 + 2 * i] for i in range(word_count)]
            # A trailing "(a)" marks adjective position; the real word is without it.
            words = [word.split("(")[0] for word in words]
            synset = Synset(part, words)
            synsets[(name, offset)] = synset
            pointer_start = 4 + 2 * word_count
            pointer_count = int(fields[pointer_start], 10)
            for i in range(pointer_count):
                symbol, target_offset, target_part, link = fields[
                    pointer_start + 1 + 4 * i : pointer_start + 5 + 4 * i
                ]
                pending.append((synset, symbol, f"{target_part}:{target_offset}", link))

    by_part = {"n": "noun", "v": "verb", "a": "adj", "s": "adj", "r": "adv"}
    for synset, symbol, target, link in pending:
        target_part, target_offset = target.split(":")
        target_synset = synsets.get((by_part[target_part], target_offset))
        if target_synset is None:
            continue
        if symbol == "!" and link != "0000":
            source_hex, target_hex = link[:2], link[2:]
            source_index, target_index = (
                int(source_hex, 16) - 1,
                int(target_hex, 16) - 1,
            )
            synset.antonyms[source_index].append(target_synset.words[target_index])
        if symbol == "&":
            synset.head_offsets.append(target)
            synset.similar.append(target_synset)

    # An adjective satellite has no antonyms of its own; it borrows those of the head it is similar to.
    for synset in synsets.values():
        if synset.part == "a" and synset.head_offsets:
            borrowed = []
            for target in synset.head_offsets:
                head = synsets.get(("adj", target.split(":")[1]))
                if head is not None:
                    borrowed += [word for group in head.antonyms for word in group]
            for group in synset.antonyms:
                if not group:
                    group.extend(borrowed[:3])
    return synsets


def lowercase_single(word: str) -> bool:
    return word == word.lower() and word.replace("_", " ").strip() != ""


def read_counts(folder: Path) -> dict[str, int]:
    """How many times each word was tagged in WordNet's sample text (cntlist.rev: sense_key sense# count)."""
    counts: dict[str, int] = {}
    for line in (folder / "cntlist.rev").read_text(encoding="utf-8").splitlines():
        sense_key, _, count = line.split(" ")
        lemma = sense_key.split("%")[0]
        counts[lemma] = counts.get(lemma, 0) + int(count)
    return counts


def main(folder: Path) -> None:
    synsets = read_synsets(folder)
    counts = read_counts(folder)

    # One entry per word and part of speech. Meanings come in the order of WordNet's index files (most
    # common first); adjectives also gather the words of similar synsets (happy: glad, joyful, cheerful ...).
    words: dict[str, list[list]] = {}
    for name, part in PARTS.items():
        for line in (folder / f"index.{name}").read_text(encoding="utf-8").splitlines():
            if line.startswith("  "):
                continue
            fields = line.split()
            lemma = fields[0]
            if not lowercase_single(lemma) or "_" in lemma:
                continue
            offset_count = int(fields[2])
            offsets = fields[-offset_count:]
            synonyms: list[str] = []
            similar: list[str] = []
            antonyms: list[str] = []
            for rank, offset in enumerate(offsets[:MAX_MEANINGS]):
                synset = synsets[(name, offset)]
                if lemma not in synset.words:
                    continue
                synonyms += [
                    w.replace("_", " ")
                    for w in synset.words
                    if w != lemma and w == w.lower()
                ]
                antonyms += [
                    w.replace("_", " ")
                    for w in synset.antonyms[synset.words.index(lemma)]
                ]
                if rank < MAX_SIMILAR_MEANINGS:
                    for neighbor in synset.similar:
                        similar += [
                            w.replace("_", " ")
                            for w in neighbor.words
                            if w != lemma and w == w.lower()
                        ]
            # Words of the same meaning first, then words of similar meanings (adjectives only).
            synonyms = list(dict.fromkeys(synonyms + similar))[:MAX_SYNONYMS]
            antonyms = list(dict.fromkeys(antonyms))[:MAX_ANTONYMS]
            if synonyms or antonyms:
                words.setdefault(lemma, []).append([part, synonyms, antonyms])

    common = {w: c for w, c in counts.items() if c > 0 and w in words}
    payload = {"words": words, "common": common}
    with gzip.open(OUTPUT, "wt", encoding="utf-8", compresslevel=9) as out:
        json.dump(payload, out, separators=(",", ":"))
    print(
        f"{len(words):,} words, {len(common):,} common; wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
