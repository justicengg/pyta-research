"""GET /dashboard — Jinja2 HTML decision dashboard.

Security hardening:
- No API key is injected into the HTML.
- Dashboard data is computed server-side and embedded as JSON payload blocks,
  so the browser does not need to call auth-protected /api/v1/... endpoints
  with secrets.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config.settings import settings
from src.db.session import get_session
from src.decision.advisor import DecisionAdvisor
from src.portfolio.tracker import PortfolioTracker
from src.risk.checker import RiskChecker

_TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


@router.get('/dashboard', response_class=HTMLResponse, tags=['dashboard'])
def dashboard(request: Request) -> HTMLResponse:
    """Render the decision dashboard HTML page."""
    asof = date.today()
    with get_session() as session:
        portfolio = PortfolioTracker().snapshot(
            asof=asof,
            session=session,
            price_source_cn=settings.price_source_cn,
            price_source_us=settings.price_source_us,
        )
        risk = RiskChecker().check(
            portfolio=portfolio,
            max_position_pct=settings.risk_max_position_pct,
            max_positions=settings.risk_max_positions,
            max_drawdown_pct=settings.risk_max_drawdown_pct,
        )
        decision = DecisionAdvisor().evaluate(
            asof=asof,
            session=session,
            price_source_cn=settings.price_source_cn,
            price_source_us=settings.price_source_us,
            max_position_pct=settings.risk_max_position_pct,
            max_positions=settings.risk_max_positions,
            max_drawdown_pct=settings.risk_max_drawdown_pct,
        )

    def _json_payload(obj: object) -> str:
        return json.dumps(asdict(obj), default=str)

    return _templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'portfolio_json': _json_payload(portfolio),
            'risk_json': _json_payload(risk),
            'decision_json': _json_payload(decision),
        },
    )
