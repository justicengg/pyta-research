"""GET /api/v1/decision/evaluate — DecisionReport as JSON."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.config.settings import settings
from src.decision.advisor import DecisionAdvisor

router = APIRouter()


@router.get('/decision/evaluate', dependencies=[Depends(verify_api_key)])
def decision_evaluate(
    asof: Optional[date] = Query(None, description='ISO date YYYY-MM-DD (default: today)'),
    session: Session = Depends(get_session),
) -> dict:
    """Run the DecisionAdvisor and return a full DecisionReport (R1–R5 rules)."""
    report = DecisionAdvisor().evaluate(
        asof=asof or date.today(),
        session=session,
        price_source_cn=settings.price_source_cn,
        price_source_us=settings.price_source_us,
        max_position_pct=settings.risk_max_position_pct,
        max_positions=settings.risk_max_positions,
        max_drawdown_pct=settings.risk_max_drawdown_pct,
    )
    data = asdict(report)
    data['asof'] = report.asof.isoformat()
    return data
