# Backend

FastAPI app, run on AWS Lambda via Mangum (`app.main.handler`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000/health
pytest
```

To try the web app against this API without AWS, run `python dev_server.py` (sample data, fake sign-in). See "Try the app locally with sample data" in [development.md](../docs/development.md).

## Layout

| File                  | What                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| `app/main.py`         | Routes. Thin: read the user ID from the token, call `service.py`.                       |
| `app/service.py`      | Reads and writes DynamoDB. No HTTP. Every function takes `user_id` first.               |
| `app/models.py`       | Pydantic request/response shapes and validation limits.                                 |
| `tests/`              | `pytest`. DynamoDB is faked with `moto`; no real AWS is used.                           |

The DynamoDB table name comes from the `TABLE_NAME` environment variable (set by
the CDK stack). See [ADR 0007](../docs/adr/0007-songs-and-fragments-data-model-and-search.md).

## Routes

Everything except `/health` requires a signed-in user (API Gateway checks the
Cognito token). The user ID always comes from the token, never from the request.

| Method and path                       | What                                   | Success |
| ------------------------------------- | -------------------------------------- | ------- |
| `GET /health`                         | Public health check                    | 200     |
| `GET /me`                             | The signed-in user's ID and email      | 200     |
| `GET /songs`                          | One page of my songs (see below)       | 200     |
| `POST /songs`                         | Create a song (title, body, tags)      | 201     |
| `GET /songs/{id}`                     | Get one song                           | 200     |
| `PUT /songs/{id}`                     | Replace a song's title, body and tags  | 200     |
| `DELETE /songs/{id}`                  | Delete a song                          | 204     |
| `GET /fragments`                      | One page of my fragments (see below)   | 200     |
| `POST /fragments`                     | Create a fragment (text, tags)         | 201     |
| `GET /fragments/random`               | Random fragments (see below)           | 200     |
| `GET /fragments/{id}`                 | Get one fragment                       | 200     |
| `PUT /fragments/{id}`                 | Replace a fragment's text and tags     | 200     |
| `DELETE /fragments/{id}`              | Delete a fragment                      | 204     |
| `GET /notebook`                       | One page of songs and fragments together (Home) | 200 |
| `GET /search`                         | Keyword and tag search (see below)     | 200     |
| `GET /tags`                           | My tags with counts                    | 200     |
| `POST /ai/chat`                       | Assistant chat: conversation + page context in; text, lyric edits, title, dictionary answers out (token checkpoint) | 200, 422, 429 |
| `GET /words/{word}`                   | Rhymes, near rhymes, synonyms, antonyms (dictionaries, no AI) | 200, 422 |

A missing item (or one that belongs to someone else) returns 404. Invalid input
returns 422.

### Lists are paged

`GET /songs` and `GET /fragments` return one page of 20 (up to 100 with `page_size`),
not everything, so they stay usable with thousands of items. Parameters, all optional:

- `q`: words; each must appear in the item (a song's title, body or tags, or a fragment's text or tags).
- `tag`: repeat it for several (at most 10); an item must carry every one.
- `year`: only items created in that year.
- `sort`: `newest` (default) or `oldest`, by creation date.
- `page`: 1 or more. A page past the end returns the last page.

The response is `{"items": [...], "total", "all_count", "page", "page_size", "pages", "years"}`:
`total` counts matches across all pages, `all_count` counts every item of that kind, and
`years` lists the years that have matches (ignoring the `year` filter), newest first, with a
count each, for a year picker. Unknown parameters return 422.

### The mixed list (Home)

`GET /notebook` works like the two lists above (same `q`, `tag`, `year`, `sort`, `page`,
`page_size` and the same response shape) and adds `scope`: `songs`, `fragments` or `both`
(default). Each item has a `kind` (`song` or `fragment`) and the fields of that kind. They are
sorted together by creation date. `GET /search` still exists but the web app no longer uses it.

### Search

`GET /search` takes three optional parameters. At least a word or a tag is needed,
or the result is empty.

- `q`: up to 100 characters, split into words. An item matches when every word
  appears (case-insensitive) in a song's title, body or tags, or a fragment's text
  or tags.
- `tag`: repeat it for several (`?tag=rain&tag=road`, at most 10). An item must
  carry every tag. Tag-only searches are allowed.
- `scope`: `both` (default), `songs` or `fragments`.

The response is `{"songs": [...], "fragments": [...], "song_total": 0, "fragment_total": 0}`: only the first 20 matches of each kind, with the full counts.

### Tags

`GET /tags?scope=both|songs|fragments` returns `[{"tag": "rain", "count": 3}, ...]`,
most used first, then alphabetical. Songs and fragments share the same tag rules:
trimmed, lowercased, no duplicates, up to 10 per item and 30 characters each.

### Random fragments

`GET /fragments/random` returns a list of random fragments of the signed-in user.
It takes `count` (1 to 10, default 1), `tag` (only fragments with that tag) and
`exclude` (a fragment ID to avoid, so "another one" does not repeat the one on
screen, unless it is the only choice). It uses no AI and costs no tokens.
