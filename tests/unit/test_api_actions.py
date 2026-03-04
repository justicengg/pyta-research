from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.api.deps import get_session
from src.db.models import ActionQueue, ExecutionLog, StrategyCard
from src.db.session import get_session as real_get_session

_BG_SCHED = 'src.api.app.BackgroundScheduler'
_PIPELINE = 'src.api.app.PipelineScheduler'
_SETTINGS_D = 'src.api.deps.settings'


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
    return m


@pytest.fixture()
def client(migrated_db):
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), patch(_PIPELINE), patch(_SETTINGS_D, cfg):
        app = create_app()

        def _override_session():
            with real_get_session() as s:
                yield s

        app.dependency_overrides[get_session] = _override_session
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


def _seed_action(generated: date = date(2026, 3, 5), status: str = 'pending', priority: str = 'normal') -> int:
    with real_get_session() as session:
        card = StrategyCard(symbol='BABA', market='US', status='active')
        session.add(card)
        session.flush()
        row = ActionQueue(
            card_id=card.id,
            symbol='BABA',
            market='US',
            action='review',
            priority=priority,
            status=status,
            generated_date=generated,
            rule_tag='review_due',
        )
        session.add(row)
        session.flush()
        return row.id


def _count_exec_logs(action_id: int) -> int:
    with real_get_session() as session:
        stmt = select(ExecutionLog).where(ExecutionLog.action_queue_id == action_id)
        return len(list(session.execute(stmt).scalars().all()))


def test_list_actions_with_filters(client: TestClient):
    _seed_action(generated=date(2026, 3, 5), status='pending', priority='urgent')
    _seed_action(generated=date(2026, 3, 4), status='accepted', priority='normal')
    resp = client.get('/api/v1/actions', params={'date': '2026-03-05', 'status': 'pending', 'priority': 'urgent'})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]['status'] == 'pending'


def test_list_actions_today_pending(client: TestClient):
    _seed_action(generated=date.today(), status='pending')
    _seed_action(generated=date.today(), status='accepted')
    resp = client.get('/api/v1/actions/today')
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]['status'] == 'pending'


def test_respond_accepted_updates_status_and_creates_execution_log(client: TestClient):
    action_id = _seed_action(status='pending')
    resp = client.post(f'/api/v1/actions/{action_id}/respond', json={'response': 'accepted'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'accepted'
    assert _count_exec_logs(action_id) == 1


def test_respond_rejected_also_creates_execution_log(client: TestClient):
    action_id = _seed_action(status='pending')
    resp = client.post(f'/api/v1/actions/{action_id}/respond', json={'response': 'rejected', 'reason': 'skip now'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'rejected'
    assert _count_exec_logs(action_id) == 1


def test_respond_repeat_returns_409_and_no_duplicate_log(client: TestClient):
    action_id = _seed_action(status='pending')
    first = client.post(f'/api/v1/actions/{action_id}/respond', json={'response': 'accepted'})
    assert first.status_code == 200
    second = client.post(f'/api/v1/actions/{action_id}/respond', json={'response': 'modified', 'modified_action': 'trim'})
    assert second.status_code == 409
    assert _count_exec_logs(action_id) == 1


def test_actions_require_api_key_when_enabled(migrated_db):
    cfg = _mock_settings(api_key='secret')
    with patch(_BG_SCHED, return_value=_mock_bg()), patch(_PIPELINE), patch(_SETTINGS_D, cfg):
        app = create_app()
        with TestClient(app) as c:
            resp = c.get('/api/v1/actions')
    assert resp.status_code == 401
