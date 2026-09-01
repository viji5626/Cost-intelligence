"""
Integration Tests for System and Hardware Profile API
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hardware_profile_unauthorized(async_client: AsyncClient):
    # Unauthenticated request should be rejected with 401
    response = await async_client.get("/api/v1/system/hardware-profile")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hardware_profile_authorized(async_client: AsyncClient, auth_headers: dict):
    response = await async_client.get(
        "/api/v1/system/hardware-profile",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "tier" in data
    assert "cpu" in data
    assert "ram" in data
    assert "gpu" in data
    assert "supported_models" in data
