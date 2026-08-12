import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

AFFECTED_ENDPOINTS = [
    "/api/v1/exams",
    "/api/v1/questions",
    "/api/v1/students",
    "/api/v1/exam-sessions",
    "/api/v1/academic/departments",
    "/api/v1/academic/sections",
    "/api/v1/academic/semesters",
]

PROD_ORIGIN = "https://fabgate.vercel.app"
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]
VERCEL_PREVIEW_ORIGIN = "https://my-app-git-feature-branch.vercel.app"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", AFFECTED_ENDPOINTS)
async def test_options_preflight_prod_origin(endpoint: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            endpoint,
            headers={
                "Origin": PROD_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization, content-type, x-request-id",
            },
        )
        assert response.status_code in (200, 204), f"Preflight failed for {endpoint} with status {response.status_code}"
        assert response.headers.get("access-control-allow-origin") == PROD_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods or "*" in allow_methods


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", AFFECTED_ENDPOINTS)
async def test_actual_request_prod_origin(endpoint: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            endpoint,
            headers={
                "Origin": PROD_ORIGIN,
            },
        )
        assert response.headers.get("access-control-allow-origin") == PROD_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
@pytest.mark.parametrize("dev_origin", DEV_ORIGINS)
async def test_dev_origins_preserved(dev_origin: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/exams",
            headers={
                "Origin": dev_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == dev_origin
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_vercel_preview_origins_allowed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/exams",
            headers={
                "Origin": VERCEL_PREVIEW_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == VERCEL_PREVIEW_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_disallowed_origin_blocked():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/exams",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") != "https://malicious-site.com"
