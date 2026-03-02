"""Unit tests for PortfolioTracker (INV-41 + patch F1/F2/F3).

Test organisation
-----------------
TestEmptyPortfolio          — baseline empty portfolio
TestBuyOnlyPositions        — buy-only aggregation
TestSellPositions           — partial / full / over-sell
TestDirectionValidation     — F1: DB CHECK + app-level ValueError
TestSourceFiltering         — F2: source-aware price lookup
TestBatchQuery              — F3: batch price query correctness
TestUnrealizedPnL           — PnL maths
TestPointInTime             — PIT date boundary
TestSnapshotToJson          — JSON serialiser

All tests use in-memory SQLite.  Price-related tests pass ``price_source_cn``/
``price_source_us`` explicitly via the ``SNAP_SRC`` constant so they are not
sensitive to defaults.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from sqlalchemy import Column
from sqlalchemy import Date as SaDate
from sqlalchemy import DateTime, Integer, MetaData, Numeric, String, Table, Text, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import RawPrice, TradeLog
from src.portfolio.report import snapshot_to_json
from src.portfolio.tracker import PortfolioTracker
from src.types import PortfolioSnapshot

# ---------------------------------------------------------------------------
# Constants and fixtures
# ---------------------------------------------------------------------------

ASOF = date(2026, 3, 1)
SYMBOL = 'sh.600000'
MARKET = 'CN'
TEST_SOURCE = 'test'

# All snapshot() calls in PnL / price tests use TEST_SOURCE for both markets
# so the batch query's source filter is deterministic.
SNAP_SRC = dict(price_source_cn=TEST_SOURCE, price_source_us=TEST_SOURCE)


@pytest.fixture()
def mem_session() -> Session:
    """In-memory SQLite session with full ORM schema (incl. CHECK constraints)."""
    engine = create_engine('sqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    with SL() as session:
        yield session


@pytest.fixture()
def unconstrained_session() -> Session:
    """In-memory SQLite session whose trade_log table has NO CHECK constraint.

    Used exclusively to test the application-level ValueError in
    PortfolioTracker.snapshot(), bypassing the DB-level guard.
    """
    engine = create_engine('sqlite:///:memory:', future=True)
    meta = MetaData()
    # Minimal trade_log table — no CheckConstraint on direction
    Table(
        'trade_log', meta,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('symbol', String(32), nullable=False),
        Column('market', String(16), nullable=False),
        Column('card_id', Integer),
        Column('direction', String(8), nullable=False),
        Column('price', Numeric(18, 6), nullable=False),
        Column('shares', Numeric(18, 4), nullable=False),
        Column('amount', Numeric(24, 6), nullable=False),
        Column('trade_date', SaDate, nullable=False),
        Column('note', Text),
        Column('created_at', DateTime(timezone=True), server_default='now'),
    )
    meta.create_all(engine)
    SL = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    with SL() as session:
        yield session


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _add_trade(
    session: Session,
    symbol: str,
    market: str,
    direction: str,
    price: float,
    shares: float,
    d: date,
    card_id: int | None = None,
) -> None:
    session.add(TradeLog(
        symbol=symbol, market=market, card_id=card_id,
        direction=direction, price=price, shares=shares,
        amount=price * shares, trade_date=d, note=None,
    ))


def _add_price(
    session: Session,
    symbol: str,
    market: str,
    d: date,
    close: float,
    source: str = TEST_SOURCE,
) -> None:
    session.add(RawPrice(
        symbol=symbol, market=market, trade_date=d,
        open=close, high=close * 1.01, low=close * 0.99,
        close=close, volume=1_000_000.0, adj_factor=None, source=source,
    ))


# ---------------------------------------------------------------------------
# Empty portfolio
# ---------------------------------------------------------------------------

class TestEmptyPortfolio:
    def test_no_trades_returns_empty_snapshot(self, mem_session: Session) -> None:
        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert isinstance(snap, PortfolioSnapshot)
        assert snap.positions == []
        assert snap.total_unrealized_pnl is None
        assert snap.snapshot_date == ASOF

    def test_generated_at_is_iso_string(self, mem_session: Session) -> None:
        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert 'T' in snap.generated_at


# ---------------------------------------------------------------------------
# Buy-only positions
# ---------------------------------------------------------------------------

class TestBuyOnlyPositions:
    def test_single_buy_creates_position(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert len(snap.positions) == 1
        pos = snap.positions[0]
        assert pos.symbol == SYMBOL
        assert pos.market == MARKET
        assert abs(pos.net_shares - 100.0) < 1e-4
        assert abs(pos.avg_cost - 10.0) < 1e-6

    def test_avg_cost_is_weighted_average(self, mem_session: Session) -> None:
        # Buy 100 @ 10.0 and 100 @ 12.0 → avg_cost = 11.0
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=2))
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=12.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        pos = snap.positions[0]
        assert abs(pos.avg_cost - 11.0) < 1e-6
        assert abs(pos.net_shares - 200.0) < 1e-4

    def test_multiple_symbols_each_appear(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_trade(mem_session, 'us.AAPL', 'US', 'buy', price=200.0, shares=5.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert len(snap.positions) == 2
        symbols = {p.symbol for p in snap.positions}
        assert SYMBOL in symbols
        assert 'us.AAPL' in symbols


# ---------------------------------------------------------------------------
# Sell / closed positions
# ---------------------------------------------------------------------------

class TestSellPositions:
    def test_partial_sell_reduces_net_shares(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=2))
        _add_trade(mem_session, SYMBOL, MARKET, 'sell', price=12.0, shares=40.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert len(snap.positions) == 1
        assert abs(snap.positions[0].net_shares - 60.0) < 1e-4

    def test_full_sell_excludes_position(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=2))
        _add_trade(mem_session, SYMBOL, MARKET, 'sell', price=12.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert snap.positions == []

    def test_oversell_also_excluded(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=50.0,
                   d=ASOF - timedelta(days=2))
        _add_trade(mem_session, SYMBOL, MARKET, 'sell', price=12.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert snap.positions == []


# ---------------------------------------------------------------------------
# F1 — Direction validation (CHECK constraint + app-level ValueError)
# ---------------------------------------------------------------------------

class TestDirectionValidation:
    def test_db_rejects_invalid_direction(self, mem_session: Session) -> None:
        """DB-level CHECK constraint blocks non-buy/sell direction at flush."""
        with pytest.raises(IntegrityError):
            mem_session.add(TradeLog(
                symbol=SYMBOL, market=MARKET, card_id=None,
                direction='BUY',           # uppercase — not in ('buy','sell')
                price=10.0, shares=100.0, amount=1000.0,
                trade_date=ASOF, note=None,
            ))
            mem_session.flush()

    def test_tracker_raises_on_unknown_direction(
        self, unconstrained_session: Session
    ) -> None:
        """App-level ValueError fires for unknown direction in the DB.

        The unconstrained_session fixture allows inserting bad data that bypasses
        the CHECK constraint, testing the tracker's own defence-in-depth guard.
        """
        unconstrained_session.execute(text(
            "INSERT INTO trade_log "
            "(symbol, market, direction, price, shares, amount, trade_date, created_at) "
            "VALUES ('sh.600000', 'CN', 'HOLD', 10.0, 100.0, 1000.0, "
            "'2026-02-28', '2026-02-28T00:00:00+00:00')"
        ))
        unconstrained_session.commit()

        with pytest.raises(ValueError, match="unknown direction"):
            PortfolioTracker().snapshot(ASOF, unconstrained_session)


# ---------------------------------------------------------------------------
# F2 — Source-aware price lookup
# ---------------------------------------------------------------------------

class TestSourceFiltering:
    def test_correct_source_returns_price(self, mem_session: Session) -> None:
        """Price stored under the preferred source is fetched correctly."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0, source='baostock')
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, price_source_cn='baostock')
        assert abs(snap.positions[0].current_price - 12.0) < 1e-6

    def test_wrong_source_gives_no_price(self, mem_session: Session) -> None:
        """Price stored under a different source is ignored (returns None)."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0, source='yfinance')
        mem_session.commit()

        # CN prefers 'baostock' but only 'yfinance' data exists → price is None
        snap = PortfolioTracker().snapshot(ASOF, mem_session, price_source_cn='baostock')
        assert snap.positions[0].current_price is None

    def test_multiple_sources_only_preferred_used(self, mem_session: Session) -> None:
        """When multiple sources exist on the same date, only preferred is used."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0, source='baostock')
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=999.0, source='other_source')
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, price_source_cn='baostock')
        assert abs(snap.positions[0].current_price - 12.0) < 1e-6

    def test_cn_and_us_use_independent_sources(self, mem_session: Session) -> None:
        """CN and US positions each pull from their own preferred source."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0, source='baostock')

        sym_us = 'us.AAPL'
        _add_trade(mem_session, sym_us, 'US', 'buy', price=100.0, shares=10.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, sym_us, 'US', ASOF, close=110.0, source='yfinance')
        mem_session.commit()

        snap = PortfolioTracker().snapshot(
            ASOF, mem_session,
            price_source_cn='baostock',
            price_source_us='yfinance',
        )
        by_sym = {p.symbol: p for p in snap.positions}
        assert abs(by_sym[SYMBOL].current_price - 12.0) < 1e-6
        assert abs(by_sym[sym_us].current_price - 110.0) < 1e-6


# ---------------------------------------------------------------------------
# F3 — Batch price query correctness
# ---------------------------------------------------------------------------

class TestBatchQuery:
    def test_prices_for_multiple_positions_fetched_correctly(
        self, mem_session: Session
    ) -> None:
        """Batch fetch returns the right price for each of N open positions."""
        symbols = [f'sh.{600000 + i}' for i in range(5)]
        for i, sym in enumerate(symbols):
            _add_trade(mem_session, sym, MARKET, 'buy',
                       price=float(10 + i), shares=100.0,
                       d=ASOF - timedelta(days=1))
            _add_price(mem_session, sym, MARKET, ASOF, close=float(12 + i))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        assert len(snap.positions) == 5
        by_sym = {p.symbol: p for p in snap.positions}
        for i, sym in enumerate(symbols):
            assert abs(by_sym[sym].current_price - float(12 + i)) < 1e-6

    def test_batch_uses_latest_date_per_symbol(self, mem_session: Session) -> None:
        """Batch query returns the most recent price, not an older one."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=2))
        _add_price(mem_session, SYMBOL, MARKET, ASOF - timedelta(days=1), close=11.0)
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        assert abs(snap.positions[0].current_price - 12.0) < 1e-6


