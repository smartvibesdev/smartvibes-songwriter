from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from mangum import Mangum
from pydantic import BaseModel

app = FastAPI(title="SmartVibes Songwriter API")


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
def me(claims: Annotated[dict[str, str], Depends(get_claims)]) -> Me:
    return Me(user_id=claims["sub"], email=claims.get("email"))


# AWS Lambda entry point (API Gateway HTTP API, payload v2).
handler = Mangum(app, lifespan="off")
