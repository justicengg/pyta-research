"""Source connector + event persistence — SQLite, same DB as settings_store.

Tables:
  source_connector — one row per connected provider
  source_event     — standardized events ingested from connectors
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path("pyta.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS source_connector (
            id            TEXT PRIMARY KEY,
            provider_id   TEXT NOT NULL,
            api_key       TEXT NOT NULL,
            custom_config TEXT,
            status        TEXT NOT NULL DEFAULT 'healthy',
            error_message TEXT,
            last_synced_at TEXT,
            created_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS source_event (
            id               TEXT PRIMARY KEY,
            connector_id     TEXT NOT NULL,
            provider_id      TEXT NOT NULL,
            title            TEXT NOT NULL,
            summary          TEXT,
            dimension        TEXT,
            impact_direction TEXT NOT NULL DEFAULT 'neutral',
            impact_strength  REAL NOT NULL DEFAULT 0.5,
            published_at     TEXT,
            ingested_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_source_event_ingested
            ON source_event (ingested_at DESC);
    """)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_connectors() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, provider_id, status, error_message, last_synced_at, created_at "
            "FROM source_connector ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_connector(connector_id: str) -> dict[str, Any] | None:
    import json
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM source_connector WHERE id = ?", (connector_id,)
        ).fetchone()
    if not row:
        return None
    r = dict(row)
    if r.get("custom_config"):
        r["custom_config"] = json.loads(r["custom_config"])
    return r


def create_connector(
    provider_id: str,
    api_key: str,
    custom_config: dict | None = None,
) -> str:
    """Insert a new connector and return its id."""
    import json
    connector_id = str(uuid.uuid4())
    config_json = json.dumps(custom_config) if custom_config else None
    with _conn() as conn:
        conn.execute(
            """INSERT INTO source_connector
               (id, provider_id, api_key, custom_config, status, created_at)
               VALUES (?, ?, ?, ?, 'healthy', ?)""",
            (connector_id, provider_id, api_key, config_json, _now()),
        )
        conn.commit()
    return connector_id


def update_status(connector_id: str, status: str, error_message: str | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            """UPDATE source_connector
               SET status = ?, error_message = ?, last_synced_at = ?
               WHERE id = ?""",
            (status, error_message, _now(), connector_id),
        )
        conn.commit()


def delete_connector(connector_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM source_connector WHERE id = ?", (connector_id,)
        )
        conn.commit()
    return cur.rowcount > 0


def get_api_key(connector_id: str) -> str | None:
    """Return raw api_key — only used internally by agent pipeline, never exposed to frontend."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT api_key FROM source_connector WHERE id = ?", (connector_id,)
        ).fetchone()
    return row[0] if row else None


# ── source_event ──────────────────────────────────────────────────────────────

def save_events(events: list[dict[str, Any]]) -> None:
    """Upsert a batch of events. Silently skips duplicates by id."""
    if not events:
        return
    with _conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO source_event
               (id, connector_id, provider_id, title, summary, dimension,
                impact_direction, impact_strength, published_at, ingested_at)
               VALUES (:id, :connector_id, :provider_id, :title, :summary,
                       :dimension, :impact_direction, :impact_strength,
                       :published_at, :ingested_at)""",
            events,
        )
        conn.commit()


def list_events(limit: int = 10) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, connector_id, provider_id, title, summary, dimension,
                      impact_direction, impact_strength, published_at, ingested_at
               FROM source_event
               ORDER BY ingested_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_events_by_connector(connector_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM source_event WHERE connector_id = ?", (connector_id,))
        conn.commit()
