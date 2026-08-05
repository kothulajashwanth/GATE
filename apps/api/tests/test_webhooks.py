import pytest


async def _send(client, headers, event, data):
    return await client.post(
        "/api/v1/webhooks/clerk",
        headers=headers,
        json={"event": event, "data": data},
    )


@pytest.mark.asyncio
async def test_clerk_webhook_requires_internal_key(client):
    response = await client.post(
        "/api/v1/webhooks/clerk", json={"event": "user.created", "data": {"id": "x"}}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_created_upserts_user(client, internal_headers):
    response = await _send(
        client,
        internal_headers,
        "user.created",
        {
            "id": "clerk_123",
            "email_addresses": [
                {"id": "ea1", "email_address": "student1@example.com"},
            ],
            "primary_email_address_id": "ea1",
            "first_name": "Jane",
            "last_name": "Doe",
            "public_metadata": {"role": "student"},
        },
    )
    assert response.status_code == 200

    # system user already created via /me in a prior test; here the student is new


    # verify via a fresh session-less query using the same in-memory engine is
    # not possible here (dependency-scoped), so check through the API instead
    response = await client.get("/api/v1/users", headers=internal_headers)
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "student1@example.com" in emails
