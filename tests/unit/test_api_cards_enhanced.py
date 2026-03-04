from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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


def _create_card(status: str = 'draft', symbol: str = 'BABA') -> int:
    with real_get_session() as session:
        card = StrategyCard(symbol=symbol, market='US', status=status)
        session.add(card)
        session.flush()
        return card.id


def _create_history_rows(card_id: int, day: date, created_at: datetime) -> None:
    with real_get_session() as session:
        aq = ActionQueue(
            card_id=card_id,
            symbol='BABA',
            market='US',
            action='review',
            priority='normal',
            status='pending',
            rule_tag='review_due',
            generated_date=day,
        )
        session.add(aq)
        session.flush()
        ex = ExecutionLog(
            action_queue_id=aq.id,
            card_id=card_id,
            symbol='BABA',
            market='US',
            response='accepted',
            source='system_suggestion',
            created_at=created_at,
        )
        session.add(ex)
        session.flush()


def test_patch_valuation_anchor_success(client: TestClient):
    card_id = _create_card()
    payload = {
        'valuation_anchor': {
            'core_metric': 'PE',
            'fair_low': 10.0,
            'fair_high': 15.0,
            'extreme_low': 8.0,
            'extreme_high': 18.0,
        }
    }
    resp = client.patch(f'/api/v1/cards/{card_id}', json=payload)
    assert resp.status_code == 200
    assert resp.json()['valuation_anchor']['core_metric'] == 'PE'


def test_patch_invalid_valuation_anchor_returns_422(client: TestClient):
    card_id = _create_card()
    payload = {
        'valuation_anchor': {
            'core_metric': 'PE',
            'fair_low': 20.0,
            'fair_high': 15.0,
        }
    }
    resp = client.patch(f'/api/v1/cards/{card_id}', json=payload)
    assert resp.status_code == 422


def test_patch_status_legal_transition(client: TestClient):
    card_id = _create_card(status='draft')
    resp = client.patch(f'/api/v1/cards/{card_id}', json={'status': 'active'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'active'


def test_patch_status_illegal_transition_returns_400(client: TestClient):
    card_id = _create_card(status='draft')
    resp = client.patch(f'/api/v1/cards/{card_id}', json={'status': 'paused'})
    assert resp.status_code == 400
    assert 'Illegal status transition' in resp.json()['detail']


def test_patch_backward_compatible_old_fields(client: TestClient):
    card_id = _create_card()
    resp = client.patch(
        f'/api/v1/cards/{card_id}',
        json={'thesis': 'long-term cloud growth', 'position_pct': 0.12},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['thesis'] == 'long-term cloud growth'
    assert body['position_pct'] == 0.12


def test_get_history_returns_associated_records(client: TestClient):
    card_id = _create_card(status='active')
    _create_history_rows(card_id, date(2026, 3, 5), datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc))

    other_card_id = _create_card(status='active', symbol='MSFT')
    _create_history_rows(other_card_id, date(2026, 3, 5), datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc))

    resp = client.get(f'/api/v1/cards/{card_id}/history')
    assert resp.status_code == 200
    data = resp.json()
    assert data['action_queue']['total'] == 1
    assert data['execution_log']['total'] == 1
    assert data['action_queue']['items'][0]['card_id'] == card_id
    assert data['execution_log']['items'][0]['card_id'] == card_id


def test_get_history_pagination(client: TestClient):
    card_id = _create_card(status='active')
    for i in range(3):
        day = date(2026, 3, 1 + i)
        ts = datetime(2026, 3, 1 + i, 9, 0, tzinfo=timezone.utc)
        _create_history_rows(card_id, day, ts)

    resp = client.get(f'/api/v1/cards/{card_id}/history', params={'page': 2, 'page_size': 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data['page'] == 2
    assert data['page_size'] == 2
    assert data['action_queue']['total'] == 3
    assert data['execution_log']['total'] == 3
    assert len(data['action_queue']['items']) == 1
    assert len(data['execution_log']['items']) == 1


def test_get_history_date_filter(client: TestClient):
    card_id = _create_card(status='active')
    _create_history_rows(card_id, date(2026, 3, 1), datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc))
    _create_history_rows(card_id, date(2026, 3, 6), datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc))

    resp = client.get(
        f'/api/v1/cards/{card_id}/history',
        params={'start_date': '2026-03-05', 'end_date': '2026-03-07'},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['action_queue']['total'] == 1
    assert data['execution_log']['total'] == 1
