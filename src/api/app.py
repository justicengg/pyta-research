"""FastAPI application factory — PYTA Research API.

Architecture
------------
Single process:
  • REST API   → /api/v1/...    (JSON, X-API-Key auth)
  • Dashboard  → /dashboard     (HTML, no auth — INV-47)
  • Health     → /health        (JSON, always open)
  • OpenAPI    → /docs /redoc

APScheduler (BackgroundScheduler) starts inside the lifespan context so the
daily pipeline runs automatically inside the same process.  BackgroundScheduler
runs jobs in a daemon thread — it does NOT block the asyncio event loop, which
makes it safe to embed in uvicorn / FastAPI.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI

from src.api.deps import verify_api_key
from src.config.settings import settings
from src.scheduler.scheduler import PipelineScheduler


# ── lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start a BackgroundScheduler on boot; shut it down cleanly on exit.

    BackgroundScheduler runs jobs in a daemon thread — safe to use alongside
    an asyncio-based server such as uvicorn.
    """
    pipeline = PipelineScheduler()
    bg = BackgroundScheduler(timezone=settings.scheduler_timezone)
    trigger = CronTrigger(
        hour=settings.scheduler_cron_hour,
        minute=settings.scheduler_cron_minute,
    )
    bg.add_job(pipeline.run_once, trigger=trigger, id='daily_pipeline', replace_existing=True)
    bg.start()
    try:
        yield
    finally:
        if bg.running:
            bg.shutdown(wait=False)


# ── app factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title='PYTA Research API',
        description=(
            'Investment data pipeline — portfolio snapshot, risk check, '
            'decision evaluation, strategy cards.'
        ),
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

    # ── business routers (added in INV-46) ────────────────────────────────────
    # from src.api.routers import portfolio, risk, decision, cards
    # app.include_router(portfolio.router, prefix='/api/v1', tags=['portfolio'])
    # app.include_router(risk.router,      prefix='/api/v1', tags=['risk'])
    # app.include_router(decision.router,  prefix='/api/v1', tags=['decision'])
    # app.include_router(cards.router,     prefix='/api/v1', tags=['cards'])

    # ── dashboard router (added in INV-47) ────────────────────────────────────
    # from src.api.routers import dashboard
    # app.include_router(dashboard.router, tags=['dashboard'])

    return app


# ── module-level instance (target for uvicorn: "src.api.app:app") ─────────────
app = create_app()
