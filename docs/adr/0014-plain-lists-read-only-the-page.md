# 0014. Plain lists read only the page, not every item

- Status: Accepted (partly supersedes 0012)
- Date: 2026-10-03

## Context

ADR 0012 chose to load all of a user's items and filter, sort and page them in Python, and
said real DynamoDB timings had to be measured before optimizing. On `dev` with 5,302 sample
items (5,001 fragments, 301 songs, 2.3 MB):

- Warm Lambda requests took about 1.5 to 1.8 seconds each (CloudWatch). With one item the same
  code takes about 0.12 seconds, so almost all of it is reading the data.
- DynamoDB returns at most 1 MB per query, so the read is two sequential round trips, about
  0.85 seconds from a laptop. Converting to Python added little.
- A cold start added about 1.2 to 1.5 seconds per new Lambda container, and the first screen
  makes several requests at once, so each starts its own.

The browser only ever receives 20 rows. Most views are the plain one (no words, no tags), where
reading everything is wasted work.

## Options considered

- **Start Home empty and make the user search (for example `*`).** Rejected: a search is the
  same full read, only later, and the first screen is worse.
- **Stored counters** (totals and per-year counts kept up to date on every write). Rejected: the
  counts can drift out of step, and a count query makes them unnecessary at this size.
- **Cache each user's items in the Lambda**, checked against a per-user version item. Still
  possible, and it would also help searches. Deferred; not needed for the plain view.
- **Read the newest keys and count by key range** (chosen).

## Decision

For `GET /notebook` with no words and no tags (any `year`, `sort`, `scope`, `page`,
`page_size`), `service._plain_notebook` is used. Searches and tag filters still use
`_filtered_notebook`, unchanged.

- An item's ID starts with its creation time (`_new_id`), so DynamoDB keeps items in date order
  and a year is a key range (`SK BETWEEN FRAG#<start of year> AND FRAG#<start of next year>`).
- Step 1, in parallel: for each kind, the newest (or oldest) `page * page_size` sort keys, read
  as keys only; and the oldest key, to find the first year.
- Step 2, in parallel: a DynamoDB count query (`Select=COUNT`, no items returned) per kind and
  year from the first year to now. The total, `all_count`, `pages` and the year list are all
  sums of these counts.
- Step 3: merge the kinds by ID, cut out the page, and fetch just those full records with
  `BatchGetItem`. Pages past the end return the last page, as before.
- One DynamoDB client is shared by all of these calls and kept for the life of the process. Each
  call used to open a new connection, which cost more than the call (about 250 ms against 85 ms
  from a laptop) and made the first version only about twice as fast as before.
- Tests compare `_plain_notebook` with `_filtered_notebook` on the same data for every sort,
  scope, year and several pages.

Measured on the same `dev` data from a laptop, with identical results to the old path: page 1
about 260 ms (was about 1,800 ms), page 50 about 400 ms, a year view about 260 ms. The first call
in a process takes about 1.6 seconds to set up the connection. Timings inside AWS are not
measured yet.

## Consequences

- Item IDs must carry the creation time, because year counts and ordering depend on it. The
  importer builds IDs from the original `createdAt` (`backend/importer`). An item whose ID time
  and `created_at` disagree would be counted in the wrong year.
- Plain lists order by ID. The filtered path orders by `created_at` then ID. They differ only for
  two items made in the same millisecond.
- The count queries read every item inside DynamoDB (billed as reads, not sent back), so the
  count step still grows with the number of items. If it becomes slow, stored counters or the
  cache are the next steps.
- Page depth costs a little: page `n` reads `n * page_size` keys per kind, as keys only.
- Searches, tag filters, `GET /tags` and the random fragment still read every item (about 1.5
  seconds at this size). They are the next candidates: the cache above, then a search index (ADR
  0012).
- Cold starts are unchanged.
