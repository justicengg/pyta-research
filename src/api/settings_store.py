"""Simple key-value settings store backed by SQLite.

Stores user-configurable settings (e.g. LLM API key) in the same SQLite DB
as the rest of the system. The API key is never returned to the frontend —
only a boolean `configured` status is exposed.

NOTE: For production multi-user deployments, encrypt the value column with
Fernet (cryptography library) before storing.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path("pyta.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def get(key: str) -> str | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM user_settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None


def put(key: str, value: str) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO user_settings (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (key, value),
        )
        conn.commit()
