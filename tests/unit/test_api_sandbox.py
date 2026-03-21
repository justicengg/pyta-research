"""Tests for secondary-market sandbox API endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.api.app import create_app
from src.db.session import configure_engine, get_session
from src.sandbox.schemas.memory import Checkpoint, ReportRecord, SandboxSession
from tests.helpers.sandbox_assertions import assert_sandbox_records_consistent

_BG_SCHED = "src.api.app.BackgroundScheduler"
_PIPELINE = "src.api.app.PipelineScheduler"
_SETTINGS_D = "src.api.deps.settings"
_SETTINGS_A = "src.api.app.settings"
_SETTINGS_DB = "src.api.routers.dashboard.settings"
_SETTINGS_LLM = "src.sandbox.llm.client.settings"


def _mock_bg():
    m = MagicMock()
    m.running = True
    return m


def _mock_settings(api_key: str = "test-key"):
    m = MagicMock()
    m.api_key = api_key
    m.scheduler_timezone = "Asia/Shanghai"
    m.scheduler_cron_hour = 18
    m.scheduler_cron_minute = 0
    m.api_enable_embedded_scheduler = False
    m.price_source_cn = "baostock"
    m.price_source_us = "yfinance"
    m.risk_max_position_pct = 0.20
    m.risk_max_positions = 10
    m.risk_max_drawdown_pct = 0.15
    m.dashboard_write_token = "dash-secret"
    m.llm_provider = "openai_compatible"
    m.llm_api_key = ""
    m.llm_base_url = "https://api.openai.com/v1"
    m.llm_model = ""
    m.llm_timeout_seconds = 20.0
    return m


@pytest.fixture
def client(migrated_db):
    configure_engine(migrated_db)
    cfg = _mock_settings()
    with patch(_BG_SCHED, return_value=_mock_bg()), \
         patch(_PIPELINE), \
         patch(_SETTINGS_D, cfg), \
         patch(_SETTINGS_A, cfg), \
         patch(_SETTINGS_DB, cfg), \
         patch(_SETTINGS_LLM, cfg):
        app = create_app()
        with TestClient(app) as c:
            yield c


AUTH = {"X-API-Key": "test-key"}


def _sample_payload() -> dict:
    return {
        "ticker": "0700.HK",
        "market": "HK",
        "round_timeout_ms": 5000,
        "events": [
            {
                "event_id": "evt-1",
                "event_type": "news",
                "content": "Tencent released a new AI product update.",
                "source": "gnews",
                "timestamp": "2026-03-21T10:00:00Z",
                "symbol": "0700.HK",
                "metadata": {"lang": "en"},
            }
        ],
    }


def test_run_sandbox_returns_round_complete_and_report(client: TestClient):
    resp = client.post("/api/v1/sandbox/run", json=_sample_payload(), headers=AUTH)
    assert resp.status_code == 200

    data = resp.json()
    assert data["sandbox_id"]
    assert data["round_complete"]["ticker"] == "0700.HK"
    assert data["round_complete"]["market"] == "HK"
    assert data["report"]["ticker"] == "0700.HK"
    assert len(data["report"]["perspective_synthesis"]) == 5

    with get_session() as session:
        sandbox_rows = session.execute(select(SandboxSession)).scalars().all()
        report_rows = session.execute(select(ReportRecord)).scalars().all()
        checkpoint_rows = session.execute(select(Checkpoint)).scalars().all()
        assert len(sandbox_rows) == 1
        assert len(report_rows) == 1
        assert len(checkpoint_rows) == 1
        assert_sandbox_records_consistent(
            session,
            sandbox_rows[0].id,
            expected_round=1,
            expected_report_count=1,
            expected_checkpoint_count=1,
            min_event_count=11,
            expected_snapshot_count=5,
        )


def test_get_sandbox_result_returns_persisted_report(client: TestClient):
    run_resp = client.post("/api/v1/sandbox/run", json=_sample_payload(), headers=AUTH)
    sandbox_id = run_resp.json()["sandbox_id"]

    result_resp = client.get(f"/api/v1/sandbox/{sandbox_id}/result", headers=AUTH)
    assert result_resp.status_code == 200

    data = result_resp.json()
    assert data["sandbox_id"] == sandbox_id
    assert data["report"]["report_type"] == "market_reading_report"
    assert data["latest_checkpoint"]["round"] == 1
    assert len(data["report"]["perspective_synthesis"]) == 5
