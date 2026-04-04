"""Async SQLAlchemy engine and session factory for SQLite."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from etf_trend.db.models import Base

_DEFAULT_DB_DIR = Path("data")
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "etf_trend.db"

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path.resolve()}"


async def init_db(url: str | None = None) -> None:
    """Create engine, session factory, and all tables.

    Call once at application startup (e.g. FastAPI lifespan).
    """
    global _engine, _session_factory  # noqa: PLW0603

    if url is None:
        _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        url = _build_url(_DEFAULT_DB_PATH)

    _engine = create_async_engine(url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session — suitable for FastAPI ``Depends``."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    async with _session_factory() as session:
        yield session
