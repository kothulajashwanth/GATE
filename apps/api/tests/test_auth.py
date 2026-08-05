import pytest


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_internal_key_creates_system_user(client, internal_headers):
    response = await client.get("/api/v1/users/me", headers=internal_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "system@internal.examshield"
    assert body["role"] == "super_admin"


@pytest.mark.asyncio
async def test_bad_internal_key_rejected(client):
    response = await client.get("/api/v1/users/me", headers={"X-Internal-Key": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mint_token_requires_auth(client):
    response = await client.post("/api/v1/auth/token")
    assert response.status_code == 401
