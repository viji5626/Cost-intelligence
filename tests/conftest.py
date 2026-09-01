"""
Pytest Configuration and Test Fixtures
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.core.security import create_access_token


@pytest_asyncio.fixture
async def async_client():
    """Yields an async HTTP test client connected to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def auth_headers():
    """Generates valid JWT authorization headers for testing authenticated endpoints."""
    token = create_access_token(
        subject="usr-test-001",
        username="test_engineer",
        roles=["ENGINEER", "ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}
