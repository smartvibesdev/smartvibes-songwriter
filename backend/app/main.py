from fastapi import FastAPI
from mangum import Mangum

app = FastAPI(title="SmartVibes Songwriter API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# AWS Lambda entry point (API Gateway HTTP API, payload v2).
handler = Mangum(app, lifespan="off")
