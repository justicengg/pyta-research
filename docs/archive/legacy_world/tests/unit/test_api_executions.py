from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.deps import get_session
from src.db.models import ExecutionLog
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


def test_create_and_get_manual_execution(client: TestClient):
    resp = client.post(
        '/api/v1/executions',
        json={
            'symbol': 'BABA',
            'market': 'US',
            'source': 'manual_override',
            'response': 'accepted',
            'executed_price': 80.25,
            'executed_quantity': 10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    execution_id = body['id']
    get_resp = client.get(f'/api/v1/executions/{execution_id}')
    assert get_resp.status_code == 200
    assert get_resp.json()['source'] == 'manual_override'


def test_list_executions_with_filters(client: TestClient):
    with real_get_session() as session:
        session.add(
            ExecutionLog(
                action_queue_id=None,
                card_id=1,
                symbol='BABA',
                market='US',
                response='accepted',
                source='manual_override',
                created_at=datetime(2026, 3, 5, 1, 0, tzinfo=timezone.utc),
            )
        )
        session.add(
            ExecutionLog(
                action_queue_id=None,
                card_id=2,
                symbol='AAPL',
                market='US',
                response='accepted',
                source='external_trade',
                created_at=datetime(2026, 3, 8, 1, 0, tzinfo=timezone.utc),
            )
        )
        session.flush()

    resp = client.get(
        '/api/v1/executions',
        params={'card_id': 1, 'source': 'manual_override', 'date_from': '2026-03-05', 'date_to': '2026-03-06'},
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]['symbol'] == 'BABA'


def test_create_execution_naive_time_interpreted_as_shanghai_then_stored_utc(client: TestClient):
    resp = client.post(
        '/api/v1/executions',
        json={
            'symbol': 'TSLA',
            'market': 'US',
            'source': 'external_trade',
            'executed_at': '2026-03-05T10:00:00',
        },
    )
    assert resp.status_code == 200
    # 10:00 Asia/Shanghai == 02:00 UTC
    assert resp.json()['executed_at'].startswith('2026-03-05T02:00:00')


def test_executions_require_api_key_when_enabled(migrated_db):
    cfg = _mock_settings(api_key='secret')
    with patch(_BG_SCHED, return_value=_mock_bg()), patch(_PIPELINE), patch(_SETTINGS_D, cfg):
        app = create_app()
        with TestClient(app) as c:
            resp = c.get('/api/v1/executions')
    assert resp.status_code == 401
