"""
Integration Tests for Authentication, Bootstrap, and Session Security (Phase P2)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.main import app
from backend.app.core.database import Base, get_db
from database.models.auth import User
from database.models.session import UserSession
from database.models.audit import AuditLog


@pytest.fixture
async def auth_test_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_01_first_boot_status_and_admin_creation(auth_test_client):
    client = auth_test_client
    # 1. Initial status should require setup
    res = await client.get("/api/v1/auth/bootstrap-status")
    assert res.status_code == 200
    data = res.json()
    assert data["is_bootstrapped"] is False
    assert data["requires_setup"] is True
    assert data["active_admins"] == 0

    # 2. Bootstrap admin with invalid weak password should fail
    weak_payload = {
        "username": "admin_hero",
        "email": "admin@hero.internal",
        "display_name": "Chief Administrator",
        "password": "weak",
        "confirm_password": "weak",
    }
    res = await client.post("/api/v1/auth/bootstrap-admin", json=weak_payload)
    assert res.status_code == 400

    # 3. Bootstrap admin with valid complex password should succeed
    valid_payload = {
        "username": "admin_hero",
        "email": "admin@hero.internal",
        "display_name": "Chief Administrator",
        "password": "HeroAdmin@2026!Secure",
        "confirm_password": "HeroAdmin@2026!Secure",
    }
    res = await client.post("/api/v1/auth/bootstrap-admin", json=valid_payload)
    assert res.status_code == 200
    auth_data = res.json()
    assert "access_token" in auth_data
    assert auth_data["username"] == "admin_hero"
    assert "ADMINISTRATOR" in auth_data["roles"]

    # 4. Subsequent bootstrap attempt should be rejected
    res = await client.post("/api/v1/auth/bootstrap-admin", json=valid_payload)
    assert res.status_code == 400
    err_text = str(res.json())
    assert "already bootstrapped" in err_text

    # 5. Bootstrap status should now be True
    res = await client.get("/api/v1/auth/bootstrap-status")
    assert res.status_code == 200
    assert res.json()["is_bootstrapped"] is True
    assert res.json()["active_admins"] == 1


@pytest.mark.asyncio
async def test_02_login_and_lockout_mechanism(auth_test_client):
    client = auth_test_client
    # Create user via bootstrap
    payload = {
        "username": "admin_hero",
        "email": "admin@hero.internal",
        "display_name": "Chief Administrator",
        "password": "HeroAdmin@2026!Secure",
        "confirm_password": "HeroAdmin@2026!Secure",
    }
    res = await client.post("/api/v1/auth/bootstrap-admin", json=payload)
    assert res.status_code == 200

    # Login with correct password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_hero", "password": "HeroAdmin@2026!Secure"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Introspect session
    session_res = await client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert session_res.status_code == 200
    assert session_res.json()["username"] == "admin_hero"

    # 4 failed attempts
    for _ in range(4):
        bad_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin_hero", "password": "wrong_password"},
        )
        assert bad_res.status_code == 401

    # 5th failed attempt triggers 5-minute lockout
    bad_res_5 = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_hero", "password": "wrong_password"},
    )
    assert bad_res_5.status_code == 401

    # 6th attempt should return HTTP 423 Locked
    locked_res = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_hero", "password": "HeroAdmin@2026!Secure"},
    )
    assert locked_res.status_code == 423
    assert "temporarily locked" in str(locked_res.json())


@pytest.mark.asyncio
async def test_03_logout_and_password_change(auth_test_client):
    client = auth_test_client
    payload = {
        "username": "admin_hero",
        "email": "admin@hero.internal",
        "display_name": "Chief Administrator",
        "password": "HeroAdmin@2026!Secure",
        "confirm_password": "HeroAdmin@2026!Secure",
    }
    boot_res = await client.post("/api/v1/auth/bootstrap-admin", json=payload)
    token = boot_res.json()["access_token"]

    # Change password
    ch_res = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "HeroAdmin@2026!Secure",
            "new_password": "HeroAdmin@2027!NewPass",
            "confirm_new_password": "HeroAdmin@2027!NewPass",
        },
    )
    assert ch_res.status_code == 200

    # Login with new password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_hero", "password": "HeroAdmin@2027!NewPass"},
    )
    assert login_res.status_code == 200
    new_token = login_res.json()["access_token"]

    # Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert logout_res.status_code == 200

    # Subsequent session check should fail
    session_res = await client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert session_res.status_code == 401
