"""Strategy card CRUD endpoints.

GET  /api/v1/cards          — list cards (optional ?status= filter)
GET  /api/v1/cards/{id}     — single card (404 if not found)
PATCH /api/v1/cards/{id}    — update mutable fields (JSON fields replace as a whole)
GET  /api/v1/cards/{id}/history — action/execution history with pagination
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.db.models import ActionQueue, ExecutionLog, StrategyCard
from src.strategy.schemas import (
    EntryRules,
    ExitRules,
    ExpectedCycle,
    PositionRules,
    ReviewCadence,
    RiskRules,
    ValuationAnchor,
)
from src.strategy.templates import apply_overrides, get_template, list_templates

router = APIRouter()


# ── request / response helpers ────────────────────────────────────────────────

class CardPatch(BaseModel):
    """Fields that can be updated via PATCH. All fields are optional.

    JSON fields use replace semantics: if provided, the whole JSON object is
    replaced. Merge-patch is not supported.
    """
    status: Optional[str] = None          # draft | active | paused | closed
    close_reason: Optional[str] = None
    thesis: Optional[str] = None
    position_pct: Optional[float] = None
    industry: Optional[str] = None
    expected_cycle: Optional[ExpectedCycle] = None
    valuation_anchor: Optional[ValuationAnchor] = None
    position_rules: Optional[PositionRules] = None
    entry_rules: Optional[EntryRules] = None
    exit_rules: Optional[ExitRules] = None
    risk_rules: Optional[RiskRules] = None
    review_cadence: Optional[ReviewCadence] = None


_STATUS_TRANSITIONS: dict[str, set[str]] = {
    'draft': {'active', 'closed'},
    'active': {'paused', 'closed'},
    'paused': {'active', 'closed'},
    'closed': {'active'},  # explicit reopen
}


def _normalize_patch_value(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Enum):
        return value.value
    return value


def _ensure_status_transition(current: str, nxt: str) -> None:
    if current == nxt:
        return
    allowed = _STATUS_TRANSITIONS.get(current, set())
    if nxt not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Illegal status transition: {current} -> {nxt}',
        )


def _card_to_dict(card: StrategyCard) -> dict:
    return {
        'id': card.id,
        'symbol': card.symbol,
        'market': card.market,
        'status': card.status,
        'thesis': card.thesis,
        'position_pct': float(card.position_pct) if card.position_pct is not None else None,
        'valuation_note': card.valuation_note,
        'entry_price': float(card.entry_price) if card.entry_price is not None else None,
        'entry_date': card.entry_date.isoformat() if card.entry_date is not None else None,
        'stop_loss_price': float(card.stop_loss_price) if card.stop_loss_price is not None else None,
        'industry': card.industry,
        'expected_cycle': card.expected_cycle,
        'valuation_anchor': card.valuation_anchor,
        'position_rules': card.position_rules,
        'entry_rules': card.entry_rules,
        'exit_rules': card.exit_rules,
        'risk_rules': card.risk_rules,
        'review_cadence': card.review_cadence,
        'rules_version': card.rules_version,
        'close_reason': card.close_reason,
        'created_at': card.created_at.isoformat() if card.created_at is not None else None,
        'updated_at': card.updated_at.isoformat() if card.updated_at is not None else None,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

class CardFromTemplate(BaseModel):
    template: str
    symbol: str
    market: str
    overrides: Optional[dict] = None


@router.get('/cards/templates', dependencies=[Depends(verify_api_key)])
def get_templates() -> list[dict]:
    """Return available strategy card templates."""
    return list_templates()


@router.post('/cards/from-template', dependencies=[Depends(verify_api_key)])
def create_from_template(
    body: CardFromTemplate,
    session: Session = Depends(get_session),
) -> dict:
    """Create a strategy card from a template with optional overrides."""
    try:
        tpl = get_template(body.template)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if body.overrides:
        tpl = apply_overrides(tpl, body.overrides)

    # Validate JSONB fields via Pydantic schemas
    try:
        if tpl.get('position_rules'):
            PositionRules(**tpl['position_rules'])
        if tpl.get('entry_rules'):
            EntryRules(**tpl['entry_rules'])
        if tpl.get('exit_rules'):
            ExitRules(**{k: v for k, v in tpl['exit_rules'].items() if v is not None})
        if tpl.get('risk_rules'):
            RiskRules(**tpl['risk_rules'])
        if tpl.get('valuation_anchor'):
            ValuationAnchor(**tpl['valuation_anchor'])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'Rule validation failed: {e}',
        )

    card = StrategyCard(
        symbol=body.symbol,
        market=body.market,
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
    return _card_to_dict(card)


@router.get('/cards', dependencies=[Depends(verify_api_key)])
def list_cards(
    status: Optional[str] = Query(None, description='Filter by status: draft | active | paused | closed'),
    session: Session = Depends(get_session),
) -> list:
    """Return all strategy cards, optionally filtered by status."""
    query = select(StrategyCard).order_by(StrategyCard.created_at.desc())
    if status:
        query = query.where(StrategyCard.status == status)
    cards = session.execute(query).scalars().all()
    return [_card_to_dict(c) for c in cards]


@router.get('/cards/{card_id}', dependencies=[Depends(verify_api_key)])
def get_card(card_id: int, session: Session = Depends(get_session)) -> dict:
    """Return a single strategy card by ID."""
    card = session.get(StrategyCard, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Card {card_id} not found')
    return _card_to_dict(card)


@router.patch('/cards/{card_id}', dependencies=[Depends(verify_api_key)])
def patch_card(
    card_id: int,
    body: CardPatch,
    session: Session = Depends(get_session),
) -> dict:
    """Update mutable fields on a strategy card.

    JSON fields in PATCH body are replaced as a whole object and do not support
    merge-patch semantics.
    """
    card = session.get(StrategyCard, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Card {card_id} not found')
    updates = body.model_dump(exclude_none=True)
    if 'status' in updates:
        _ensure_status_transition(card.status, updates['status'])
    for field, value in updates.items():
        setattr(card, field, _normalize_patch_value(value))
    session.commit()
    session.refresh(card)
    return _card_to_dict(card)


def _history_action_to_dict(row: ActionQueue) -> dict:
    return {
        'id': row.id,
        'card_id': row.card_id,
        'symbol': row.symbol,
        'market': row.market,
        'action': row.action,
        'priority': row.priority,
        'reason': row.reason,
        'rule_tag': row.rule_tag,
        'status': row.status,
        'generated_date': row.generated_date.isoformat() if row.generated_date is not None else None,
        'expires_at': row.expires_at.isoformat() if row.expires_at is not None else None,
        'created_at': row.created_at.isoformat() if row.created_at is not None else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at is not None else None,
    }


def _history_execution_to_dict(row: ExecutionLog) -> dict:
    return {
        'id': row.id,
        'action_queue_id': row.action_queue_id,
        'card_id': row.card_id,
        'symbol': row.symbol,
        'market': row.market,
        'response': row.response,
        'reason': row.reason,
        'source': row.source,
        'executed_price': float(row.executed_price) if row.executed_price is not None else None,
        'executed_quantity': float(row.executed_quantity) if row.executed_quantity is not None else None,
        'executed_at': row.executed_at.isoformat() if row.executed_at is not None else None,
        'created_at': row.created_at.isoformat() if row.created_at is not None else None,
    }


def _apply_date_filters(
    stmt: Select,
    date_expr,
    start_date: date | None,
    end_date: date | None,
) -> Select:
    if start_date is not None:
        stmt = stmt.where(date_expr >= start_date)
    if end_date is not None:
        stmt = stmt.where(date_expr <= end_date)
    return stmt


@router.get('/cards/{card_id}/history', dependencies=[Depends(verify_api_key)])
def get_card_history(
    card_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """Return action_queue and execution_log history for a card with pagination."""
    card = session.get(StrategyCard, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Card {card_id} not found')

    offset = (page - 1) * page_size

    aq_stmt = select(ActionQueue).where(ActionQueue.card_id == card_id)
    aq_stmt = _apply_date_filters(aq_stmt, ActionQueue.generated_date, start_date, end_date)
    aq_total_stmt = select(func.count()).select_from(aq_stmt.subquery())
    aq_rows = session.execute(
        aq_stmt.order_by(ActionQueue.generated_date.desc(), ActionQueue.id.desc()).offset(offset).limit(page_size)
    ).scalars().all()

    ex_stmt = select(ExecutionLog).where(ExecutionLog.card_id == card_id)
    ex_stmt = _apply_date_filters(ex_stmt, func.date(ExecutionLog.created_at), start_date, end_date)
    ex_total_stmt = select(func.count()).select_from(ex_stmt.subquery())
    ex_rows = session.execute(
        ex_stmt.order_by(ExecutionLog.created_at.desc(), ExecutionLog.id.desc()).offset(offset).limit(page_size)
    ).scalars().all()

    return {
        'card_id': card_id,
        'page': page,
        'page_size': page_size,
        'start_date': start_date.isoformat() if start_date is not None else None,
        'end_date': end_date.isoformat() if end_date is not None else None,
        'action_queue': {
            'total': session.scalar(aq_total_stmt) or 0,
            'items': [_history_action_to_dict(row) for row in aq_rows],
        },
        'execution_log': {
            'total': session.scalar(ex_total_stmt) or 0,
            'items': [_history_execution_to_dict(row) for row in ex_rows],
        },
    }
