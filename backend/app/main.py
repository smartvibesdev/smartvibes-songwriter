from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel

from app import service
from app.ai import budget
from app.ai import service as ai_service
from app.ai.claude import AiNotConfigured, AiUnavailable, TextGenerator, get_generator
from app.models import (
    MAX_TAG_LENGTH,
    MAX_TAGS,
    BudgetOut,
    Fragment,
    FragmentIn,
    GenerateIn,
    GenerateOut,
    ListParams,
    NotebookEntry,
    NotebookParams,
    Page,
    Scope,
    SearchResults,
    Song,
    SongIn,
    TagCount,
    TokenCount,
)

app = FastAPI(title="SmartVibes Songwriter API")


@app.exception_handler(service.NotFoundError)
def not_found_handler(request: Request, error: service.NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(AiNotConfigured)
def ai_not_configured_handler(request: Request, error: AiNotConfigured) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "AI is not set up yet"})


@app.exception_handler(AiUnavailable)
def ai_unavailable_handler(request: Request, error: AiUnavailable) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "The AI service could not be reached. Try again."},
    )


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
def list_songs(user_id: UserId, params: Annotated[ListParams, Query()]) -> Page[Song]:
    return service.query_songs(
        user_id,
        params.q,
        params.tag,
        params.year,
        params.sort,
        params.page,
        params.page_size,
    )


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
def list_fragments(
    user_id: UserId, params: Annotated[ListParams, Query()]
) -> Page[Fragment]:
    return service.query_fragments(
        user_id,
        params.q,
        params.tag,
        params.year,
        params.sort,
        params.page,
        params.page_size,
    )


@app.post("/fragments", status_code=201)
def create_fragment(user_id: UserId, data: FragmentIn) -> Fragment:
    return service.create_fragment(user_id, data)


@app.get("/fragments/random")
def random_fragments(
    user_id: UserId,
    count: Annotated[int, Query(ge=1, le=10)] = 1,
    tag: Annotated[str | None, Query(max_length=MAX_TAG_LENGTH)] = None,
    exclude: Annotated[str | None, Query(max_length=100)] = None,
) -> list[Fragment]:
    return service.random_fragments(user_id, count, tag, exclude)


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


@app.get("/notebook")
def list_notebook(
    user_id: UserId, params: Annotated[NotebookParams, Query()]
) -> Page[NotebookEntry]:
    return service.query_notebook(
        user_id,
        params.q,
        params.tag,
        params.year,
        params.sort,
        params.page,
        params.page_size,
        params.scope,
    )


# --- AI generation (every call goes through the token checkpoint in app/ai) ---


def _budget_out(usage: budget.Usage) -> BudgetOut:
    return BudgetOut(used=usage.used, limit=usage.limit, remaining=usage.remaining)


@app.get("/ai/usage")
def ai_usage(user_id: UserId) -> BudgetOut:
    return _budget_out(budget.get_usage(user_id))


@app.post("/ai/generate")
def ai_generate(
    user_id: UserId,
    body: GenerateIn,
    generator: Annotated[TextGenerator, Depends(get_generator)],
) -> GenerateOut:
    try:
        result = ai_service.generate(
            user_id, generator, body.kind, body.seed, body.dial
        )
    except budget.BudgetExceeded as error:
        if error.scope == "global":
            detail = "AI is paused for everyone for today. Try again tomorrow."
        else:
            detail = "You have used today's AI budget. It resets at midnight UTC."

        raise HTTPException(status_code=429, detail=detail) from error

    return GenerateOut(
        kind=result.kind,
        text=result.text,
        dial=result.dial,
        temperature=result.temperature,
        tokens=TokenCount(input=result.input_tokens, output=result.output_tokens),
        budget=_budget_out(result.usage),
    )


# --- Search ---


@app.get("/search")
def search(
    user_id: UserId,
    q: Annotated[str, Query(max_length=100)] = "",
    scope: Scope = "both",
    tag: Annotated[list[str] | None, Query(max_length=MAX_TAGS)] = None,
) -> SearchResults:
    return service.search(user_id, q, scope, tag)


@app.get("/tags")
def list_tags(user_id: UserId, scope: Scope = "both") -> list[TagCount]:
    return service.list_tags(user_id, scope)


# AWS Lambda entry point (API Gateway HTTP API, payload v2).
handler = Mangum(app, lifespan="off")
