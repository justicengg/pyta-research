"""yfinance enricher — fetches price snapshot + fundamentals and maps to CanonicalSecurityData.

This is the $0-cost built-in data source for the free/trial tier.
yfinance scrapes Yahoo Finance; it is sufficient for US-listed securities.

Usage:
    from src.data.enrichers.yfinance_enricher import fetch_canonical, fetch_canonical_cached
    data = fetch_canonical("NVDA", "US")
    print(data.to_agent_context())
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from sqlalchemy.orm import Session

from src.data.canonical import CanonicalSecurityData, Fundamentals, PriceSnapshot
from src.data.store import CanonicalDataStore

logger = logging.getLogger(__name__)

_store = CanonicalDataStore()


def fetch_canonical_cached(symbol: str, market: str, session: Session) -> CanonicalSecurityData:
    """Return a canonical snapshot, using the DB cache when the data is fresh.

    Cache TTL is 5 minutes (CACHE_TTL_SECONDS).  On a cache miss the function
    falls through to a live yfinance fetch and writes the result back to the DB.

    Blocks synchronously — call via run_in_executor in async contexts.
    """
    cached = _store.get_fresh(session, symbol, market, source="yfinance")
    if cached is not None:
        return cached

    fresh = fetch_canonical(symbol, market)
    try:
        _store.upsert(session, fresh)
        session.commit()
    except Exception as exc:
        logger.warning("Failed to cache canonical data for %s/%s: %s", symbol, market, exc)
        session.rollback()
    return fresh


def fetch_canonical(symbol: str, market: str) -> CanonicalSecurityData:
    """Fetch a canonical security snapshot for the given symbol.

    Blocks synchronously — call via run_in_executor in async contexts.
    Raises on network errors; callers should handle and degrade gracefully.
    """
    ticker = yf.Ticker(symbol)

    # ── 1. info dict (fundamentals + current price) ────────────────────────────
    info: dict[str, Any] = {}
    try:
        raw_info = ticker.info
        if isinstance(raw_info, dict):
            info = raw_info
    except Exception as exc:
        logger.warning("yfinance .info failed for %s: %s", symbol, exc)

    # ── 2. recent price history (5d) for 5-day change calculation ─────────────
    change_5d_pct: float | None = None
    try:
        hist = ticker.history(period="5d")
        if hist is not None and len(hist) >= 2:
            first = float(hist["Close"].iloc[0])
            last = float(hist["Close"].iloc[-1])
            if first > 0:
                change_5d_pct = (last - first) / first * 100
    except Exception as exc:
        logger.warning("yfinance .history failed for %s: %s", symbol, exc)

    # ── 3. Build price snapshot ────────────────────────────────────────────────
    current = _float(info.get("currentPrice") or info.get("regularMarketPrice"))
    prev_close = _float(info.get("regularMarketPreviousClose") or info.get("previousClose"))

    change_1d_pct: float | None = None
    if current is not None and prev_close and prev_close > 0:
        change_1d_pct = (current - prev_close) / prev_close * 100

    price = PriceSnapshot(
        current=current,
        prev_close=prev_close,
        open=_float(info.get("regularMarketOpen") or info.get("open")),
        high_52w=_float(info.get("fiftyTwoWeekHigh")),
        low_52w=_float(info.get("fiftyTwoWeekLow")),
        change_1d_pct=change_1d_pct,
        change_5d_pct=change_5d_pct,
        volume=_int(info.get("regularMarketVolume") or info.get("volume")),
        avg_volume_10d=_int(info.get("averageVolume10days") or info.get("averageDailyVolume10Day")),
    )

    # ── 4. Build fundamentals ──────────────────────────────────────────────────
    fundamentals = Fundamentals(
        market_cap=_float(info.get("marketCap")),
        pe_ratio=_float(info.get("trailingPE")),
        forward_pe=_float(info.get("forwardPE")),
        pb_ratio=_float(info.get("priceToBook")),
        eps_ttm=_float(info.get("trailingEps")),
        revenue_ttm=_float(info.get("totalRevenue")),
        revenue_growth=_float(info.get("revenueGrowth")),
        gross_margin=_float(info.get("grossMargins")),
        debt_to_equity=_float(info.get("debtToEquity")),
        dividend_yield=_float(info.get("dividendYield")),
    )

    # ── 5. Assemble canonical object ───────────────────────────────────────────
    return CanonicalSecurityData(
        symbol=symbol,
        market=market,
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        currency=info.get("currency"),
        price=price,
        fundamentals=fundamentals,
        fetched_at=datetime.now(timezone.utc),
        source="yfinance",
        raw_payload={},  # don't persist full info dict — can be MBs
    )


# ── helpers ────────────────────────────────────────────────────────────────────

def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
        return result if result == result else None  # reject NaN
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
