# How the rhyme finder works, in plain words

This explains what the word tools do and why part of the work is done ahead of time. For the
decisions behind it, see ADR 0016 (what the tools are) and ADR 0017 (the ready-made data file).

## The one idea: words rhyme when they end with the same sound

"Food", "mood" and "crude" rhyme because the last stretch of each one sounds the same: "-ood".
That is about sound, not spelling ("through" and "blue" rhyme; "though" and "through" do not).

So to find rhymes, the app needs to know **how each word sounds**. That comes from the CMU
Pronouncing Dictionary ("CMUdict"), a free list of about 126,000 English words, each written as
its sounds. In it:

| Word  | Its sounds       |
| ----- | ---------------- |
| food  | F UW1 D          |
| mood  | M UW1 D          |
| stone | S T OW1 N        |
| home  | HH OW1 M         |

Each code is one sound (`UW` is the "oo" in food, `D` is the "d"). The digit `1` marks the vowel
that is stressed (said the loudest).

## What "the ending" means

Take the sounds from the stressed vowel to the end of the word. Drop the digit.

- food → `UW D`
- mood → `UW D` (same ending, so they rhyme)
- stone → `OW N`
- home → `OW M` (a different ending, but close, see "near rhymes")

**An exact rhyme** is a word with the same ending. **A near rhyme** has the same vowel and an ending
consonant that is a close cousin of the original: N and M (both hummed through the nose), or T and D
(both a quick tap of the tongue). So stone / home is a near rhyme, and so is food / shoot.

## What is done ahead of time

Finding the rhymes for one word needs a list of every word that shares its ending. Making that list
means looking at all 126,000 words, working out each one's ending, putting words with the same
ending together, and sorting each pile so common words come first ("mood" before "rood").

That is a lot of work, about 1 second on your Mac. The first version of the app did it **when
someone first looked up a word** after the server woke up. The server in AWS (a Lambda) is slower
than your Mac, so the first person waited about 9 seconds.

Now the work is done **once, by a script, before the app is deployed**, and the answer is saved in a
file that is committed to git like any other file:

1. A person runs `python build_rhyme_data.py` (in the `backend` folder). It reads CMUdict and our
   extras file, does the grouping and sorting for **all** the words, and writes
   `backend/app/words/rhymes.json.gz` (about 2 MB).
2. That file is deployed with the app.
3. When someone looks up a word, the app just reads the answer out of the file.

The file is like an answer key. Nobody works the problems out again each time; the app looks the
answer up. The script runs only when someone runs it by hand. It does not run on deploy or on each
lookup.

### What is in the file

It holds three small tables:

1. **Word → its endings.** For "food": `UW D` (exact ending), `UW ~2` (near-rhyme family: a vowel
   plus "any of T or D"), its whole sound `F UW D`, and 1 syllable.
2. **Exact ending → words.** `UW D` → include, attitude, conclude, food, exclude, mood, brood, ...
   (the most common first, at most 400 per ending).
3. **Near-rhyme family → words.** `UW ~2` → include, minute, shoot, attitude, compute, ...

There are about 13,000 exact endings and 10,900 near-rhyme families in all. The file does **not**
hold one entry per pair of rhyming words (that would be billions); it holds one list per ending.

### What happens when you look up "food"

1. Find "food" in table 1: its exact ending is `UW D`, its near family is `UW ~2`.
2. Take the list for `UW D` from table 2, and the list for `UW ~2` from table 3.
3. Remove "food" itself and its sound-alikes (a word that sounds the same but is spelled
   differently, such as "night" and "knight", is not a rhyme).
4. Remove from the near list anything already in the exact list.
5. Keep the first 150 of each and send them to the page.

That is all that happens at lookup time: a few table reads and some filtering.

## Slang and brands (the extras file)

CMUdict was built years ago, so it lacks words like "finna" and "boujee". The file
`backend/app/words/extra_pronunciations.txt` adds about 100 of them in the same format. The build
script merges them in. **If you edit that file, run `python build_rhyme_data.py` again and commit
the new `rhymes.json.gz`.** A test (`test_rhyme_data_is_up_to_date_with_the_extras_file`) fails if
you forget.

## Synonyms and antonyms

These come from a different source, Princeton WordNet, which groups words by meaning. A small
file made from it (`backend/app/words/wordnet.json.gz`) is read when needed. It was made once by
`backend/build_word_data.py`, the same idea as above.

An antonym link in WordNet joins one word to one word (include → exclude). But "exclude" sits in a
group of words with the same meaning (omit, leave out, take out), so those are also listed as
opposites of "include".

## Where each piece lives

| What                                 | Where                                                  |
| ------------------------------------ | ------------------------------------------------------ |
| The lookup route                     | `GET /words/{word}` in `backend/app/main.py`           |
| Rhyme lookup (reads the file)        | `backend/app/words/rhymes.py`                          |
| Sound rules (ending, near family)    | `backend/app/words/phonetics.py`                       |
| Script that builds the rhyme file    | `backend/build_rhyme_data.py`                          |
| The rhyme file it builds             | `backend/app/words/rhymes.json.gz`                     |
| Slang and brand pronunciations       | `backend/app/words/extra_pronunciations.txt`           |
| Synonyms and antonyms                | `backend/app/words/lexicon.py`, `wordnet.json.gz`      |
| Script that builds the WordNet file  | `backend/build_word_data.py`                           |
| The panel on the song page           | `frontend/src/ai/WordsPanel.tsx`                       |

None of this uses AI or tokens, and all of it runs in the backend. The browser only sends one word
and shows what comes back.
