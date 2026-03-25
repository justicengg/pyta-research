from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import settings
from src.sources import store

_SETTINGS = "src.api.deps.settings"


@pytest.fixture
def client(migrated_db: str):
    settings.database_url = migrated_db
    cfg = MagicMock()
    cfg.api_key = "test-key"
    cfg.api_enable_embedded_scheduler = False
    with patch(_SETTINGS, cfg):
        app = create_app()
        with TestClient(app) as test_client:
            yield test_client


AUTH = {"X-API-Key": "test-key"}


def test_sources_events_requires_api_key(client: TestClient):
    response = client.get("/api/v1/sources/events")
    assert response.status_code == 401


def test_sources_events_filters_by_symbol_and_returns_total(client: TestClient):
    store.save_events(
        [
            {
                "id": "evt-aapl",
                "connector_id": "connector-1",
                "provider_id": "gnews",
                "title": "Apple launches updated iPad lineup",
                "summary": "New hardware cycle starts.",
                "dimension": "event_driven",
                "impact_direction": "positive",
                "impact_strength": 0.7,
                "symbols": ["AAPL", "0700.HK"],
                "published_at": "2026-03-23T10:00:00+00:00",
                "ingested_at": "2026-03-23T10:01:00+00:00",
            },
            {
                "id": "evt-tsla",
                "connector_id": "connector-1",
                "provider_id": "gnews",
                "title": "Tesla faces delivery pressure",
                "summary": "Margin outlook turns mixed.",
                "dimension": "event_driven",
                "impact_direction": "negative",
                "impact_strength": 0.6,
                "symbols": ["TSLA"],
                "published_at": "2026-03-23T09:00:00+00:00",
                "ingested_at": "2026-03-23T09:01:00+00:00",
            },
        ]
    )

    response = client.get(
        "/api/v1/sources/events",
        params={"symbol": "AAPL", "limit": 20},
        headers=AUTH,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "evt-aapl"
    assert payload["items"][0]["symbols"] == ["AAPL", "0700.HK"]
