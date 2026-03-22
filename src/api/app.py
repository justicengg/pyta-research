"""FastAPI application factory — PYTA Research API.

Architecture
------------
Single process:
  • REST API   → /api/v1/...    (JSON, X-API-Key auth)
  • Health     → /health        (JSON, always open)
  • OpenAPI    → /docs /redoc
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI

from src.api.deps import verify_api_key
from src.config.settings import settings


# ── lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Optionally start a BackgroundScheduler; always shut down cleanly.

    BackgroundScheduler runs jobs in a daemon thread — safe to use alongside
    an asyncio-based server such as uvicorn.
    """
    yield


# ── app factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title='PYTA Research API',
        description='Secondary market multi-agent sandbox.',
        version='0.1.0',
        lifespan=lifespan,
    )

    # ── /health — always open, used by load-balancers / uptime monitors ───────
    @app.get('/health', tags=['system'])
    def health() -> dict:
        return {'status': 'ok', 'version': app.version}

    # ── /api/v1/ping — auth-gated smoke-test ──────────────────────────────────
    @app.get('/api/v1/ping', tags=['system'], dependencies=[Depends(verify_api_key)])
    def ping() -> dict:
        return {'pong': True}

    # ── business routers ──────────────────────────────────────────────────────
    from src.api.routers import sandbox
    app.include_router(sandbox.router, prefix='/api/v1', tags=['sandbox'])

    return app


# ── module-level instance (target for uvicorn: "src.api.app:app") ─────────────
app = create_app()
