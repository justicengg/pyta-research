"""Unit tests for REST API routers — INV-46.

Test matrix (≥ 12 tests)
------------------------
TestPortfolioRouter   — snapshot endpoint: 200, auth, invalid asof
TestRiskRouter        — risk/check endpoint: 200, auth, invalid asof
TestDecisionRouter    — decision/evaluate endpoint: 200, auth, invalid asof
TestCardsRouter       — list/get/patch: 200, 404, auth

Strategy: mock the business-logic layer (PortfolioTracker / RiskChecker /
DecisionAdvisor) via unittest.mock.patch so tests have no DB dependency for
portfolio/risk/decision.  Cards endpoints use a real migrated in-memory SQLite
session via the `migrated_db` fixture from conftest.py.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.deps import get_session
from src.types import (
    DecisionReport,
    PortfolioSnapshot,
    RiskReport,
)

# ── shared patch targets ───────────────────────────────────────────────────────

_BG_SCHED   = 'src.api.app.BackgroundScheduler'
_PIPELINE   = 'src.api.app.PipelineScheduler'
_SETTINGS_D = 'src.api.deps.settings'
_SETTINGS_P = 'src.api.routers.portfolio.settings'
_SETTINGS_R = 'src.api.routers.risk.settings'
_SETTINGS_DC = 'src.api.routers.decision.settings'
_TRACKER_P  = 'src.api.routers.portfolio.PortfolioTracker'
_TRACKER_R  = 'src.api.routers.risk.PortfolioTracker'
_CHECKER    = 'src.api.routers.risk.RiskChecker'
_ADVISOR    = 'src.api.routers.decision.DecisionAdvisor'

ASOF = date(2026, 3, 1)


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
    return m


# ── fixture dataclasses ───────────────────────────────────────────────────────

def _empty_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        snapshot_date=ASOF,
        positions=[],
        total_unrealized_pnl=None,
        generated_at='2026-03-01T10:00:00+00:00',
    )


def _empty_risk_report() -> RiskReport:
    return RiskReport(
        asof=ASOF, status='ok', violations=[],
        total_positions=0, total_cost_basis=None,
        total_market_value=None, portfolio_drawdown_pct=None,
        generated_at='2026-03-01T10:00:00+00:00',
    )


def _empty_decision_report() -> DecisionReport:
    return DecisionReport(
        asof=ASOF, advice=[],
        risk_status='ok', risk_violations=0,
        total_positions=0,
        exit_count=0, trim_count=0, hold_count=0,
        enter_count=0, watch_count=0,
        generated_at='2026-03-01T10:00:00+00:00',
    )


# ── base client fixture ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """TestClient with auth disabled and all business logic mocked."""
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS_D, cfg), \
         patch(_SETTINGS_P, cfg), \
         patch(_SETTINGS_R, cfg), \
         patch(_SETTINGS_DC, cfg), \
         patch(_TRACKER_P) as MockTrackerP, \
         patch(_TRACKER_R) as MockTrackerR, \
         patch(_CHECKER) as MockChecker, \
         patch(_ADVISOR) as MockAdvisor:

        MockTrackerP.return_value.snapshot.return_value = _empty_snapshot()
        MockTrackerR.return_value.snapshot.return_value = _empty_snapshot()
        MockChecker.return_value.check.return_value = _empty_risk_report()
        MockAdvisor.return_value.evaluate.return_value = _empty_decision_report()

        app = create_app()
        with TestClient(app) as c:
            yield c


# ── TestPortfolioRouter ───────────────────────────────────────────────────────

class TestPortfolioRouter:
    def test_snapshot_returns_200(self, client):
        resp = client.get('/api/v1/portfolio/snapshot')
        assert resp.status_code == 200

    def test_snapshot_body_has_snapshot_date(self, client):
        resp = client.get('/api/v1/portfolio/snapshot', params={'asof': '2026-03-01'})
        assert resp.status_code == 200
        assert 'snapshot_date' in resp.json()

    def test_snapshot_invalid_asof_returns_422(self, client):
        resp = client.get('/api/v1/portfolio/snapshot', params={'asof': 'not-a-date'})
        assert resp.status_code == 422

    def test_snapshot_requires_auth(self):
        cfg = _mock_settings(api_key='secret')
        with patch(_BG_SCHED, return_value=_mock_bg()), \
             patch(_PIPELINE), \
             patch(_SETTINGS_D, cfg), \
             patch(_SETTINGS_P, cfg), \
             patch(_TRACKER_P) as MockTrackerP:
            MockTrackerP.return_value.snapshot.return_value = _empty_snapshot()
            app = create_app()
            with TestClient(app) as c:
                resp = c.get('/api/v1/portfolio/snapshot')
        assert resp.status_code == 401


# ── TestRiskRouter ────────────────────────────────────────────────────────────

class TestRiskRouter:
    def test_risk_check_returns_200(self, client):
        resp = client.get('/api/v1/risk/check')
        assert resp.status_code == 200

    def test_risk_check_body_has_status(self, client):
        resp = client.get('/api/v1/risk/check')
        assert resp.json()['status'] == 'ok'

    def test_risk_invalid_asof_returns_422(self, client):
        resp = client.get('/api/v1/risk/check', params={'asof': 'bad'})
        assert resp.status_code == 422

    def test_risk_requires_auth(self):
        cfg = _mock_settings(api_key='secret')
        with patch(_BG_SCHED, return_value=_mock_bg()), \
             patch(_PIPELINE), \
             patch(_SETTINGS_D, cfg), \
             patch(_SETTINGS_R, cfg), \
             patch(_TRACKER_R) as MockTrackerR, \
             patch(_CHECKER) as MockChecker:
            MockTrackerR.return_value.snapshot.return_value = _empty_snapshot()
            MockChecker.return_value.check.return_value = _empty_risk_report()
            app = create_app()
            with TestClient(app) as c:
                resp = c.get('/api/v1/risk/check')
        assert resp.status_code == 401


# ── TestDecisionRouter ────────────────────────────────────────────────────────

class TestDecisionRouter:
    def test_decision_evaluate_returns_200(self, client):
        resp = client.get('/api/v1/decision/evaluate')
        assert resp.status_code == 200

    def test_decision_body_has_risk_status(self, client):
        resp = client.get('/api/v1/decision/evaluate')
        assert 'risk_status' in resp.json()

    def test_decision_invalid_asof_returns_422(self, client):
        resp = client.get('/api/v1/decision/evaluate', params={'asof': '99-99-99'})
        assert resp.status_code == 422

    def test_decision_requires_auth(self):
        cfg = _mock_settings(api_key='secret')
        with patch(_BG_SCHED, return_value=_mock_bg()), \
             patch(_PIPELINE), \
             patch(_SETTINGS_D, cfg), \
             patch(_SETTINGS_DC, cfg), \
             patch(_ADVISOR) as MockAdvisor:
            MockAdvisor.return_value.evaluate.return_value = _empty_decision_report()
            app = create_app()
            with TestClient(app) as c:
                resp = c.get('/api/v1/decision/evaluate')
        assert resp.status_code == 401


# ── TestCardsRouter ───────────────────────────────────────────────────────────

class TestCardsRouter:
    """Cards endpoints use a real migrated SQLite DB via migrated_db fixture."""

    @pytest.fixture(autouse=True)
    def _setup_client(self, migrated_db):
        from src.db.session import get_session as _real_get_session

        cfg = _mock_settings()
        with patch(_BG_SCHED, return_value=_mock_bg()), \
             patch(_PIPELINE), \
             patch(_SETTINGS_D, cfg):
            app = create_app()

            # Override get_session to use the migrated test DB
            def _override_session():
                with _real_get_session() as s:
                    yield s

            app.dependency_overrides[get_session] = _override_session
            with TestClient(app) as c:
                self.client = c
                yield
            app.dependency_overrides.clear()

    def test_list_cards_empty_returns_200(self):
        resp = self.client.get('/api/v1/cards')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_cards_with_status_filter(self):
        resp = self.client.get('/api/v1/cards', params={'status': 'active'})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_card_not_found_returns_404(self):
        resp = self.client.get('/api/v1/cards/9999')
        assert resp.status_code == 404

    def test_patch_card_not_found_returns_404(self):
        resp = self.client.patch('/api/v1/cards/9999', json={'status': 'active'})
        assert resp.status_code == 404
