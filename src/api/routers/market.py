"""Market data endpoints — canonical security snapshot via yfinance."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/market/snapshot/{ticker}", dependencies=[Depends(verify_api_key)])
async def get_market_snapshot(ticker: str, market: str = "US") -> dict[str, Any]:
    """Fetch a canonical market snapshot for the given ticker.

    Returns price (current, 1d/5d change, 52w range, volume) and
    fundamentals (market cap, P/E, P/B, revenue, margins, etc.).

    Backed by yfinance — works for all US-listed securities, no API key required.
    Response time is typically 1-3 seconds.
    """
    try:
        from src.data.enrichers.yfinance_enricher import fetch_canonical
        canonical = await asyncio.get_event_loop().run_in_executor(
            None, fetch_canonical, ticker.upper(), market.upper()
        )
        return canonical.model_dump(mode="json")
    except Exception as exc:
        logger.error("Market snapshot failed for %s: %s", ticker, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market data for {ticker}: {exc}",
        )


@router.get("/market/snapshot/{ticker}/context", dependencies=[Depends(verify_api_key)])
async def get_market_snapshot_context(ticker: str, market: str = "US") -> dict[str, Any]:
    """Same as /snapshot but returns the compact agent-context format.

    This is the exact payload injected into agent prompts — useful for debugging
    what data the agents actually see.
    """
    try:
        from src.data.enrichers.yfinance_enricher import fetch_canonical
        canonical = await asyncio.get_event_loop().run_in_executor(
            None, fetch_canonical, ticker.upper(), market.upper()
        )
        return canonical.to_agent_context()
    except Exception as exc:
        logger.error("Market context failed for %s: %s", ticker, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market context for {ticker}: {exc}",
        )
