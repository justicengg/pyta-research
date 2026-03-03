"""GET /api/v1/portfolio/snapshot — PortfolioSnapshot as JSON."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.config.settings import settings
from src.portfolio.tracker import PortfolioTracker

router = APIRouter()


@router.get('/portfolio/snapshot', dependencies=[Depends(verify_api_key)])
def portfolio_snapshot(
    asof: Optional[date] = Query(None, description='ISO date YYYY-MM-DD (default: today)'),
    session: Session = Depends(get_session),
) -> dict:
    """Return a full portfolio snapshot including positions, cost basis, and market value."""
    snap = PortfolioTracker().snapshot(
        asof=asof or date.today(),
        session=session,
        price_source_cn=settings.price_source_cn,
        price_source_us=settings.price_source_us,
    )
    data = asdict(snap)
    data['snapshot_date'] = snap.snapshot_date.isoformat()
    return data
