from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from src.db.base import Base
from src.db.models import ActionQueue, StrategyCard
from src.decision.advisor import DecisionAdvisor

ASOF = date(2026, 3, 10)


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        with s.begin():
            yield s


def _add_trade(s: Session, symbol: str, market: str, direction: str, price: float, shares: float) -> None:
    s.execute(text(
        "INSERT INTO trade_log "
        "(symbol, market, direction, price, shares, amount, trade_date, created_at) "
        "VALUES (:sym, :mkt, :dir, :price, :shares, :amt, :td, :ca)"
    ), {
        'sym': symbol, 'mkt': market, 'dir': direction,
        'price': price, 'shares': shares, 'amt': price * shares,
        'td': ASOF.isoformat(), 'ca': datetime.now(timezone.utc).isoformat(),
    })


def _add_price(s: Session, symbol: str, market: str, close: float, source: str = 'baostock') -> None:
    s.execute(text(
        "INSERT INTO raw_price "
        "(symbol, market, trade_date, close, source, ingested_at) "
        "VALUES (:sym, :mkt, :td, :close, :src, :ia)"
    ), {
        'sym': symbol, 'mkt': market, 'td': ASOF.isoformat(),
        'close': close, 'src': source, 'ia': datetime.now(timezone.utc).isoformat(),
    })


def _add_card(
    s: Session,
    symbol: str,
    market: str = 'CN',
    status: str = 'active',
    stop_loss_price: float | None = None,
    entry_price: float | None = None,
    review_cadence: str | None = None,
    updated_days_ago: int = 0,
    exit_rules: dict | None = None,
    entry_rules: dict | None = None,
    valuation_anchor: dict | None = None,
) -> int:
    card = StrategyCard(
        symbol=symbol,
        market=market,
        status=status,
        stop_loss_price=stop_loss_price,
        entry_price=entry_price,
        review_cadence=review_cadence,
        exit_rules=exit_rules,
        entry_rules=entry_rules,
        valuation_anchor=valuation_anchor,
        created_at=datetime.now(timezone.utc) - timedelta(days=updated_days_ago),
        updated_at=datetime.now(timezone.utc) - timedelta(days=updated_days_ago),
    )
    s.add(card)
    s.flush()
    return card.id


def _queue_rows(s: Session) -> list[ActionQueue]:
    return list(s.scalars(select(ActionQueue).order_by(ActionQueue.id.asc())).all())


def test_r6_review_due_triggers_review(session: Session):
    _add_card(session, 'AAA', status='active', review_cadence='monthly', updated_days_ago=40)
    total = DecisionAdvisor().generate_queue(asof=ASOF, session=session)
    assert total == 1
    row = _queue_rows(session)[0]
    assert row.action == 'review'
    assert row.rule_tag == 'review_due'


def test_r1b_thesis_break_triggers_exit(session: Session):
    _add_trade(session, 'BBB', 'CN', 'buy', 10.0, 100)
    _add_price(session, 'BBB', 'CN', 10.5)
    _add_card(
        session,
        'BBB',
        status='active',
        exit_rules={'thesis_break': 'always_true'},
    )
    DecisionAdvisor().generate_queue(asof=ASOF, session=session, max_position_pct=1.0)
    row = _queue_rows(session)[0]
    assert row.action == 'exit'
    assert row.rule_tag == 'thesis_break'


