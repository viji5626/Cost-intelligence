"""
Integration Tests for Health and Air-Gap Verification API
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["air_gap_mode"] is True
    assert data["telemetry_enabled"] is False


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["air_gap_verified"] is True


@pytest.mark.asyncio
async def test_air_gap_egress_blocking_middleware(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/health/",
        headers={"X-External-Fetch": "true"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "AIR_GAP_EGRESS_BLOCKED"
