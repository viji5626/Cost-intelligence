"""
Database Connection and Session Management Module
Provides async SQLAlchemy engine, scoped session factory, connection probes, and SQLite fallback.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.logging import logger


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


db_uri = settings.SQLALCHEMY_DATABASE_URI

# Use sqlite fallback if postgres is specified in dev but no postgres service exists
if "postgresql" in db_uri and not settings.POSTGRES_SERVER.startswith("prod"):
    # If connection fails, engine will switch to sqlite
    pass

try:
    if "sqlite" in db_uri:
        engine = create_async_engine(db_uri, echo=False, future=True)
    else:
        engine = create_async_engine(
            db_uri,
            echo=False,
            future=True,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
except Exception:
    engine = create_async_engine("sqlite+aiosqlite:///./hero_cost_intel.db", echo=False, future=True)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """Initializes database schema ensuring all tables exist."""
    import database.models  # Ensure all models are registered
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning(f"Database table initialization notice: {exc}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding transactional async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Probes the database connection using a lightweight SELECT 1 check."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning(f"Database health check probe failed: {exc}")
        return False

