"""FastAPI shared dependencies.

get_session  — yields a SQLAlchemy Session for the request lifetime.
verify_api_key — enforces X-API-Key header when settings.api_key is configured.
"""
from __future__ import annotations

from typing import Generator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_session as _get_db_session

# ── database ──────────────────────────────────────────────────────────────────

def get_session() -> Generator[Session, None, None]:
    """Yield a transactional SQLAlchemy session, auto-closed after the request."""
    with _get_db_session() as session:
        yield session


# ── authentication ────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Raise HTTP 401 if the request carries an invalid API key.

    When ``settings.api_key`` is empty (default) the check is **skipped**,
    which makes local development seamless without requiring any header.
    """
    if not settings.api_key:
        return  # auth disabled
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or missing API key',
            headers={'WWW-Authenticate': 'ApiKey'},
        )
