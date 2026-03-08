from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.config.settings import settings
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
    m.dashboard_write_token = 'dash-secret'
    return m


def _seed_card_and_action() -> int:
    with get_session() as session:
        card = StrategyCard(symbol='BABA', market='US', status='active')
        session.add(card)
        session.flush()
        action = ActionQueue(
            card_id=card.id,
            symbol='BABA',
            market='US',
            action='review',
            priority='normal',
            status='pending',
            generated_date=date.today(),
            rule_tag='review_due',
        )
        session.add(action)
        session.flush()
        return action.id


def _count_exec_logs(action_id: int) -> int:
    with get_session() as session:
        return len(list(session.scalars(select(ExecutionLog).where(ExecutionLog.action_queue_id == action_id)).all()))


def _snapshot_symbols() -> list[str]:
    with get_session() as session:
        rows = list(
            session.scalars(
                select(TradeLog).where(TradeLog.note == 'initial_snapshot').order_by(TradeLog.id.asc())
            ).all()
        )
        return [r.symbol for r in rows]


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


class TestDashboardV2:
    def test_dashboard_contains_three_tabs(self, client: TestClient):
        body = client.get('/dashboard').text
        assert 'tab-observe' in body
        assert 'tab-decide' in body
        assert 'tab-exec' in body

    def test_dashboard_no_api_key_leak(self, client: TestClient):
        body = client.get('/dashboard').text
        assert 'name="api-key"' not in body
        assert 'X-API-Key' not in body

    def test_login_fail_with_wrong_token(self, client: TestClient):
        resp = client.post('/dashboard/login', json={'token': 'wrong'})
        assert resp.status_code == 401

    def test_dashboard_respond_requires_auth(self, client: TestClient):
        action_id = _seed_card_and_action()
        csrf = _csrf(client)
        resp = client.post(
            '/dashboard/respond',
            json={'action_id': action_id, 'response': 'accepted'},
            headers={'X-CSRF-Token': csrf, 'origin': 'http://testserver'},
        )
        assert resp.status_code == 403

    def test_dashboard_respond_csrf_fail(self, client: TestClient):
        action_id = _seed_card_and_action()
        _csrf(client)
        _login(client)
        resp = client.post(
            '/dashboard/respond',
            json={'action_id': action_id, 'response': 'accepted'},
            headers={'X-CSRF-Token': 'bad', 'origin': 'http://testserver'},
        )
        assert resp.status_code == 403

    def test_dashboard_respond_success_writes_execution(self, client: TestClient):
        action_id = _seed_card_and_action()
        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        resp = client.post(
            '/dashboard/respond',
            json={'action_id': action_id, 'response': 'accepted', 'request_id': 'req-1'},
            headers={'X-CSRF-Token': csrf, 'origin': 'http://testserver'},
        )
        assert resp.status_code == 200
        assert _count_exec_logs(action_id) == 1

    def test_dashboard_respond_repeat_returns_409(self, client: TestClient):
        action_id = _seed_card_and_action()
        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        first = client.post(
            '/dashboard/respond',
            json={'action_id': action_id, 'response': 'accepted'},
            headers={'X-CSRF-Token': csrf, 'origin': 'http://testserver'},
        )
        assert first.status_code == 200
        second = client.post(
            '/dashboard/respond',
            json={'action_id': action_id, 'response': 'rejected'},
            headers={'X-CSRF-Token': csrf, 'origin': 'http://testserver'},
        )
        assert second.status_code == 409
        assert _count_exec_logs(action_id) == 1

    def test_dashboard_execution_create_requires_auth_and_csrf(self, client: TestClient):
        resp = client.post(
            '/dashboard/executions',
            json={'symbol': 'BABA', 'market': 'US', 'source': 'manual_override'},
            headers={'origin': 'http://testserver'},
        )
        assert resp.status_code == 403

        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        ok = client.post(
            '/dashboard/executions',
            json={'symbol': 'BABA', 'market': 'US', 'source': 'manual_override', 'request_id': 'req-2'},
            headers={'origin': 'http://testserver', 'X-CSRF-Token': csrf},
        )
        assert ok.status_code == 200

    def test_dashboard_snapshot_invalid_payload_does_not_clear_existing_snapshot(self, client: TestClient):
        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        headers = {'origin': 'http://testserver', 'X-CSRF-Token': csrf}

        first = client.post(
            '/dashboard/portfolio-snapshot',
            json={'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 10, 'avg_cost': 100}]},
            headers=headers,
        )
        assert first.status_code == 200
        assert _snapshot_symbols() == ['AAPL']

        bad = client.post(
            '/dashboard/portfolio-snapshot',
            json={'positions': [{'symbol': 'BABA', 'market': 'US', 'shares': 0, 'avg_cost': 80}]},
            headers=headers,
        )
        assert bad.status_code == 422
        assert _snapshot_symbols() == ['AAPL']

    def test_dashboard_snapshot_non_numeric_returns_422(self, client: TestClient):
        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        resp = client.post(
            '/dashboard/portfolio-snapshot',
            json={'positions': [{'symbol': 'AAPL', 'market': 'US', 'shares': 'abc', 'avg_cost': 100}]},
            headers={'origin': 'http://testserver', 'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 422

    def test_dashboard_create_card_from_template_validates_rules(self, client: TestClient):
        _csrf(client)
        _login(client)
        csrf = _csrf(client)
        resp = client.post(
            '/dashboard/cards/from-template',
            json={
                'template': 'value_basic',
                'symbol': 'TSLA',
                'market': 'US',
                'overrides': {'risk_rules': {'stock_max_loss_pct': 1.5}},
            },
            headers={'origin': 'http://testserver', 'X-CSRF-Token': csrf},
        )
        assert resp.status_code == 422
