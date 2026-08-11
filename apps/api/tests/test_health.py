import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /health
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in {"healthy", "unhealthy"}

        # GET /health/database
        res_db = await client.get("/health/database")
        assert res_db.status_code in {200, 503}
        data_db = res_db.json()
        assert "status" in data_db
        assert "database" in data_db
