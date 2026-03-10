"""Tests for trade_log feedback loop in dashboard respond / executions."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.db.models import ActionQueue, ExecutionLog, StrategyCard, TradeLog
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


def _mock_settings():
    m = MagicMock()
    m.api_key = ''
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


def _seed_action(action_type: str = 'exit') -> int:
    with get_session() as session:
        card = StrategyCard(symbol='BABA', market='US', status='active')
        session.add(card)
        session.flush()
        action = ActionQueue(
            card_id=card.id,
            symbol='BABA',
            market='US',
            action=action_type,
            priority='urgent',
            status='pending',
            generated_date=date.today(),
            rule_tag='stop_loss_hit',
        )
        session.add(action)
        session.flush()
        return action.id


def _trade_logs() -> list[dict]:
    """Return trade logs as plain dicts to avoid DetachedInstanceError."""
    with get_session() as session:
        rows = list(session.scalars(select(TradeLog).order_by(TradeLog.id)).all())
        return [
            {
                'symbol': r.symbol,
                'market': r.market,
                'direction': r.direction,
                'price': float(r.price),
                'shares': float(r.shares),
                'amount': float(r.amount),
                'note': r.note,
                'card_id': r.card_id,
            }
            for r in rows
        ]


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


def _csrf(client: TestClient) -> str:
    client.get('/dashboard')
    return client.cookies.get('dashboard_csrf') or ''


def _login(client: TestClient) -> None:
    resp = client.post('/dashboard/login', json={'token': 'dash-secret'})
    assert resp.status_code == 200


def _auth_headers(client: TestClient) -> dict:
    _csrf(client)
    _login(client)
    csrf = _csrf(client)
    return {'X-CSRF-Token': csrf, 'origin': 'http://testserver'}


class TestRespondTradeLog:

    def test_respond_accepted_exit_creates_sell_trade_log(self, client: TestClient):
        action_id = _seed_action('exit')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
            'executed_price': 80.0,
            'executed_quantity': 100,
        }, headers=headers)
        assert resp.status_code == 200

        logs = _trade_logs()
        assert len(logs) == 1
        assert logs[0]['direction'] == 'sell'
        assert logs[0]['symbol'] == 'BABA'
        assert logs[0]['price'] == 80.0
        assert logs[0]['shares'] == 100
        assert logs[0]['amount'] == 8000.0
        assert logs[0]['note'] == 'dashboard_respond'

    def test_respond_accepted_enter_creates_buy_trade_log(self, client: TestClient):
        action_id = _seed_action('enter')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
            'executed_price': 85.5,
            'executed_quantity': 50,
        }, headers=headers)
        assert resp.status_code == 200

        logs = _trade_logs()
        assert len(logs) == 1
        assert logs[0]['direction'] == 'buy'

    def test_respond_accepted_without_price_no_trade_log(self, client: TestClient):
        action_id = _seed_action('exit')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
        }, headers=headers)
        assert resp.status_code == 200
        assert len(_trade_logs()) == 0

    def test_respond_rejected_no_trade_log(self, client: TestClient):
        action_id = _seed_action('exit')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'rejected',
            'executed_price': 80.0,
            'executed_quantity': 100,
        }, headers=headers)
        assert resp.status_code == 200
        assert len(_trade_logs()) == 0

    def test_respond_hold_action_no_trade_log(self, client: TestClient):
        action_id = _seed_action('hold')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
            'executed_price': 85.0,
            'executed_quantity': 100,
        }, headers=headers)
        assert resp.status_code == 200
        # hold is informational — no trade
        assert len(_trade_logs()) == 0

    def test_respond_trim_creates_sell(self, client: TestClient):
        action_id = _seed_action('trim')
        headers = _auth_headers(client)
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
            'executed_price': 90.0,
            'executed_quantity': 30,
        }, headers=headers)
        assert resp.status_code == 200

        logs = _trade_logs()
        assert len(logs) == 1
        assert logs[0]['direction'] == 'sell'
        assert logs[0]['shares'] == 30


class TestManualExecutionTradeLog:

    def test_manual_execution_creates_trade_log(self, client: TestClient):
        headers = _auth_headers(client)
        resp = client.post('/dashboard/executions', json={
            'symbol': 'AAPL',
            'market': 'US',
            'source': 'manual_override',
            'direction': 'buy',
            'executed_price': 178.0,
            'executed_quantity': 10,
        }, headers=headers)
        assert resp.status_code == 200

        logs = _trade_logs()
        assert len(logs) == 1
        assert logs[0]['symbol'] == 'AAPL'
        assert logs[0]['direction'] == 'buy'
        assert logs[0]['price'] == 178.0
        assert logs[0]['note'] == 'manual_override'

    def test_manual_execution_sell_direction(self, client: TestClient):
        headers = _auth_headers(client)
        resp = client.post('/dashboard/executions', json={
            'symbol': 'TSLA',
            'market': 'US',
            'source': 'external_trade',
            'direction': 'sell',
            'executed_price': 250.0,
            'executed_quantity': 5,
        }, headers=headers)
        assert resp.status_code == 200

        logs = _trade_logs()
        assert len(logs) == 1
        assert logs[0]['direction'] == 'sell'
        assert logs[0]['note'] == 'external_trade'

    def test_manual_execution_without_price_no_trade_log(self, client: TestClient):
        headers = _auth_headers(client)
        resp = client.post('/dashboard/executions', json={
            'symbol': 'AAPL',
            'market': 'US',
            'source': 'manual_override',
        }, headers=headers)
        assert resp.status_code == 200
        assert len(_trade_logs()) == 0

    def test_manual_execution_invalid_direction_rejected(self, client: TestClient):
        headers = _auth_headers(client)
        resp = client.post('/dashboard/executions', json={
            'symbol': 'AAPL',
            'market': 'US',
            'source': 'manual_override',
            'direction': 'short',
            'executed_price': 178.0,
            'executed_quantity': 10,
        }, headers=headers)
        assert resp.status_code == 422
