from fastapi.testclient import TestClient

from app.main import app, get_claims

client = TestClient(app)


def test_me_requires_authentication():
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_identity_from_claims():
    app.dependency_overrides[get_claims] = lambda: {
        "sub": "abc-123",
        "email": "a@example.com",
    }
    try:
        response = client.get("/me")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"user_id": "abc-123", "email": "a@example.com"}


def test_me_through_lambda_handler():
    """Full path: an API Gateway (HTTP API v2) event with authorizer claims."""
    from app.main import handler

    event = {
        "version": "2.0",
        "routeKey": "GET /me",
        "rawPath": "/me",
        "rawQueryString": "",
        "headers": {"host": "example.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "http": {"method": "GET", "path": "/me", "sourceIp": "1.2.3.4"},
            "authorizer": {
                "jwt": {"claims": {"sub": "abc-123", "email": "a@example.com"}}
            },
        },
        "isBase64Encoded": False,
    }
    result = handler(event, None)
    assert result["statusCode"] == 200
    assert '"user_id":"abc-123"' in result["body"]
