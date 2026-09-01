"""
Unit Tests for Security, Token Generation, and Password Hashing
"""

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    raw = "hero_secure_password"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_flow():
    token = create_access_token(
        subject="usr-test-123",
        username="hero_lead_eng",
        roles=["ENGINEER", "ADMIN"],
    )
    payload = decode_access_token(token)
    assert payload.sub == "usr-test-123"
    assert payload.username == "hero_lead_eng"
    assert "ADMIN" in payload.roles