def test_r2b_take_profit_default_trim(session: Session):
    _add_trade(session, 'CCC', 'CN', 'buy', 10.0, 100)
    _add_price(session, 'CCC', 'CN', 13.0)
    _add_card(
        session,
        'CCC',
        status='active',
        exit_rules={'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.2}},
    )
    DecisionAdvisor().generate_queue(asof=ASOF, session=session, max_position_pct=1.0)
    row = _queue_rows(session)[0]
    assert row.action == 'trim'
    assert row.rule_tag == 'take_profit_hit'


def test_r2b_take_profit_mode_exit(session: Session):
    _add_trade(session, 'CCD', 'CN', 'buy', 10.0, 100)
    _add_price(session, 'CCD', 'CN', 13.0)
    _add_card(
        session,
        'CCD',
        status='active',
        exit_rules={'take_profit': {'metric': 'unrealized_pnl_pct', 'threshold': 0.2, 'mode': 'exit'}},
    )
    DecisionAdvisor().generate_queue(asof=ASOF, session=session, max_position_pct=1.0)
    row = _queue_rows(session)[0]
    assert row.action == 'exit'
    assert row.rule_tag == 'take_profit_hit'


def test_r4b_entry_signal_triggers_enter(session: Session):
    _add_card(
        session,
        'DDD',
        status='active',
        entry_price=8.0,
        valuation_anchor={'core_metric': 'price', 'fair_low': 10.0, 'fair_high': 15.0},
        entry_rules={'trigger_conditions': ['valuation_below_fair_low'], 'filter_conditions': ['always_true']},
    )
    DecisionAdvisor().generate_queue(asof=ASOF, session=session)
    row = _queue_rows(session)[0]
    assert row.action == 'enter'
    assert row.rule_tag == 'entry_signal'


def test_generate_queue_expires_previous_pending(session: Session):
    old = ActionQueue(
        card_id=None,
        symbol='OLD',
        market='CN',
        action='hold',
        priority='normal',
        reason='old',
        rule_tag='within_limits',
        status='pending',
        generated_date=ASOF - timedelta(days=1),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(old)
    _add_card(session, 'EEE', status='draft')
    DecisionAdvisor().generate_queue(asof=ASOF, session=session)
    session.refresh(old)
    assert old.status == 'expired'


def test_generate_queue_idempotent_same_asof(session: Session):
    _add_card(session, 'FFF', status='draft')
    advisor = DecisionAdvisor()
    n1 = advisor.generate_queue(asof=ASOF, session=session)
    rows_after_first = len(_queue_rows(session))
    n2 = advisor.generate_queue(asof=ASOF, session=session)
    rows_after_second = len(_queue_rows(session))
    assert n1 == 1
    assert n2 == 1
    assert rows_after_first == rows_after_second == 1


def test_priority_resolution_r1_over_r2(session: Session):
    # Make GGG concentration-heavy and also thesis-break true.
    _add_trade(session, 'GGG', 'CN', 'buy', 10.0, 800)
    _add_trade(session, 'HHH', 'CN', 'buy', 10.0, 200)
    _add_price(session, 'GGG', 'CN', 10.0)
    _add_price(session, 'HHH', 'CN', 10.0)
    _add_card(session, 'GGG', status='active', exit_rules={'thesis_break': 'always_true'})
    DecisionAdvisor().generate_queue(asof=ASOF, session=session, max_position_pct=0.2)
    g_row = next(r for r in _queue_rows(session) if r.symbol == 'GGG')
    assert g_row.action == 'exit'
    assert g_row.rule_tag == 'thesis_break'


def test_missing_metric_fallback_to_card_active(session: Session):
    _add_card(
        session,
        'III',
        status='active',
        valuation_anchor={'core_metric': 'unknown_metric', 'fair_low': 1, 'fair_high': 2},
        entry_rules={'trigger_conditions': ['valuation_below_fair_low'], 'filter_conditions': ['always_true']},
    )
    DecisionAdvisor().generate_queue(asof=ASOF, session=session)
    row = _queue_rows(session)[0]
    assert row.action == 'enter'
    assert row.rule_tag == 'card_active'


def test_evaluate_backward_compatibility_still_no_review_action(session: Session):
    _add_card(session, 'JJJ', status='active', review_cadence='weekly', updated_days_ago=10)
    report = DecisionAdvisor().evaluate(asof=ASOF, session=session)
    assert all(a.action in {'exit', 'trim', 'hold', 'enter', 'watch'} for a in report.advice)
