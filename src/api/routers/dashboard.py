"""Dashboard routes with server-side data rendering and secure write proxies."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import func, select

from src.config.settings import settings
from src.db.models import ActionQueue, ExecutionLog, RawPrice, StrategyCard, TradeLog
from src.db.session import get_session
from src.decision.advisor import DecisionAdvisor
from src.portfolio.tracker import PortfolioTracker
from src.risk.checker import RiskChecker

_TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()

SESSION_COOKIE = 'dashboard_session'
CSRF_COOKIE = 'dashboard_csrf'


class DashboardLogin(BaseModel):
    token: str


class DashboardRespond(BaseModel):
    action_id: int
    response: str
    reason: str | None = None
    modified_action: str | None = None
    executed_price: float | None = None
    executed_quantity: float | None = None
    request_id: str | None = None


class DashboardManualExecution(BaseModel):
    card_id: int | None = None
    symbol: str
    market: str
    response: str = 'accepted'
    reason: str | None = None
    source: str
    executed_price: float | None = None
    executed_quantity: float | None = None
    executed_at: datetime | None = None
    request_id: str | None = None


def _json_payload(obj: object) -> str:
    return json.dumps(obj, default=str)


def _session_hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _build_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _is_logged_in(request: Request) -> bool:
    if not settings.dashboard_write_token:
        return False
    expected = _session_hash(settings.dashboard_write_token)
    got = request.cookies.get(SESSION_COOKIE, '')
    return hmac.compare_digest(expected, got)


def _verify_same_origin(request: Request) -> None:
    host = request.headers.get('host', '')
    origin = request.headers.get('origin')
    referer = request.headers.get('referer')
    if origin:
        if urlparse(origin).netloc != host:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Origin mismatch')
        return
    if referer:
        if urlparse(referer).netloc != host:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Referer mismatch')
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Missing origin metadata')


def _require_write_auth(request: Request) -> None:
    if not _is_logged_in(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Dashboard write auth required')


def _require_csrf(request: Request) -> None:
    header_token = request.headers.get('X-CSRF-Token', '')
    cookie_token = request.cookies.get(CSRF_COOKIE, '')
    if not header_token or not cookie_token or not hmac.compare_digest(header_token, cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='CSRF validation failed')


def _audit_reason(base_reason: str | None, operator: str, request_id: str | None, source_ip: str | None) -> str:
    rid = request_id or '-'
    ip = source_ip or '-'
    body = base_reason or ''
    return f'[op={operator}][req={rid}][ip={ip}] {body}'.strip()


@router.get('/dashboard', response_class=HTMLResponse, tags=['dashboard'])
def dashboard(request: Request) -> HTMLResponse:
    asof = date.today()
    with get_session() as session:
        portfolio = PortfolioTracker().snapshot(
            asof=asof,
            session=session,
            price_source_cn=settings.price_source_cn,
            price_source_us=settings.price_source_us,
        )
        risk = RiskChecker().check(
            portfolio=portfolio,
            max_position_pct=settings.risk_max_position_pct,
            max_positions=settings.risk_max_positions,
            max_drawdown_pct=settings.risk_max_drawdown_pct,
        )
        decision = DecisionAdvisor().evaluate(
            asof=asof,
            session=session,
            price_source_cn=settings.price_source_cn,
            price_source_us=settings.price_source_us,
            max_position_pct=settings.risk_max_position_pct,
            max_positions=settings.risk_max_positions,
            max_drawdown_pct=settings.risk_max_drawdown_pct,
        )

        pending_actions_rows = list(session.scalars(
            select(ActionQueue)
            .where(ActionQueue.status == 'pending')
            .order_by(ActionQueue.generated_date.desc(), ActionQueue.id.desc())
            .limit(50)
        ).all())
        handled_actions_rows = list(session.scalars(
            select(ActionQueue)
            .where(ActionQueue.status.in_(['accepted', 'rejected', 'modified']))
            .order_by(ActionQueue.updated_at.desc(), ActionQueue.id.desc())
            .limit(50)
        ).all())
        cards_rows = list(session.scalars(
            select(StrategyCard).order_by(StrategyCard.updated_at.desc(), StrategyCard.id.desc()).limit(200)
        ).all())
        executions_rows = list(session.scalars(
            select(ExecutionLog)
            .where(func.date(ExecutionLog.created_at) >= (asof - timedelta(days=30)))
            .order_by(ExecutionLog.created_at.desc(), ExecutionLog.id.desc())
            .limit(200)
        ).all())

        pending_actions = [
            {
                'id': x.id,
                'card_id': x.card_id,
                'symbol': x.symbol,
                'market': x.market,
                'action': x.action,
                'priority': x.priority,
                'reason': x.reason,
                'rule_tag': x.rule_tag,
                'status': x.status,
                'generated_date': x.generated_date.isoformat() if x.generated_date else None,
            }
            for x in pending_actions_rows
        ]
        handled_actions = [
            {
                'id': x.id,
                'card_id': x.card_id,
                'symbol': x.symbol,
                'market': x.market,
                'action': x.action,
                'priority': x.priority,
                'reason': x.reason,
                'rule_tag': x.rule_tag,
                'status': x.status,
                'updated_at': x.updated_at.isoformat() if x.updated_at else None,
            }
            for x in handled_actions_rows
        ]
        cards = [
            {
                'id': x.id,
                'symbol': x.symbol,
                'market': x.market,
                'status': x.status,
                'thesis': x.thesis,
                'position_pct': float(x.position_pct) if x.position_pct is not None else None,
                'valuation_anchor': x.valuation_anchor,
                'position_rules': x.position_rules,
                'entry_rules': x.entry_rules,
                'exit_rules': x.exit_rules,
                'risk_rules': x.risk_rules,
                'review_cadence': x.review_cadence,
                'updated_at': x.updated_at.isoformat() if x.updated_at else None,
            }
            for x in cards_rows
        ]
        executions = [
            {
                'id': x.id,
                'action_queue_id': x.action_queue_id,
                'card_id': x.card_id,
                'symbol': x.symbol,
                'market': x.market,
                'response': x.response,
                'reason': x.reason,
                'source': x.source,
                'executed_price': float(x.executed_price) if x.executed_price is not None else None,
                'executed_quantity': float(x.executed_quantity) if x.executed_quantity is not None else None,
                'executed_at': x.executed_at.isoformat() if x.executed_at else None,
                'created_at': x.created_at.isoformat() if x.created_at else None,
            }
            for x in executions_rows
        ]

    csrf_token = _build_csrf_token()
    response = _templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'portfolio_json': _json_payload(asdict(portfolio)),
            'risk_json': _json_payload(asdict(risk)),
            'decision_json': _json_payload(asdict(decision)),
            'pending_actions_json': _json_payload(pending_actions),
            'handled_actions_json': _json_payload(handled_actions),
            'cards_json': _json_payload(cards),
            'executions_json': _json_payload(executions),
            'csrf_token': csrf_token,
            'write_enabled': _is_logged_in(request),
        },
    )
    _secure = request.url.scheme == 'https'
    response.set_cookie(CSRF_COOKIE, csrf_token, samesite='lax', httponly=False, secure=_secure)
    return response


@router.post('/dashboard/login', tags=['dashboard'])
async def dashboard_login(request: Request) -> JSONResponse:
    payload = DashboardLogin(**(await request.json()))
    if not settings.dashboard_write_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Dashboard write disabled')
    if not hmac.compare_digest(payload.token, settings.dashboard_write_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid dashboard token')

    csrf_token = _build_csrf_token()
    response = JSONResponse({'ok': True})
    _secure = request.url.scheme == 'https'
    response.set_cookie(SESSION_COOKIE, _session_hash(settings.dashboard_write_token), httponly=True, samesite='lax', secure=_secure, max_age=86400)
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, samesite='lax', secure=_secure)
    return response


@router.post('/dashboard/respond', tags=['dashboard'])
async def dashboard_respond(request: Request) -> JSONResponse:
    _require_write_auth(request)
    _verify_same_origin(request)
    _require_csrf(request)

    body = DashboardRespond(**(await request.json()))
    if body.response not in {'accepted', 'rejected', 'modified'}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid response')
    if body.response == 'modified' and not body.modified_action:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='modified_action required')

    now = datetime.now(timezone.utc)
    operator = 'dashboard'
    source_ip = request.client.host if request.client else None
    with get_session() as session:
        action = session.get(ActionQueue, body.action_id)
        if action is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Action {body.action_id} not found')
        if action.status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Action {body.action_id} already responded with status={action.status}',
            )

        action.status = body.response
        action.updated_at = now
        if body.response == 'modified' and body.modified_action:
            action.action = body.modified_action

        session.add(ExecutionLog(
            action_queue_id=action.id,
            card_id=action.card_id,
            symbol=action.symbol,
            market=action.market,
            response=body.response,
            reason=_audit_reason(body.reason, operator, body.request_id, source_ip),
            source='system_suggestion',
            executed_price=body.executed_price,
            executed_quantity=body.executed_quantity,
            executed_at=now,
        ))
        session.commit()
        session.refresh(action)
        final_status = action.status

    return JSONResponse({'ok': True, 'action_id': body.action_id, 'status': final_status})


@router.post('/dashboard/executions', tags=['dashboard'])
async def dashboard_executions(request: Request) -> JSONResponse:
    _require_write_auth(request)
    _verify_same_origin(request)
    _require_csrf(request)

    body = DashboardManualExecution(**(await request.json()))
    if body.source not in {'manual_override', 'external_trade'}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid source')

    operator = 'dashboard'
    source_ip = request.client.host if request.client else None
    executed_at = body.executed_at.astimezone(timezone.utc) if body.executed_at else datetime.now(timezone.utc)

    with get_session() as session:
        row = ExecutionLog(
            action_queue_id=None,
            card_id=body.card_id,
            symbol=body.symbol,
            market=body.market,
            response=body.response,
            reason=_audit_reason(body.reason, operator, body.request_id, source_ip),
            source=body.source,
            executed_price=body.executed_price,
            executed_quantity=body.executed_quantity,
            executed_at=executed_at,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        execution_id = row.id

    return JSONResponse({'ok': True, 'execution_id': execution_id})


SNAPSHOT_NOTE = 'initial_snapshot'


@router.post('/dashboard/portfolio-snapshot', tags=['dashboard'])
async def dashboard_portfolio_snapshot(request: Request) -> JSONResponse:
    """Import portfolio positions via dashboard (server-side proxy)."""
    _require_write_auth(request)
    _verify_same_origin(request)
    _require_csrf(request)

    body = await request.json()
    positions = body.get('positions', [])
    snapshot_date_str = body.get('snapshot_date')
    snap_date = date.fromisoformat(snapshot_date_str) if snapshot_date_str else date.today()

    if not positions:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='positions is required')

    with get_session() as session:
        # Idempotent: delete previous snapshot records
        from sqlalchemy import delete, distinct, select as sa_select
        session.execute(delete(TradeLog).where(TradeLog.note == SNAPSHOT_NOTE))

        # Check price coverage
        covered = set(
            session.execute(sa_select(distinct(RawPrice.symbol), RawPrice.market)).all()
        )
        warnings: list[str] = []
        inserted = 0

        for p in positions:
            symbol = p.get('symbol', '')
            market = p.get('market', '')
            shares = float(p.get('shares', 0))
            avg_cost = float(p.get('avg_cost', 0))
            if not symbol or not market or shares <= 0 or avg_cost <= 0:
                continue
            session.add(TradeLog(
                symbol=symbol,
                market=market,
                direction='buy',
                price=avg_cost,
                shares=shares,
                amount=round(avg_cost * shares, 6),
                trade_date=snap_date,
                note=SNAPSHOT_NOTE,
            ))
            inserted += 1
            if (symbol, market) not in covered:
                warnings.append(f'{symbol}({market}): no price data')

        session.commit()

    return JSONResponse({'ok': True, 'imported': inserted, 'warnings': warnings})


@router.post('/dashboard/cards/from-template', tags=['dashboard'])
async def dashboard_create_card_from_template(request: Request) -> JSONResponse:
    """Create a strategy card from template via dashboard (server-side proxy)."""
    _require_write_auth(request)
    _verify_same_origin(request)
    _require_csrf(request)

    body = await request.json()
    template_name = body.get('template', '')
    symbol = body.get('symbol', '')
    market = body.get('market', '')

    if not template_name or not symbol or not market:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='template, symbol, market required')

    from src.strategy.templates import apply_overrides, get_template

    try:
        tpl = get_template(template_name)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    overrides = body.get('overrides') or {}
    if overrides:
        tpl = apply_overrides(tpl, overrides)

    with get_session() as session:
        card = StrategyCard(
            symbol=symbol,
            market=market,
            status='active',
            expected_cycle=tpl.get('expected_cycle'),
            review_cadence=tpl.get('review_cadence'),
            position_rules=tpl.get('position_rules'),
            entry_rules=tpl.get('entry_rules'),
            exit_rules=tpl.get('exit_rules'),
            risk_rules=tpl.get('risk_rules'),
            valuation_anchor=tpl.get('valuation_anchor'),
            rules_version=1,
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        card_id = card.id

    return JSONResponse({'ok': True, 'card_id': card_id})
