from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import ActionQueue, ExecutionLog, StrategyCard
from src.db.session import configure_engine, get_session


def _enable_fk(session: Session) -> None:
    # SQLite disables FK actions by default; enable for ON DELETE tests.
    session.execute(text('PRAGMA foreign_keys=ON'))


def _create_card(session: Session, symbol: str = 'BABA', market: str = 'US') -> StrategyCard:
    card = StrategyCard(symbol=symbol, market=market, status='active')
    session.add(card)
    session.flush()
    return card


def test_action_queue_insert_and_query(migrated_db: str):
    configure_engine(migrated_db)
    with get_session() as session:
        _enable_fk(session)
        card = _create_card(session)
        item = ActionQueue(
            card_id=card.id,
            symbol='BABA',
            market='US',
            action='hold',
            priority='normal',
            status='pending',
            generated_date=date(2026, 3, 5),
            rule_tag='review_due',
            reason='monthly review due',
        )
        session.add(item)
        session.flush()

        row = session.get(ActionQueue, item.id)
        assert row is not None
        assert row.symbol == 'BABA'
        assert row.action == 'hold'


def test_action_queue_business_unique_key(migrated_db: str):
    configure_engine(migrated_db)
    with get_session() as session:
        _enable_fk(session)
        card = _create_card(session, symbol='TSLA')
        first = ActionQueue(
            card_id=card.id,
            symbol='TSLA',
            market='US',
            action='trim',
            priority='urgent',
            status='pending',
            generated_date=date(2026, 3, 5),
            rule_tag='concentration_breach',
        )
        session.add(first)
        session.flush()

        dup = ActionQueue(
            card_id=card.id,
            symbol='TSLA',
            market='US',
            action='trim',
            priority='urgent',
            status='pending',
            generated_date=date(2026, 3, 5),
            rule_tag='concentration_breach',
        )
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_execution_log_action_queue_fk_set_null_on_delete(migrated_db: str):
    configure_engine(migrated_db)
    with get_session() as session:
        _enable_fk(session)
        card = _create_card(session, symbol='AAPL')
        aq = ActionQueue(
            card_id=card.id,
            symbol='AAPL',
            market='US',
            action='enter',
            priority='normal',
            status='pending',
            generated_date=date(2026, 3, 5),
            rule_tag='entry_signal',
        )
        session.add(aq)
        session.flush()

        log = ExecutionLog(
            action_queue_id=aq.id,
            card_id=card.id,
            symbol='AAPL',
            market='US',
            response='accepted',
            source='system_suggestion',
        )
        session.add(log)
        session.flush()

        session.delete(aq)
        session.flush()
        session.refresh(log)
        assert log.action_queue_id is None


def test_execution_log_insert_manual_override(migrated_db: str):
    configure_engine(migrated_db)
    with get_session() as session:
        _enable_fk(session)
        card = _create_card(session, symbol='MSFT')
        log = ExecutionLog(
            action_queue_id=None,
            card_id=card.id,
            symbol='MSFT',
            market='US',
            response='modified',
            reason='adjusted order size',
            source='manual_override',
            executed_price=380.12,
            executed_quantity=5.0,
        )
        session.add(log)
        session.flush()
        assert log.id > 0
