"""Unit tests for FastAPI foundation — auth middleware + /health + /api/v1/ping.

Test matrix
-----------
TestHealth          — GET /health always returns 200 regardless of auth config
TestPingNoAuth      — GET /api/v1/ping when api_key is empty (auth disabled)
TestPingAuthEnabled — GET /api/v1/ping when api_key is set (auth enforced)

Fixtures
--------
All fixtures patch BackgroundScheduler and PipelineScheduler so no real
database connections or threads are created during tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

# ── helpers ───────────────────────────────────────────────────────────────────

_BG_SCHED = 'src.api.app.BackgroundScheduler'
_PIPELINE  = 'src.api.app.PipelineScheduler'
_SETTINGS  = 'src.api.deps.settings'


def _mock_bg():
    """Return a MagicMock that looks like a running BackgroundScheduler."""
    mock = MagicMock()
    mock.running = True
    return mock


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client_no_auth():
    """TestClient with auth disabled (api_key='')."""
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS) as mock_cfg:
        mock_cfg.api_key = ''
        mock_cfg.scheduler_timezone = 'Asia/Shanghai'
        mock_cfg.scheduler_cron_hour = 18
        mock_cfg.scheduler_cron_minute = 0
        mock_cfg.api_enable_embedded_scheduler = False
        app = create_app()
        with TestClient(app) as client:
            yield client


@pytest.fixture
def client_with_auth():
    """TestClient with API key = 'test-secret-key'."""
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS) as mock_cfg:
        mock_cfg.api_key = 'test-secret-key'
        mock_cfg.scheduler_timezone = 'Asia/Shanghai'
        mock_cfg.scheduler_cron_hour = 18
        mock_cfg.scheduler_cron_minute = 0
        mock_cfg.api_enable_embedded_scheduler = False
        app = create_app()
        with TestClient(app) as client:
            yield client


# ── TestHealth ────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client_no_auth):
        resp = client_no_auth.get('/health')
        assert resp.status_code == 200

    def test_health_body_has_status_ok(self, client_no_auth):
        resp = client_no_auth.get('/health')
        assert resp.json()['status'] == 'ok'

    def test_health_accessible_when_auth_enabled(self, client_with_auth):
        """Health endpoint should not require API key."""
        resp = client_with_auth.get('/health')
        assert resp.status_code == 200

    def test_health_wrong_key_still_200(self, client_with_auth):
        """Wrong API key on /health must not block it."""
        resp = client_with_auth.get('/health', headers={'X-API-Key': 'wrong'})
        assert resp.status_code == 200


# ── TestPingNoAuth ────────────────────────────────────────────────────────────

class TestPingNoAuth:
    def test_ping_no_header_returns_200_when_auth_disabled(self, client_no_auth):
        resp = client_no_auth.get('/api/v1/ping')
        assert resp.status_code == 200

    def test_ping_any_key_returns_200_when_auth_disabled(self, client_no_auth):
        resp = client_no_auth.get('/api/v1/ping', headers={'X-API-Key': 'anything'})
        assert resp.status_code == 200

    def test_ping_body_has_pong(self, client_no_auth):
        resp = client_no_auth.get('/api/v1/ping')
        assert resp.json() == {'pong': True}


# ── TestPingAuthEnabled ───────────────────────────────────────────────────────

class TestPingAuthEnabled:
    def test_ping_correct_key_returns_200(self, client_with_auth):
        resp = client_with_auth.get(
            '/api/v1/ping', headers={'X-API-Key': 'test-secret-key'}
        )
        assert resp.status_code == 200

    def test_ping_wrong_key_returns_401(self, client_with_auth):
        resp = client_with_auth.get(
            '/api/v1/ping', headers={'X-API-Key': 'wrong-key'}
        )
        assert resp.status_code == 401

    def test_ping_missing_key_returns_401(self, client_with_auth):
        resp = client_with_auth.get('/api/v1/ping')
        assert resp.status_code == 401

    def test_ping_401_body_has_detail(self, client_with_auth):
        resp = client_with_auth.get('/api/v1/ping')
        assert 'detail' in resp.json()
