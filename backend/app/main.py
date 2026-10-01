from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel

from app import service
from app.models import Fragment, FragmentIn, SearchResults, Song, SongIn

app = FastAPI(title="SmartVibes Songwriter API")


@app.exception_handler(service.NotFoundError)
def not_found_handler(request: Request, error: service.NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


class Me(BaseModel):
    user_id: str
    email: str | None = None


def get_claims(request: Request) -> dict[str, str]:
    """Token claims that API Gateway's Cognito authorizer already verified.

    Mangum exposes the raw Lambda event on the ASGI scope. Locally (uvicorn) there
    is no event, so this returns 401.
    """
    event = request.scope.get("aws.event") or {}
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims")
    )
    if not claims:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return claims


def get_user_id(claims: Annotated[dict[str, str], Depends(get_claims)]) -> str:
    """The signed-in user's ID. The only source of identity for data routes."""
    return claims["sub"]


UserId = Annotated[str, Depends(get_user_id)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
def me(claims: Annotated[dict[str, str], Depends(get_claims)]) -> Me:
    return Me(user_id=claims["sub"], email=claims.get("email"))


# --- Songs ---


@app.get("/songs")
def list_songs(user_id: UserId) -> list[Song]:
    return service.list_songs(user_id)


@app.post("/songs", status_code=201)
def create_song(user_id: UserId, data: SongIn) -> Song:
    return service.create_song(user_id, data)


@app.get("/songs/{song_id}")
def get_song(user_id: UserId, song_id: str) -> Song:
    return service.get_song(user_id, song_id)


@app.put("/songs/{song_id}")
def update_song(user_id: UserId, song_id: str, data: SongIn) -> Song:
    return service.update_song(user_id, song_id, data)


@app.delete("/songs/{song_id}", status_code=204)
def delete_song(user_id: UserId, song_id: str) -> Response:
    service.delete_song(user_id, song_id)
    return Response(status_code=204)


# --- Fragments ---


@app.get("/fragments")
def list_fragments(user_id: UserId) -> list[Fragment]:
    return service.list_fragments(user_id)


@app.post("/fragments", status_code=201)
def create_fragment(user_id: UserId, data: FragmentIn) -> Fragment:
    return service.create_fragment(user_id, data)


@app.get("/fragments/{fragment_id}")
def get_fragment(user_id: UserId, fragment_id: str) -> Fragment:
    return service.get_fragment(user_id, fragment_id)


@app.put("/fragments/{fragment_id}")
def update_fragment(user_id: UserId, fragment_id: str, data: FragmentIn) -> Fragment:
    return service.update_fragment(user_id, fragment_id, data)


@app.delete("/fragments/{fragment_id}", status_code=204)
def delete_fragment(user_id: UserId, fragment_id: str) -> Response:
    service.delete_fragment(user_id, fragment_id)
    return Response(status_code=204)


# --- Search ---


@app.get("/search")
def search(
    user_id: UserId, q: Annotated[str, Query(min_length=1, max_length=100)]
) -> SearchResults:
    return service.search(user_id, q)


# AWS Lambda entry point (API Gateway HTTP API, payload v2).
handler = Mangum(app, lifespan="off")
