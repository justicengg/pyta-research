"""Unit tests for src/decision/advisor.py — DecisionAdvisor.

Test matrix
-----------
TestDecisionAdvisorEmpty        — no trades, no cards → empty advice
TestHoldRule                    — R3 default hold for open position
TestExitRule                    — R1 stop_loss_hit → exit
TestTrimRule                    — R2 concentration_breach → trim
TestStopLossPriorityOverTrim    — R1 > R2: exit wins when both apply
TestCardRules                   — R4 enter (active card) / R5 watch (draft card)
TestCardWithPosition            — card + matching position: position rule governs
TestClosedCardIgnored           — closed cards not included in advice
TestActiveBeforeDraft           — when same symbol has both, active card preferred
TestRiskPropagation             — risk_status / risk_violations forwarded correctly
TestCountAggregation            — action counts tallied correctly
TestDecisionReportJson          — report_to_json round-trip
"""
from __future__ import annotations

import json
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.db.base import Base
from src.decision.advisor import DecisionAdvisor
from src.decision.report import report_to_json

ASOF = date(2026, 3, 1)
ADVISOR = DecisionAdvisor()

# ── session fixture ───────────────────────────────────────────────────────────

@pytest.fixture
def session():
    """In-memory SQLite with full ORM schema."""
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        with s.begin():
            yield s


# ── helpers ───────────────────────────────────────────────────────────────────

def _add_trade(s: Session, symbol: str, market: str, direction: str,
               price: float, shares: float, trade_date: date = ASOF) -> None:
    s.execute(text(
        "INSERT INTO trade_log "
        "(symbol, market, direction, price, shares, amount, trade_date, created_at) "
        "VALUES (:sym, :mkt, :dir, :price, :shares, :amt, :td, :ca)"
    ), {
        'sym': symbol, 'mkt': market, 'dir': direction,
        'price': price, 'shares': shares, 'amt': price * shares,
        'td': trade_date.isoformat(), 'ca': '2026-03-01T00:00:00+00:00',
    })


def _add_price(s: Session, symbol: str, market: str, close: float,
               source: str = 'baostock', trade_date: date = ASOF) -> None:
    s.execute(text(
        "INSERT INTO raw_price "
        "(symbol, market, trade_date, close, source, ingested_at) "
        "VALUES (:sym, :mkt, :td, :close, :src, :ia)"
    ), {
        'sym': symbol, 'mkt': market, 'td': trade_date.isoformat(),
        'close': close, 'src': source, 'ia': datetime.utcnow().isoformat(),
    })


def _add_card(s: Session, symbol: str, market: str,
              status: str = 'draft',
              stop_loss_price: float | None = None,
              entry_price: float | None = None) -> int:
    s.execute(text(
        "INSERT INTO strategy_card "
        "(symbol, market, status, stop_loss_price, entry_price, "
        " created_at, updated_at) "
        "VALUES (:sym, :mkt, :st, :sl, :ep, :ca, :ua)"
    ), {
        'sym': symbol, 'mkt': market, 'st': status,
        'sl': stop_loss_price, 'ep': entry_price,
        'ca': '2026-03-01T00:00:00+00:00',
        'ua': '2026-03-01T00:00:00+00:00',
    })
    row = s.execute(text("SELECT last_insert_rowid()")).scalar()
    return row


# ── TestDecisionAdvisorEmpty ──────────────────────────────────────────────────

class TestDecisionAdvisorEmpty:
    def test_no_trades_no_cards_returns_empty_report(self, session):
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        assert report.advice == []
        assert report.total_positions == 0
        assert report.risk_status == 'ok'
        assert report.risk_violations == 0
        assert report.exit_count == 0
        assert report.enter_count == 0

    def test_report_metadata_present(self, session):
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        assert report.asof == ASOF
        assert report.generated_at  # non-empty


# ── TestHoldRule ──────────────────────────────────────────────────────────────

