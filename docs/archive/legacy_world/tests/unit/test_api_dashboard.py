"""Unit tests for the dashboard router — hardened server-side payload mode.

Test matrix
-----------
test_dashboard_returns_200                     — GET /dashboard returns HTTP 200
test_dashboard_content_type_is_html           — Content-Type header contains text/html
test_dashboard_contains_chartjs_cdn           — Chart.js CDN script tag present
test_dashboard_contains_embedded_json_payload — risk/decision/portfolio JSON script blocks present
test_dashboard_does_not_expose_api_key        — no <meta name="api-key"> and no X-API-Key JS header
"""
from __future__ import annotations

from contextlib import nullcontext
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.types import DecisionReport, PortfolioSnapshot, RiskReport

# ── patch targets ──────────────────────────────────────────────────────────────

_BG_SCHED    = 'src.api.app.BackgroundScheduler'
_PIPELINE    = 'src.api.app.PipelineScheduler'
_SETTINGS_D  = 'src.api.deps.settings'
_SETTINGS_A  = 'src.api.app.settings'
_SETTINGS_DB = 'src.api.routers.dashboard.settings'
_GET_SESSION = 'src.api.routers.dashboard.get_session'
_TRACKER     = 'src.api.routers.dashboard.PortfolioTracker'
_CHECKER     = 'src.api.routers.dashboard.RiskChecker'
_ADVISOR     = 'src.api.routers.dashboard.DecisionAdvisor'


def _mock_bg():
    m = MagicMock()
    m.running = True
    return m


def _mock_settings(api_key: str = ''):
    m = MagicMock()
    m.api_key = api_key
    m.scheduler_timezone = 'Asia/Shanghai'
    m.scheduler_cron_hour = 18
    m.scheduler_cron_minute = 0
    m.api_enable_embedded_scheduler = False
    m.price_source_cn = 'baostock'
    m.price_source_us = 'yfinance'
    m.risk_max_position_pct = 0.20
    m.risk_max_positions = 10
    m.risk_max_drawdown_pct = 0.15
    m.dashboard_write_token = ''
    return m


def _portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        snapshot_date=date(2026, 3, 3),
        generated_at='2026-03-03T00:00:00+00:00',
        positions=[],
        total_unrealized_pnl=None,
    )


def _risk() -> RiskReport:
    return RiskReport(
        asof=date(2026, 3, 3),
        status='ok',
        violations=[],
        total_positions=0,
        total_cost_basis=None,
        total_market_value=None,
        portfolio_drawdown_pct=None,
        generated_at='2026-03-03T00:00:00+00:00',
    )


def _decision() -> DecisionReport:
    return DecisionReport(
        asof=date(2026, 3, 3),
        advice=[],
        risk_status='ok',
        risk_violations=0,
        total_positions=0,
        exit_count=0,
        trim_count=0,
        hold_count=0,
        enter_count=0,
        watch_count=0,
        generated_at='2026-03-03T00:00:00+00:00',
    )


@pytest.fixture
def client():
    """TestClient with scheduler and DB/business logic patched."""
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS_D, cfg), \
         patch(_SETTINGS_A, cfg), \
         patch(_SETTINGS_DB, cfg), \
         patch(_GET_SESSION, side_effect=lambda: nullcontext(MagicMock())), \
         patch(_TRACKER) as MockTracker, \
         patch(_CHECKER) as MockChecker, \
         patch(_ADVISOR) as MockAdvisor:
        MockTracker.return_value.snapshot.return_value = _portfolio()
        MockChecker.return_value.check.return_value = _risk()
        MockAdvisor.return_value.evaluate.return_value = _decision()

        app = create_app()
        with TestClient(app) as c:
            yield c


class TestDashboardRouter:
    def test_dashboard_returns_200(self, client):
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_dashboard_content_type_is_html(self, client):
        resp = client.get('/dashboard')
        assert 'text/html' in resp.headers['content-type']

    def test_dashboard_contains_chartjs_cdn(self, client):
        resp = client.get('/dashboard')
        assert 'chart.js' in resp.text.lower()

    def test_dashboard_contains_embedded_json_payload(self, client):
        body = client.get('/dashboard').text
        assert 'id="portfolio-data"' in body
        assert 'id="risk-data"' in body
        assert 'id="decision-data"' in body

    def test_dashboard_does_not_expose_api_key(self, client):
        body = client.get('/dashboard').text
        assert 'name="api-key"' not in body
        assert 'X-API-Key' not in body
