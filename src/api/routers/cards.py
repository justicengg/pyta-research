"""Strategy card CRUD endpoints.

GET  /api/v1/cards          — list cards (optional ?status= filter)
GET  /api/v1/cards/{id}     — single card (404 if not found)
PATCH /api/v1/cards/{id}    — update mutable fields
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.db.models import StrategyCard

router = APIRouter()


# ── request / response helpers ────────────────────────────────────────────────

class CardPatch(BaseModel):
    """Fields that can be updated via PATCH.  All are optional."""
    status: Optional[str] = None          # draft | active | closed
    close_reason: Optional[str] = None
    thesis: Optional[str] = None
    position_pct: Optional[float] = None


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
        'close_reason': card.close_reason,
        'created_at': card.created_at.isoformat() if card.created_at is not None else None,
        'updated_at': card.updated_at.isoformat() if card.updated_at is not None else None,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get('/cards', dependencies=[Depends(verify_api_key)])
def list_cards(
    status: Optional[str] = Query(None, description='Filter by status: draft | active | closed'),
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
    """Update mutable fields on a strategy card (status, close_reason, thesis, position_pct)."""
    card = session.get(StrategyCard, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Card {card_id} not found')
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(card, field, value)
    session.commit()
    session.refresh(card)
    return _card_to_dict(card)
