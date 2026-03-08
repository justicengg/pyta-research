"""Tests for POST /api/v1/portfolio/snapshot — position import."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.db.models import TradeLog
from src.db.session import configure_engine, get_session

_BG_SCHED = 'src.api.app.BackgroundScheduler'
_PIPELINE = 'src.api.app.PipelineScheduler'
_SETTINGS_D = 'src.api.deps.settings'
_SETTINGS_A = 'src.api.app.settings'
_SETTINGS_DB = 'src.api.routers.dashboard.settings'


def _mock_bg():
    m = MagicMock()
    m.running = True
    return m


def _mock_settings(api_key: str = 'test-key'):
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
    m.dashboard_write_token = 'dash-secret'
    return m


@pytest.fixture
def client(migrated_db):
    configure_engine(migrated_db)
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS_D, cfg), \
         patch(_SETTINGS_A, cfg), \
         patch(_SETTINGS_DB, cfg):
        app = create_app()
        with TestClient(app) as c:
            yield c


AUTH = {'X-API-Key': 'test-key'}


class TestPortfolioSnapshotImport:

    def test_import_creates_trade_log_records(self, client: TestClient):
        resp = client.post('/api/v1/portfolio/snapshot', json={
            'positions': [
                {'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0},
                {'symbol': 'BABA', 'market': 'US', 'shares': 100, 'avg_cost': 85.5},
            ],
            'snapshot_date': '2026-03-08',
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data['imported'] == 2

        with get_session() as session:
            rows = session.execute(select(TradeLog)).scalars().all()
            assert len(rows) == 2
            symbols = {r.symbol for r in rows}
            assert symbols == {'AAPL', 'BABA'}
            for r in rows:
                assert r.direction == 'buy'
                assert r.note == 'initial_snapshot'

    def test_import_is_idempotent(self, client: TestClient):
        payload = {
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0}],
        }
        client.post('/api/v1/portfolio/snapshot', json=payload, headers=AUTH)
        client.post('/api/v1/portfolio/snapshot', json=payload, headers=AUTH)

        with get_session() as session:
            rows = session.execute(select(TradeLog)).scalars().all()
            assert len(rows) == 1  # not 2

    def test_import_replaces_previous_snapshot(self, client: TestClient):
        client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0}],
        }, headers=AUTH)
        client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'BABA', 'market': 'US', 'shares': 100, 'avg_cost': 85.0}],
        }, headers=AUTH)

        with get_session() as session:
            rows = session.execute(select(TradeLog)).scalars().all()
            assert len(rows) == 1
            assert rows[0].symbol == 'BABA'

    def test_import_returns_price_warnings(self, client: TestClient):
        resp = client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'UNKNOWN', 'market': 'US', 'shares': 10, 'avg_cost': 100.0}],
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['warnings']) == 1
        assert 'UNKNOWN' in data['warnings'][0]

    def test_import_requires_auth(self, client: TestClient):
        resp = client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0}],
        })
        assert resp.status_code == 401

    def test_import_validates_positive_shares(self, client: TestClient):
        resp = client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': -10, 'avg_cost': 178.0}],
        }, headers=AUTH)
        assert resp.status_code == 422

    def test_import_calculates_amount(self, client: TestClient):
        client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0}],
        }, headers=AUTH)

        with get_session() as session:
            row = session.execute(select(TradeLog)).scalars().first()
            assert float(row.amount) == 8900.0

    def test_import_default_snapshot_date_is_today(self, client: TestClient):
        resp = client.post('/api/v1/portfolio/snapshot', json={
            'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 50, 'avg_cost': 178.0}],
        }, headers=AUTH)
        data = resp.json()
        assert data['snapshot_date'] == date.today().isoformat()
