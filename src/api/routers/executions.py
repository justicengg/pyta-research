"""Execution log API endpoints."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.db.models import ExecutionLog

router = APIRouter()
SH_TZ = ZoneInfo('Asia/Shanghai')


class ManualExecution(BaseModel):
    card_id: int | None = None
    symbol: str
    market: str
    response: Literal['accepted', 'rejected', 'modified'] = 'accepted'
    reason: str | None = None
    source: Literal['manual_override', 'external_trade']
    executed_price: float | None = None
    executed_quantity: float | None = None
    executed_at: datetime | None = None


def _to_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SH_TZ).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def _row_to_dict(row: ExecutionLog) -> dict:
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


@router.get('/executions', dependencies=[Depends(verify_api_key)])
def list_executions(
    card_id: int | None = Query(None),
    source: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[dict]:
    stmt = select(ExecutionLog).order_by(ExecutionLog.created_at.desc(), ExecutionLog.id.desc())
    if card_id is not None:
        stmt = stmt.where(ExecutionLog.card_id == card_id)
    if source is not None:
        stmt = stmt.where(ExecutionLog.source == source)
    if date_from is not None:
        stmt = stmt.where(func.date(ExecutionLog.created_at) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(ExecutionLog.created_at) <= date_to)
    stmt = stmt.limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_row_to_dict(row) for row in rows]


@router.post('/executions', dependencies=[Depends(verify_api_key)])
def create_execution(body: ManualExecution, session: Session = Depends(get_session)) -> dict:
    row = ExecutionLog(
        action_queue_id=None,
        card_id=body.card_id,
        symbol=body.symbol,
        market=body.market,
        response=body.response,
        reason=body.reason,
        source=body.source,
        executed_price=body.executed_price,
        executed_quantity=body.executed_quantity,
        executed_at=_to_utc(body.executed_at),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _row_to_dict(row)


@router.get('/executions/{execution_id}', dependencies=[Depends(verify_api_key)])
def get_execution(execution_id: int, session: Session = Depends(get_session)) -> dict:
    row = session.get(ExecutionLog, execution_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Execution {execution_id} not found')
    return _row_to_dict(row)