class TestHoldRule:
    def test_open_position_no_card_defaults_to_hold(self, session):
        _add_trade(session, 'A', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'A', 'CN', 11.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        assert len(report.advice) == 1
        adv = report.advice[0]
        assert adv.action == 'hold'
        assert adv.reason == 'within_limits'
        assert adv.card_id is None

    def test_hold_advice_carries_position_data(self, session):
        _add_trade(session, 'B', 'CN', 'buy', 10.0, 200)
        _add_price(session, 'B', 'CN', 12.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = report.advice[0]
        assert adv.net_shares == 200.0
        assert adv.avg_cost == 10.0
        assert adv.current_price == 12.0
        assert adv.unrealized_pnl == pytest.approx(400.0)  # (12-10)*200


# ── TestExitRule ──────────────────────────────────────────────────────────────

class TestExitRule:
    def test_price_below_stop_loss_triggers_exit(self, session):
        _add_trade(session, 'C', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'C', 'CN', 7.5)  # below stop_loss=8.0
        _add_card(session, 'C', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = next(a for a in report.advice if a.symbol == 'C')
        assert adv.action == 'exit'
        assert adv.reason == 'stop_loss_hit'
        assert adv.stop_loss_price == 8.0
        assert report.exit_count == 1

    def test_price_exactly_at_stop_loss_triggers_exit(self, session):
        _add_trade(session, 'D', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'D', 'CN', 8.0)  # exactly at stop
        _add_card(session, 'D', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = next(a for a in report.advice if a.symbol == 'D')
        assert adv.action == 'exit'

    def test_price_above_stop_loss_does_not_exit(self, session):
        _add_trade(session, 'E', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'E', 'CN', 9.5)  # above stop_loss=8.0
        _add_card(session, 'E', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = next(a for a in report.advice if a.symbol == 'E')
        assert adv.action == 'hold'

    def test_no_price_skips_stop_loss_check(self, session):
        # No raw_price row → current_price=None → R1 cannot fire
        _add_trade(session, 'F', 'CN', 'buy', 10.0, 100)
        _add_card(session, 'F', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = next(a for a in report.advice if a.symbol == 'F')
        assert adv.action == 'hold'


# ── TestTrimRule ──────────────────────────────────────────────────────────────

class TestTrimRule:
    def test_concentration_breach_triggers_trim(self, session):
        # Two positions: 'G' is 80% of portfolio → concentration breach
        _add_trade(session, 'G', 'CN', 'buy', 10.0, 800)
        _add_trade(session, 'H', 'CN', 'buy', 10.0, 200)
        _add_price(session, 'G', 'CN', 10.0)
        _add_price(session, 'H', 'CN', 10.0)
        # G = 8000/10000 = 80% > 20% → C1 violation
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=0.20)
        adv_g = next(a for a in report.advice if a.symbol == 'G')
        assert adv_g.action == 'trim'
        assert adv_g.reason == 'concentration_breach'
        assert report.trim_count == 1


# ── TestStopLossPriorityOverTrim ──────────────────────────────────────────────

class TestStopLossPriorityOverTrim:
    def test_exit_beats_trim_when_both_apply(self, session):
        # 'I' is 80% of portfolio AND below stop loss → should exit, not trim
        _add_trade(session, 'I', 'CN', 'buy', 10.0, 800)
        _add_trade(session, 'J', 'CN', 'buy', 10.0, 200)
        _add_price(session, 'I', 'CN', 7.0)   # below stop_loss=8.0
        _add_price(session, 'J', 'CN', 10.0)
        _add_card(session, 'I', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=0.20)
        adv_i = next(a for a in report.advice if a.symbol == 'I')
        assert adv_i.action == 'exit'   # R1 > R2


# ── TestCardRules ─────────────────────────────────────────────────────────────

class TestCardRules:
    def test_active_card_no_position_suggests_enter(self, session):
        _add_card(session, 'K', 'US', status='active', entry_price=50.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        adv = next(a for a in report.advice if a.symbol == 'K')
        assert adv.action == 'enter'
        assert adv.reason == 'card_active'
        assert adv.net_shares is None  # no position yet
        assert report.enter_count == 1

    def test_draft_card_no_position_suggests_watch(self, session):
        _add_card(session, 'L', 'CN', status='draft')
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        adv = next(a for a in report.advice if a.symbol == 'L')
        assert adv.action == 'watch'
        assert adv.reason == 'card_draft'
        assert report.watch_count == 1


# ── TestCardWithPosition ──────────────────────────────────────────────────────

class TestCardWithPosition:
    def test_card_plus_position_evaluates_position_rule(self, session):
        # Active card + existing position above stop loss → hold (not enter)
        _add_trade(session, 'M', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'M', 'CN', 12.0)
        _add_card(session, 'M', 'CN', status='active', stop_loss_price=8.0)
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        advices = [a for a in report.advice if a.symbol == 'M']
        assert len(advices) == 1   # not duplicated
        assert advices[0].action == 'hold'
        assert advices[0].card_status == 'active'


# ── TestClosedCardIgnored ─────────────────────────────────────────────────────

class TestClosedCardIgnored:
    def test_closed_card_produces_no_advice(self, session):
        _add_card(session, 'N', 'CN', status='closed')
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        assert not any(a.symbol == 'N' for a in report.advice)


# ── TestActiveBeforeDraft ─────────────────────────────────────────────────────

class TestActiveBeforeDraft:
    def test_active_card_preferred_over_draft_same_symbol(self, session):
        _add_card(session, 'O', 'CN', status='draft', stop_loss_price=7.0)
        _add_card(session, 'O', 'CN', status='active', stop_loss_price=8.0)
        # Add position to trigger position evaluation
        _add_trade(session, 'O', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'O', 'CN', 7.5)  # below active card stop=8.0
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        adv = next(a for a in report.advice if a.symbol == 'O')
        # active card's stop_loss=8.0 is used → price 7.5 triggers exit
        assert adv.action == 'exit'
        assert adv.stop_loss_price == 8.0


# ── TestRiskPropagation ───────────────────────────────────────────────────────

class TestRiskPropagation:
    def test_risk_status_forwarded_from_risk_checker(self, session):
        # Drawdown > 15% → breach
        _add_trade(session, 'P', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'P', 'CN', 8.0)  # -20% loss
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0,
                                  max_drawdown_pct=0.15)
        assert report.risk_status == 'breach'
        assert report.risk_violations >= 1


# ── TestCountAggregation ──────────────────────────────────────────────────────

class TestCountAggregation:
    def test_mixed_actions_counted_correctly(self, session):
        # hold: Q (no card, above limits)
        _add_trade(session, 'Q', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'Q', 'CN', 11.0)
        # exit: R (below stop loss)
        _add_trade(session, 'R', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'R', 'CN', 7.0)
        _add_card(session, 'R', 'CN', status='active', stop_loss_price=8.0)
        # enter: S (active card, no position)
        _add_card(session, 'S', 'US', status='active')
        # watch: T (draft card, no position)
        _add_card(session, 'T', 'CN', status='draft')

        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        assert report.hold_count == 1
        assert report.exit_count == 1
        assert report.enter_count == 1
        assert report.watch_count == 1
        assert report.trim_count == 0
        assert report.total_positions == 2


# ── TestDecisionReportJson ────────────────────────────────────────────────────

class TestDecisionReportJson:
    def test_json_round_trip_empty(self, session):
        report = ADVISOR.evaluate(asof=ASOF, session=session)
        payload = json.loads(report_to_json(report))
        assert payload['asof'] == ASOF.isoformat()
        assert payload['advice'] == []
        assert payload['risk_status'] == 'ok'
        assert 'generated_at' in payload

    def test_json_round_trip_with_advice(self, session):
        _add_trade(session, 'U', 'CN', 'buy', 10.0, 100)
        _add_price(session, 'U', 'CN', 11.0)
        _add_card(session, 'V', 'US', status='active')
        report = ADVISOR.evaluate(asof=ASOF, session=session, max_position_pct=1.0)
        payload = json.loads(report_to_json(report))
        assert len(payload['advice']) == 2
        symbols = {a['symbol'] for a in payload['advice']}
        assert 'U' in symbols
        assert 'V' in symbols
