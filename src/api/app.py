"""FastAPI application factory — PYTA Research API.

Architecture
------------
Single process:
  • REST API   → /api/v1/...    (JSON, X-API-Key auth)
  • Dashboard  → /dashboard     (HTML)
  • Health     → /health        (JSON, always open)
  • OpenAPI    → /docs /redoc

Embedded APScheduler is optional and disabled by default
(`settings.api_enable_embedded_scheduler = False`). In production, prefer
running scheduler as a dedicated process via `python -m src.cli scheduler start`
to avoid duplicate jobs in multi-worker/multi-instance API deployments.
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
    """Optionally start a BackgroundScheduler; always shut down cleanly.

    BackgroundScheduler runs jobs in a daemon thread — safe to use alongside
    an asyncio-based server such as uvicorn.
    """
    if not settings.api_enable_embedded_scheduler:
        yield
        return

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

    # ── business routers ──────────────────────────────────────────────────────
    from src.api.routers import cards, decision, portfolio, risk
    app.include_router(portfolio.router, prefix='/api/v1', tags=['portfolio'])
    app.include_router(risk.router,      prefix='/api/v1', tags=['risk'])
    app.include_router(decision.router,  prefix='/api/v1', tags=['decision'])
    app.include_router(cards.router,     prefix='/api/v1', tags=['cards'])

    # ── dashboard router ──────────────────────────────────────────────────────
    from src.api.routers import dashboard
    app.include_router(dashboard.router, tags=['dashboard'])

    return app


# ── module-level instance (target for uvicorn: "src.api.app:app") ─────────────
app = create_app()
