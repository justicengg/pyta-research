"""Unit tests for the dashboard router — INV-47.

Test matrix (≥ 4 tests)
-----------------------
test_dashboard_returns_200              — GET /dashboard returns HTTP 200
test_dashboard_content_type_is_html    — Content-Type header contains text/html
test_dashboard_contains_chartjs_cdn    — Chart.js CDN script tag present
test_dashboard_contains_api_endpoints  — JS fetch calls reference /api/v1/ endpoints
test_dashboard_no_auth_when_key_set    — /dashboard is open even when api_key is configured
test_dashboard_contains_api_key_meta   — <meta name="api-key"> tag is present in HTML
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

# ── patch targets ──────────────────────────────────────────────────────────────

_BG_SCHED    = 'src.api.app.BackgroundScheduler'
_PIPELINE    = 'src.api.app.PipelineScheduler'
_SETTINGS_D  = 'src.api.deps.settings'
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
    return m


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """TestClient with background scheduler suppressed."""
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS_D, cfg), \
         patch(_SETTINGS_DB, cfg):
        app = create_app()
        with TestClient(app) as c:
            yield c


# ── tests ──────────────────────────────────────────────────────────────────────

class TestDashboardRouter:
    def test_dashboard_returns_200(self, client):
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_dashboard_content_type_is_html(self, client):
        resp = client.get('/dashboard')
        assert 'text/html' in resp.headers['content-type']

    def test_dashboard_contains_chartjs_cdn(self, client):
        resp = client.get('/dashboard')
        assert 'chart.js' in resp.text.lower()

    def test_dashboard_contains_api_endpoints(self, client):
        body = client.get('/dashboard').text
        assert '/api/v1/decision/evaluate' in body
        assert '/api/v1/risk/check' in body
        assert '/api/v1/portfolio/snapshot' in body

    def test_dashboard_no_auth_when_key_set(self):
        """Dashboard must be accessible without X-API-Key even when api_key is configured."""
        cfg = _mock_settings(api_key='supersecret')
        with patch(_BG_SCHED, return_value=_mock_bg()), \
             patch(_PIPELINE), \
             patch(_SETTINGS_D, cfg), \
             patch(_SETTINGS_DB, cfg):
            app = create_app()
            with TestClient(app) as c:
                resp = c.get('/dashboard')
        assert resp.status_code == 200

    def test_dashboard_contains_api_key_meta(self, client):
        resp = client.get('/dashboard')
        assert 'name="api-key"' in resp.text
