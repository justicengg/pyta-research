"""End-to-end integration tests: portfolio → strategy card → pipeline → respond → trade_log."""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.db.models import ActionQueue, RawPrice, StrategyCard, TradeLog
from src.db.session import configure_engine, get_session
from src.decision.advisor import DecisionAdvisor

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


def _auth_headers(client: TestClient) -> dict:
    client.get('/dashboard')
    client.post('/dashboard/login', json={'token': 'dash-secret'})
    client.get('/dashboard')
    csrf = client.cookies.get('dashboard_csrf') or ''
    return {'X-CSRF-Token': csrf, 'origin': 'http://testserver'}


class TestFullLoop:

    def test_import_card_queue_respond_trade_log(self, client: TestClient):
        """Full loop: import snapshot → create card → generate queue → respond → trade_log updated."""
        headers = _auth_headers(client)
        today = date.today()

        # 1. Import portfolio snapshot
        resp = client.post('/dashboard/portfolio-snapshot', json={
            'positions': [
                {'symbol': 'BABA', 'market': 'US', 'shares': 100, 'avg_cost': 85.0},
            ],
        }, headers=headers)
        assert resp.status_code == 200

        # 2. Create strategy card from template
        resp = client.post('/dashboard/cards/from-template', json={
            'template': 'value_basic',
            'symbol': 'BABA',
            'market': 'US',
        }, headers=headers)
        assert resp.status_code == 200
        card_id = resp.json()['card_id']

        # Seed a price row so portfolio tracker can compute current_price
        with get_session() as session:
            session.add(RawPrice(
                symbol='BABA', market='US', trade_date=today,
                open=80, high=82, low=78, close=80, volume=1000000,
                source='yfinance',
            ))
            session.commit()

        # 3. Run generate_queue (the step that scheduler would run)
        with get_session() as session:
            total = DecisionAdvisor().generate_queue(
                asof=today,
                session=session,
                price_source_cn='baostock',
                price_source_us='yfinance',
                max_position_pct=0.20,
                max_positions=10,
                max_drawdown_pct=0.15,
            )
            session.commit()
        assert total >= 1

        # 4. Fetch the pending action
        with get_session() as session:
            action = session.scalar(
                select(ActionQueue)
                .where(ActionQueue.symbol == 'BABA', ActionQueue.status == 'pending')
                .order_by(ActionQueue.id.desc())
                .limit(1)
            )
            assert action is not None
            action_id = action.id
            action_type = action.action

        # 5. Respond accepted with execution details
        resp = client.post('/dashboard/respond', json={
            'action_id': action_id,
            'response': 'accepted',
            'executed_price': 79.5,
            'executed_quantity': 100,
        }, headers=headers)
        assert resp.status_code == 200

        # 6. Verify trade_log was created
        with get_session() as session:
            trade_logs = list(session.scalars(
                select(TradeLog).where(TradeLog.note == 'dashboard_respond')
            ).all())
            # Only actions that map to buy/sell produce trade_logs
            if action_type in ('exit', 'trim', 'enter', 'add'):
                assert len(trade_logs) == 1
                assert trade_logs[0].symbol == 'BABA'
                assert float(trade_logs[0].price) == 79.5
            else:
                # hold/watch/review don't produce trade_logs
                assert len(trade_logs) == 0

    def test_pipeline_generates_action_queue(self, client: TestClient):
        """Seed data → run generate_queue → verify action_queue populated."""
        today = date.today()
        headers = _auth_headers(client)

        # Seed a strategy card (active, with stop_loss)
        with get_session() as session:
            card = StrategyCard(
                symbol='TSLA', market='US', status='active',
                stop_loss_price=150.0,
                exit_rules={'stop_loss': {'threshold': -0.10}},
            )
            session.add(card)
            session.commit()

        # No positions, no price → should generate "enter" action for active card
        with get_session() as session:
            total = DecisionAdvisor().generate_queue(
                asof=today,
                session=session,
                price_source_cn='baostock',
                price_source_us='yfinance',
                max_position_pct=0.20,
                max_positions=10,
                max_drawdown_pct=0.15,
            )
            session.commit()

        assert total >= 1
        with get_session() as session:
            actions = list(session.scalars(
                select(ActionQueue)
                .where(ActionQueue.symbol == 'TSLA', ActionQueue.generated_date == today)
            ).all())
            assert len(actions) >= 1
            assert actions[0].action == 'enter'
            assert actions[0].status == 'pending'
