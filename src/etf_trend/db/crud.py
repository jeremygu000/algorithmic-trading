"""CRUD helpers for the watchlist table."""

from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from etf_trend.db.models import WatchlistItem

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-^]{1,15}$")


def _normalize(symbol: str) -> str:
    s = symbol.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise ValueError(f"Invalid symbol: {symbol}")
    return s


async def list_watchlist(session: AsyncSession) -> list[str]:
    """Return all watchlist symbols ordered by insertion time."""
    stmt = select(WatchlistItem.symbol).order_by(WatchlistItem.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def add_symbol(session: AsyncSession, symbol: str) -> list[str]:
    """Add a symbol. If it already exists, silently skip."""
    sym = _normalize(symbol)
    existing = await session.execute(select(WatchlistItem).where(WatchlistItem.symbol == sym))
    if existing.scalar_one_or_none() is None:
        session.add(WatchlistItem(symbol=sym))
        await session.commit()
    return await list_watchlist(session)


async def remove_symbol(session: AsyncSession, symbol: str) -> list[str]:
    """Remove a symbol from the watchlist."""
    sym = _normalize(symbol)
    await session.execute(delete(WatchlistItem).where(WatchlistItem.symbol == sym))
    await session.commit()
    return await list_watchlist(session)


async def set_watchlist(session: AsyncSession, symbols: list[str]) -> list[str]:
    """Bulk-replace the entire watchlist."""
    normalized = list(dict.fromkeys(_normalize(s) for s in symbols))
    await session.execute(delete(WatchlistItem))
    for sym in normalized:
        session.add(WatchlistItem(symbol=sym))
    await session.commit()
    return await list_watchlist(session)
