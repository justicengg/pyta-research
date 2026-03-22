"""Tests for strategy card templates and from-template API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.db.models import StrategyCard
from src.db.session import configure_engine, get_session
from src.strategy.schemas import EntryRules, ExitRules, PositionRules, RiskRules
from src.strategy.templates import TEMPLATES, apply_overrides, get_template, list_templates

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


class TestTemplateDefinitions:

    def test_all_templates_have_required_keys(self):
        required = {'label', 'expected_cycle', 'review_cadence',
                    'position_rules', 'entry_rules', 'exit_rules', 'risk_rules'}
        for name, tpl in TEMPLATES.items():
            missing = required - set(tpl.keys())
            assert not missing, f'Template {name} missing keys: {missing}'

    def test_all_templates_pass_schema_validation(self):
        for name, tpl in TEMPLATES.items():
            PositionRules(**tpl['position_rules'])
            EntryRules(**tpl['entry_rules'])
            # ExitRules has optional fields; validate structure
            ExitRules(**{k: v for k, v in tpl['exit_rules'].items() if v is not None})
            RiskRules(**tpl['risk_rules'])

    def test_get_template_returns_deep_copy(self):
        t1 = get_template('value_basic')
        t2 = get_template('value_basic')
        t1['position_rules']['max_pct'] = 0.99
        assert t2['position_rules']['max_pct'] != 0.99

    def test_get_template_unknown_raises(self):
        with pytest.raises(KeyError, match='Unknown template'):
            get_template('nonexistent')

    def test_list_templates_returns_all(self):
        result = list_templates()
        names = {t['name'] for t in result}
        assert names == set(TEMPLATES.keys())

    def test_apply_overrides_deep_merge(self):
        tpl = get_template('value_basic')
        overrides = {'exit_rules': {'stop_loss': {'value': 0.15}}}
        result = apply_overrides(tpl, overrides)
        # stop_loss.method should be preserved, value should be overridden
        assert result['exit_rules']['stop_loss']['method'] == 'fixed_pct'
        assert result['exit_rules']['stop_loss']['value'] == 0.15
        # take_profit should be unchanged
        assert result['exit_rules']['take_profit']['threshold'] == 0.30


class TestFromTemplateAPI:

    def test_create_from_template_success(self, client: TestClient):
        resp = client.post('/api/v1/cards/from-template', json={
            'template': 'value_basic',
            'symbol': 'BABA',
            'market': 'US',
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data['symbol'] == 'BABA'
        assert data['status'] == 'active'
        assert data['exit_rules']['take_profit']['threshold'] == 0.30
        assert data['review_cadence'] == 'monthly'

    def test_create_from_template_with_overrides(self, client: TestClient):
        resp = client.post('/api/v1/cards/from-template', json={
            'template': 'defensive',
            'symbol': 'AAPL',
            'market': 'US',
            'overrides': {
                'exit_rules': {'stop_loss': {'value': 0.07}},
            },
        }, headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data['exit_rules']['stop_loss']['value'] == 0.07
        assert data['exit_rules']['stop_loss']['method'] == 'fixed_pct'

    def test_create_from_template_unknown(self, client: TestClient):
        resp = client.post('/api/v1/cards/from-template', json={
            'template': 'nonexistent',
            'symbol': 'BABA',
            'market': 'US',
        }, headers=AUTH)
        assert resp.status_code == 400

    def test_create_from_template_requires_auth(self, client: TestClient):
        resp = client.post('/api/v1/cards/from-template', json={
            'template': 'value_basic',
            'symbol': 'BABA',
            'market': 'US',
        })
        assert resp.status_code == 401

    def test_get_templates_list(self, client: TestClient):
        resp = client.get('/api/v1/cards/templates', headers=AUTH)
        assert resp.status_code == 200
        names = {t['name'] for t in resp.json()}
        assert 'value_basic' in names
        assert 'momentum' in names

    def test_card_persisted_in_db(self, client: TestClient):
        client.post('/api/v1/cards/from-template', json={
            'template': 'balanced',
            'symbol': 'TSLA',
            'market': 'US',
        }, headers=AUTH)
        with get_session() as session:
            cards = session.execute(select(StrategyCard)).scalars().all()
            assert len(cards) == 1
            assert cards[0].symbol == 'TSLA'
            assert cards[0].rules_version == 1