# ---------------------------------------------------------------------------
# Unrealized PnL
# ---------------------------------------------------------------------------

class TestUnrealizedPnL:
    def test_pnl_computed_correctly(self, mem_session: Session) -> None:
        # Buy 100 @ 10.0, current price 12.0 → unrealized_pnl = +200
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        pos = snap.positions[0]
        assert abs(pos.current_price - 12.0) < 1e-6
        assert abs(pos.unrealized_pnl - 200.0) < 1e-4
        assert abs(pos.unrealized_pnl_pct - 0.2) < 1e-6

    def test_negative_pnl(self, mem_session: Session) -> None:
        # Buy 100 @ 10.0, current price 8.0 → unrealized_pnl = -200
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=8.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        pos = snap.positions[0]
        assert abs(pos.unrealized_pnl - (-200.0)) < 1e-4
        assert abs(pos.unrealized_pnl_pct - (-0.2)) < 1e-6

    def test_total_pnl_sums_all_positions(self, mem_session: Session) -> None:
        # position 1: 100 @ 10.0, price 12.0 → +200
        # position 2: 50 @ 20.0, price 18.0 → -100  →  total = +100
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)

        sym2 = 'us.AAPL'
        _add_trade(mem_session, sym2, 'US', 'buy', price=20.0, shares=50.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, sym2, 'US', ASOF, close=18.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        assert snap.total_unrealized_pnl is not None
        assert abs(snap.total_unrealized_pnl - 100.0) < 1e-4

    def test_no_price_gives_none_pnl(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        pos = snap.positions[0]
        assert pos.current_price is None
        assert pos.unrealized_pnl is None
        assert pos.unrealized_pnl_pct is None

    def test_total_pnl_none_when_no_prices(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        assert snap.total_unrealized_pnl is None


# ---------------------------------------------------------------------------
# Point-In-Time correctness
# ---------------------------------------------------------------------------

class TestPointInTime:
    def test_future_trades_excluded(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF + timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert snap.positions == []

    def test_trade_on_asof_is_included(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0, d=ASOF)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert len(snap.positions) == 1

    def test_future_price_not_used(self, mem_session: Session) -> None:
        """Price query uses only trade_date <= asof; future rows are ignored."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)
        _add_price(mem_session, SYMBOL, MARKET, ASOF + timedelta(days=1), close=999.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        assert abs(snap.positions[0].current_price - 12.0) < 1e-6


# ---------------------------------------------------------------------------
# snapshot_to_json
# ---------------------------------------------------------------------------

class TestSnapshotToJson:
    def test_output_is_valid_json(self, mem_session: Session) -> None:
        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        output = snapshot_to_json(snap)
        data = json.loads(output)
        assert 'snapshot_date' in data
        assert 'positions' in data
        assert 'total_unrealized_pnl' in data

    def test_snapshot_date_is_iso_string(self, mem_session: Session) -> None:
        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        data = json.loads(snapshot_to_json(snap))
        assert data['snapshot_date'] == ASOF.isoformat()

    def test_positions_serialized(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session, **SNAP_SRC)
        data = json.loads(snapshot_to_json(snap))
        assert len(data['positions']) == 1
        pos = data['positions'][0]
        assert pos['symbol'] == SYMBOL
        assert pos['market'] == MARKET
