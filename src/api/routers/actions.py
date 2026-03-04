"""Action queue API endpoints."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_session, verify_api_key
from src.db.models import ActionQueue, ExecutionLog

router = APIRouter()


class ActionResponse(BaseModel):
    response: Literal['accepted', 'rejected', 'modified']
    reason: str | None = None
    modified_action: str | None = None
    executed_price: float | None = None
    executed_quantity: float | None = None

    @model_validator(mode='after')
    def validate_modified_payload(self):
        if self.response == 'modified' and not self.modified_action:
            raise ValueError('modified_action is required when response=modified')
        return self


def _row_to_dict(row: ActionQueue) -> dict:
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


@router.get('/actions', dependencies=[Depends(verify_api_key)])
def list_actions(
    date_filter: date | None = Query(None, alias='date'),
    status_filter: str | None = Query(None, alias='status'),
    priority: str | None = Query(None),
    session: Session = Depends(get_session),
) -> list[dict]:
    stmt = select(ActionQueue).order_by(ActionQueue.generated_date.desc(), ActionQueue.id.desc())
    if date_filter is not None:
        stmt = stmt.where(ActionQueue.generated_date == date_filter)
    if status_filter is not None:
        stmt = stmt.where(ActionQueue.status == status_filter)
    if priority is not None:
        stmt = stmt.where(ActionQueue.priority == priority)
    rows = session.execute(stmt).scalars().all()
    return [_row_to_dict(row) for row in rows]


@router.get('/actions/today', dependencies=[Depends(verify_api_key)])
def list_actions_today(session: Session = Depends(get_session)) -> list[dict]:
    stmt = (
        select(ActionQueue)
        .where(ActionQueue.generated_date == date.today(), ActionQueue.status == 'pending')
        .order_by(ActionQueue.priority.asc(), ActionQueue.id.asc())
    )
    rows = session.execute(stmt).scalars().all()
    return [_row_to_dict(row) for row in rows]


@router.get('/actions/{action_id}', dependencies=[Depends(verify_api_key)])
def get_action(action_id: int, session: Session = Depends(get_session)) -> dict:
    row = session.get(ActionQueue, action_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Action {action_id} not found')
    return _row_to_dict(row)


@router.post('/actions/{action_id}/respond', dependencies=[Depends(verify_api_key)])
def respond_action(action_id: int, body: ActionResponse, session: Session = Depends(get_session)) -> dict:
    row = session.get(ActionQueue, action_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Action {action_id} not found')

    # Idempotent state machine: only pending actions can be responded to.
    if row.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Action {action_id} already responded with status={row.status}',
        )

    row.status = body.response
    row.updated_at = datetime.now(timezone.utc)
    if body.response == 'modified' and body.modified_action:
        row.action = body.modified_action

    session.add(
        ExecutionLog(
            action_queue_id=row.id,
            card_id=row.card_id,
            symbol=row.symbol,
            market=row.market,
            response=body.response,
            reason=body.reason,
            source='system_suggestion',
            executed_price=body.executed_price,
            executed_quantity=body.executed_quantity,
            executed_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.refresh(row)
    return _row_to_dict(row)
