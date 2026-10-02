# 0010. Search scope, song tags and random fragments

- Status: Accepted
- Date: 2026-10-02

## Context

Week 2 shipped keyword search over songs and fragments (ADR 0007). The Explore
screen needs more: search only songs or only fragments, filter by tag, and pull a
random fragment to spark ideas. Only fragments had tags, and the plan lists tags
for fragments as a later feature that was already stored.

## Options considered

- **Song tags.** Add tags to songs with the same rules as fragments, or keep
  tags fragment-only. A shared tag list across both is simpler for the user.
- **Tag filter.** Items must carry every chosen tag (AND), or any of them (OR).
  AND narrows the way people expect when they click more chips.
- **Random fragments.** Pick in the database, or load the user's fragments and
  pick in Python. DynamoDB has no random read, and at a few hundred items per
  user the Python pick is cheap, like search.
- **Pattern search** (wildcards or regular expressions). Deferred: the owner is
  not sure what it should mean, and user-supplied regular expressions can hang a
  server.

## Decision

- Songs get `tags`, validated by the same rules as fragment tags (one shared
  function). Songs saved before this change have no tags and read as untagged.
- `GET /search` takes optional `q`, repeated `tag` and `scope`. Words must all
  appear, tags must all be present, and a search with neither returns nothing.
  Song tags are also searched as text.
- `GET /tags` lists the user's tags with counts, most used first.
- `GET /fragments/random` returns up to `count` random fragments, optionally for
  one tag, avoiding an `exclude` ID when there is another choice. It is declared
  before `/fragments/{id}` so "random" is not read as an ID.
- Everything stays inside the signed-in user's partition, so no route can see
  another user's tags or fragments.

## Consequences

- The Explore screen can filter by scope and tag chips, and offer "another one".
- Tags are not unique per user in the database, so counting means loading the
  user's items. Fine at this scale; if it grows, keep a tag index item per user.
- Search and tag counts get slower with very large collections, as in ADR 0007.
- Random picks use Python's `random`, which is not for security purposes.
