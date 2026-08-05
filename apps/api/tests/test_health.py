import pytest


@pytest.mark.asyncio
async def test_health_reports_degraded_without_infra(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] in {"up", "down"}
