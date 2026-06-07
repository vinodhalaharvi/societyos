"""
Tests for the FastAPI server.
Run with:  pytest tests/test_health.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from societyos.server.app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data