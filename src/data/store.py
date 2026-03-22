"""Canonical data store — SQLite-backed TTL cache for CanonicalSecurityData.

Each (symbol, market, source) triple has exactly one row in market_snapshot.
Reads return a fresh snapshot if fetched_at is within CACHE_TTL_SECONDS;
otherwise return None so the caller knows to re-fetch from the upstream source.

Usage::

    from src.data.store import CanonicalDataStore
    store = CanonicalDataStore()

    cached = store.get_fresh(session, "NVDA", "US")
    if cached is None:
        fresh = fetch_canonical("NVDA", "US")
        store.upsert(session, fresh)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.canonical import CanonicalSecurityData
from src.db.models import MarketSnapshot

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300  # 5 minutes


class CanonicalDataStore:
    """Write-through TTL cache that stores one snapshot row per (symbol, market, source)."""

    def get_fresh(
        self,
        session: Session,
        symbol: str,
        market: str,
        source: str = "yfinance",
    ) -> CanonicalSecurityData | None:
        """Return a cached snapshot if it is fresher than CACHE_TTL_SECONDS, else None."""
        stmt = select(MarketSnapshot).where(
            MarketSnapshot.symbol == symbol.upper(),
            MarketSnapshot.market == market.upper(),
            MarketSnapshot.source == source,
        )
        row = session.scalar(stmt)
        if row is None:
            logger.debug("cache miss (no row): %s/%s source=%s", symbol, market, source)
            return None

        now = datetime.now(timezone.utc)
        fetched = row.fetched_at
        # Ensure tz-aware comparison
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age_seconds = (now - fetched).total_seconds()
        if age_seconds > CACHE_TTL_SECONDS:
            logger.debug(
                "cache stale: %s/%s age=%.0fs ttl=%ds",
                symbol, market, age_seconds, CACHE_TTL_SECONDS,
            )
            return None

        logger.debug("cache hit: %s/%s age=%.0fs", symbol, market, age_seconds)
        try:
            return CanonicalSecurityData.model_validate_json(row.snapshot_json)
        except Exception as exc:
            logger.warning("cache row for %s/%s is corrupt: %s — ignoring", symbol, market, exc)
            return None

    def upsert(self, session: Session, canonical: CanonicalSecurityData) -> None:
        """Insert or update the snapshot row for this (symbol, market, source) triple."""
        symbol = canonical.symbol.upper()
        market = canonical.market.upper()
        source = canonical.source

        stmt = select(MarketSnapshot).where(
            MarketSnapshot.symbol == symbol,
            MarketSnapshot.market == market,
            MarketSnapshot.source == source,
        )
        row = session.scalar(stmt)

        snapshot_json = canonical.model_dump_json()
        fetched_at = canonical.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)

        if row is None:
            row = MarketSnapshot(
                symbol=symbol,
                market=market,
                source=source,
                snapshot_json=snapshot_json,
                fetched_at=fetched_at,
            )
            session.add(row)
            logger.debug("cache insert: %s/%s source=%s", symbol, market, source)
        else:
            row.snapshot_json = snapshot_json
            row.fetched_at = fetched_at
            logger.debug("cache update: %s/%s source=%s", symbol, market, source)

        session.flush()
