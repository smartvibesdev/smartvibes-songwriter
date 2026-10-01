# 0007. Songs and fragments: data model and keyword search

- Status: Accepted
- Date: 2026-10-01

## Context

Week 2 adds songs and fragments (create, read, update, delete) and keyword
search. The plan (section 5) already sketches a single DynamoDB table. Two
things needed settling: how items are keyed and ID'd so a user can only ever
reach their own data, and how to search, because DynamoDB has no full-text
search.

## Options considered

**Keys and ownership**

- **Every item lives under the owner's partition key, `USER#<sub>`** (`sub` is
  the user ID in the verified Cognito token). Reads, edits and deletes always
  include that key, so another user's items are simply not found.
- **A global `SONG#<id>` partition with an owner attribute and an ownership
  check in code.** One forgotten check leaks data, and listing a user's songs
  needs an index.

**Item IDs**

- **A random UUID.** Collision-proof, but lists come back in random order unless
  sorted afterwards.
- **A time prefix plus random bits** (chosen). 12 hex digits of milliseconds
  followed by 128 random bits. Sorts by creation time like a ULID (Universally
  Unique Lexicographically Sortable Identifier), is as collision-proof as a
  UUID, and needs no library.

**Search**

- **Load the user's own items and filter in Python.** No new AWS service. Fine
  at a few hundred items per user.
- **Amazon OpenSearch or another search index.** Real full-text search, but a
  new service with a running cost, far beyond what this app needs now.
- **DynamoDB `Scan` with a filter.** Reads the whole table, so cost and speed
  would grow with every user, not just the searcher.

## Decision

- **Items:** songs are `PK = USER#<sub>`, `SK = SONG#<id>` (title, body,
  created_at, updated_at). Fragments are `SK = FRAG#<id>` (text, tags,
  created_at, updated_at).
- **Identity comes only from the token.** No route accepts a user ID from the
  client. Every function in `backend/app/service.py` takes `user_id` first, and
  tests check that a second user gets 404 or empty results for the first user's
  items.
- **Edits are full replacements** (`PUT`). Deletes are hard deletes. Fragments
  are independent of songs. No API pagination for now.
- **Search** loads the caller's songs and fragments with one `Query` each and
  keeps those where every search word appears (case-insensitive substring) in a
  song's title or body, or a fragment's text or tags.
- **Validation limits** (Pydantic): title 200 characters, song body 20,000,
  fragment text 2,000, at most 10 tags of 30 characters. Tags are trimmed,
  lowercased and de-duplicated.
- **The service layer knows nothing about HTTP**, so the planned MCP (Model
  Context Protocol) server can reuse it unchanged.

## Consequences

- Listing and search are cheap, and one user's data can't leak into another's
  by a missed check.
- Search is substring matching only: no stemming, no ranking, no "search by
  meaning". Search by meaning arrives with embeddings in Week 4.
- Search cost and latency grow with a user's item count. If users reach
  thousands of items, move to a search index and record that in a new ADR.
- Data is keyed by Cognito `sub`. Email and Google sign-ins are currently
  separate users with separate data. Linking them is a separate decision.
