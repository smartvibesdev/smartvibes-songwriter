# Backend

FastAPI app, run on AWS Lambda via Mangum (`app.main.handler`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000/health
pytest
```

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
| `GET /songs`                          | List my songs, newest first            | 200     |
| `POST /songs`                         | Create a song                          | 201     |
| `GET /songs/{id}`                     | Get one song                           | 200     |
| `PUT /songs/{id}`                     | Replace a song's title and body        | 200     |
| `DELETE /songs/{id}`                  | Delete a song                          | 204     |
| `GET /fragments`                      | List my fragments, newest first        | 200     |
| `POST /fragments`                     | Create a fragment (text, tags)         | 201     |
| `GET /fragments/{id}`                 | Get one fragment                       | 200     |
| `PUT /fragments/{id}`                 | Replace a fragment's text and tags     | 200     |
| `DELETE /fragments/{id}`              | Delete a fragment                      | 204     |
| `GET /search?q=...`                   | Keyword search over songs and fragments | 200     |

A missing item (or one that belongs to someone else) returns 404. Invalid input
returns 422.

### Search

`q` is 1 to 100 characters. It is split into words, and an item matches when
every word appears (case-insensitive) in a song's title or body, or a fragment's
text or tags. The response is `{"songs": [...], "fragments": [...]}`.
