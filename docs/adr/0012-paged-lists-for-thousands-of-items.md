# 0012. Paged lists and filters for thousands of items

- Status: Accepted
- Date: 2026-10-02

## Context

The first screens loaded every song and fragment and drew them all, because the plan
assumed "a few hundred fragments per user". The owner has more than 5,000 fragments
elsewhere, each with a date, tags and text, to bring into the app. Measured on 5,000
sample fragments (in the local fake database), every list, search, tag count and random
pick read all of them, about 1.8 seconds each; a search for one common word matched 1,753
and would have drawn 1,753 cards. Songs, with up to 20,000 characters of lyrics each, are
heavier still. The owner dislikes "Load more" and endless scrolling, and is not sure how to
group songs (folders were suggested).

## Options considered

- **Load more or endless scrolling.** Rejected by the owner, and poor for finding things.
- **Folders for songs.** A folder puts an item in one place. Tags already exist, let an item
  be several things, and work the same for songs and fragments. Deferred.
- **Cursor paging straight from DynamoDB.** Fast for plain "newest first", but cannot jump to
  a page or count matches, and filters would still need a scan.
- **Filter, sort and page in Python after one read of the user's items** (chosen). One code
  path for words, tags, year, sort and page number, and exact counts.
- **A search index or another database (OpenSearch, Postgres).** Real full-text and meaning
  search, but a new always-on service. Deferred to the embeddings decision (Week 4).

## Decision

- `GET /songs` and `GET /fragments` return one page of 20 (`page_size` up to 100) with
  `total`, `all_count`, `pages` and a per-year count, and take `q`, `tag`, `year`, `sort`
  and `page`. Words match a song's title, body and tags, or a fragment's text and tags.
- Filtering, sorting and slicing work on the raw records, and only the returned page is
  turned into model objects. Pages past the end return the last page.
- Home is the one list screen, over both kinds at once: `GET /notebook` pages, filters and sorts
  songs and fragments together, and a SHOW control chooses all (the default), fragments or songs.
  Separate Songs and Fragments pages existed briefly and were removed as duplicates (ADR 0013).
- The tag list reads only each item's tags, and a random pick reads only the keys (and tags
  when filtering) and then fetches the chosen items.
- Screens: a search box, tag chips with a "Browse all tags" box, a year selector, a sort
  choice, slim rows, "Showing 1-20", and Newer/Older paging. Lists are for finding things, not
  for scrolling through everything.
- On wide screens only the list scrolls: the header, search, filters and pager stay fixed (the
  owner prefers this to scrolling the whole page), and the controls are packed into two rows so the
  list keeps room (about 6 rows on a 900-pixel-tall window). Phones scroll the page normally, because
  a scrolling box inside a scrolling page is awkward on a touch screen. Adding a song or fragment
  opens in a box over the page so the form does not take the list's space.

## Consequences

- Pages stay small and fast to draw, however many items there are.
- Every request still reads all of the user's items of that kind. In the fake database that
  load is nearly the whole cost (about 1.7 of 1.8 seconds). Real DynamoDB timings are not
  known yet and must be measured on `dev` with real data before optimizing.
- The part of the load that is our own code is small: converting 5,000 items from DynamoDB's
  format to Python takes about 14 milliseconds on a laptop (measured), and filtering, sorting
  and paging about the same. Almost all of the 1.7 seconds seen locally is the fake database
  (`moto`) imitating DynamoDB. On AWS the cost should be the network reads (a few 1 MB
  queries), but that has not been measured.
- If the load is too slow, the next steps are, in order: read the table with the low-level
  client and parse only what is needed; cache a user's items in the Lambda, checked against a
  per-user version item that every write bumps; then a search index (a new ADR).
- Offset paging means a page can shift if items are added or deleted while it is open. That
  is acceptable for one person's notebook.
- Songs are not yet organized beyond tags. A status (idea, draft, finished) or collections
  may come later, once the owner says how they group songs.
- Bulk import of the owner's existing fragments is still to do and needs their file format.
