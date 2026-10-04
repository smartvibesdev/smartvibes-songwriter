# 0017. Build the rhyme data ahead of time

- Status: Accepted
- Date: 2026-10-04

For a plain-words explanation, see [How the rhyme finder works](../how-rhymes-work.md).

## Context

ADR 0016 added the rhyme finder. The first version read the CMU Pronouncing Dictionary (CMUdict,
about 126,000 words) when the Lambda first needed it, and built its lookup tables then: work out
each word's rhyming ending, group words by ending, and sort each group by how common the words are.

On the real `dev` Lambda (512 MB of memory, which comes with a small share of CPU) that first
lookup took up to 8.7 seconds, measured in the CloudWatch logs. Later lookups took 2 to 7
milliseconds. On a laptop the same work takes about 1 second. Every cold Lambda instance pays the
cost again, so users met it often.

## Options considered

- **Keep building at run time, with more Lambda memory.** Memory also buys CPU, so 1769 MB would
  cut it to about 2.5 seconds, but every cold start would still pay for work whose answer never
  changes.
- **Build at run time, in the Lambda's startup (init) phase.** Hides it from the first request but
  adds seconds to every cold start of every route, including the song list.
- **Build ahead of time and commit the result (chosen).** The grouping and sorting do not depend on
  the user, so do them once and ship the answer.
- **Look rhymes up in a database (DynamoDB).** More moving parts, a new table, and a network call
  per lookup, for a dataset that fits in a 2 MB file.

## Decision

- `backend/build_rhyme_data.py` reads CMUdict plus `extra_pronunciations.txt` and writes
  `backend/app/words/rhymes.json.gz` (about 2 MB). It holds, for every word, its exact-rhyme ending,
  near-rhyme family, whole sound and syllable count, and, for every ending and family, a ranked
  list of ordinary words (at most 400, most common first).
- `app/words/rhymes.py` only reads that file. It no longer imports `cmudict` or parses it. The
  sound rules shared by the script and the tests live in `app/words/phonetics.py`.
- `cmudict` moves from `requirements.txt` to `requirements-dev.txt`: it is needed to build the
  file, not to run the API, so the Lambda package is smaller.
- The data file is committed to git, like `wordnet.json.gz` (ADR 0016). The script is run by hand,
  not by the deploy.
- A test fails if `extra_pronunciations.txt` changed without rebuilding the file, by comparing a
  fingerprint (hash) stored in the file with the extras file's current hash.
- The Lambda is also raised from 512 MB to 1024 MB (separate commit), which speeds up cold starts of
  the whole API.

## Consequences

- The first lookup on a new Lambda instance reads about 3.5 MB of files and takes a fraction of a
  second, instead of up to 8.7 seconds. Measured locally: 0.1 s instead of 1.1 s for the first
  rhyme lookup. Real `dev` timings are checked after the deploy.
- Results are the same as before for the same data.
- Someone who edits the slang file, or rebuilds the WordNet file (which decides which words count as
  ordinary), must run `python build_rhyme_data.py` and commit the new `rhymes.json.gz`. The test
  catches a forgotten rebuild for the slang file. It does not catch one after the WordNet file
  changes, so that case needs care.
- The committed data file is a build product, so changes to it show up as a binary diff in pull
  requests. The script and its inputs are the reviewable part.
- Rhyme lists hold at most 400 words per ending, and the page shows 150. Endings with more
  candidates than that lose the least common ones.
