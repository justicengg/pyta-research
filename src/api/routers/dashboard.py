"""GET /dashboard — Jinja2 HTML decision dashboard (no auth required).

The page is served as plain HTML; JavaScript in the page calls the
/api/v1/... JSON endpoints using the API key injected via <meta> tag.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config.settings import settings

_TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


@router.get('/dashboard', response_class=HTMLResponse, tags=['dashboard'])
def dashboard(request: Request) -> HTMLResponse:
    """Render the decision dashboard HTML page."""
    return _templates.TemplateResponse(
        request,
        'dashboard.html',
        {'api_key': settings.api_key},
    )
