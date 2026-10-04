# 0016. Word tools without AI: rhymes, near rhymes, synonyms and antonyms

- Status: Accepted
- Date: 2026-10-04

## Context

The song page needs word tools: exact rhymes, near rhymes, synonyms and antonyms. The plan
(section 3, idea 4) says phonetic lookup should cost zero tokens and AI should be used only where it
adds value. These tools look words up; they do not need to write anything, so they do not need
Claude, a token budget or a network call.

The question was whether rhymes and synonyms are one service or two. They answer different
questions from different data, but they are used together (look up a word, see everything), they
are small, and they have the same security and scaling needs as the rest of the API.

## Options considered

- **Separate services (a second Lambda or API) per tool.** Independent deploys, but two more
  things to build, secure and pay for, with no benefit at this size.
- **One endpoint, one module, two data sources (chosen).** `GET /words/{word}` returns rhymes, near
  rhymes, syllable counts, synonyms and antonyms in one response. Inside, `app/words/rhymes.py`
  and `app/words/lexicon.py` are separate and share nothing but the word, so either can be
  replaced or split out later.
- **Ask Claude for rhymes.** Flexible, but costs tokens, is slow, and rhymes are a solved lookup.

Data sources, all bundled with the Lambda and read from local files:

- **CMU Pronouncing Dictionary** (PyPI package `cmudict`, about 134,000 words, public domain) for
  rhymes, near rhymes and syllable counts.
- **Princeton WordNet 3.0** for synonyms, antonyms and a measure of how common a word is. WordNet
  is large (about 30 MB), so `backend/build_word_data.py` boils it down once into
  `backend/app/words/wordnet.json.gz` (about 1 MB, committed, with WordNet's license beside it).
  The alternatives were the `nltk` package, which needs a separate data download at build time,
  and the `wn` package, which is only published as a source archive that the Lambda bundler
  cannot install.

## Decision

- **Exact rhyme:** the same sounds from the last stressed vowel to the end of the word, with
  homophones of the word left out ("night" does not rhyme with "knight").
- **Near rhyme:** the same vowels, with consonants that are close cousins swapped (N and M, T and
  D, K and G, F and V, S and Z, and similar), such as stone / home or love / enough.
- **Which words are offered:** only ordinary words (those WordNet knows, with simple endings such
  as -s, -ed and -ing allowed), so names and dictionary oddities stay out. They are ordered by how
  often they appear in WordNet's sample text, then alphabetically, and capped at 80 each.
- **Synonyms:** words of the same WordNet meaning, then (adjectives only) words of similar
  meanings, grouped by part of speech. **Antonyms:** WordNet's direct opposites, with adjective
  "similar to" groups borrowing the opposites of their head word.
- **Modern words:** CMUdict lacks much slang (finna, boujee, rizz), so `backend/app/words/extra_pronunciations.txt`
  adds about 100 entries in CMUdict's own format. They only fill gaps (CMUdict wins for a word it
  has) and are offered as rhymes like any ordinary word. Add lines to the file to teach it more.
- The route needs sign-in like every other route, takes one word of at most 40 characters, and
  never touches DynamoDB or Anthropic, so it does not use the token checkpoint.
- The data is read on first use and cached per Lambda instance.

## Consequences

- No cost per lookup and no daily limit. The Lambda package grows by about 5 MB.
- The first lookup in a new Lambda instance takes about 0.7 seconds to load and index the
  dictionaries; later ones take milliseconds.
- WordNet is thin on everyday nouns (it lists "rock" and "gem" for "stone", not "pebble"), and it
  has no slang or modern words. The synonym lists are a starting point, and a later AI "other words
  for this" tool can cover what WordNet misses.
- Words missing from the pronouncing dictionary have no rhymes (the panel says so). Guessing
  sounds for unknown words is left for later.
- Rhymes match the last stressed syllable only; they do not yet handle multi-word rhymes
  ("mind ya" for "behind a").
- To change the data, run `build_word_data.py` again and commit the new file.
