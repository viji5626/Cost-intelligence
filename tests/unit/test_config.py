"""
Unit Tests for Application Configuration
"""

from backend.app.core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.PROJECT_NAME == "HERO Vehicle Cost & Plant OPEX Intelligence Platform"
    assert settings.AIR_GAP_MODE is True
    assert settings.ENABLE_TELEMETRY is False
    assert settings.ALLOW_EXTERNAL_EGRESS is False
    assert "postgresql+asyncpg" in settings.SQLALCHEMY_DATABASE_URI
    assert "postgresql+psycopg2" in settings.SQLALCHEMY_SYNC_DATABASE_URI
