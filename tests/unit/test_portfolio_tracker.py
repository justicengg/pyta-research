"""Unit tests for PortfolioTracker (INV-41).

Uses in-memory SQLite + Base.metadata.create_all().
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import RawPrice, TradeLog
from src.portfolio.report import snapshot_to_json
from src.portfolio.tracker import PortfolioTracker
from src.types import PortfolioSnapshot, PositionSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_session() -> Session:
    engine = create_engine('sqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    with SL() as session:
        yield session


ASOF = date(2026, 3, 1)
SYMBOL = 'sh.600000'
MARKET = 'CN'


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
        symbol=symbol,
        market=market,
        card_id=card_id,
        direction=direction,
        price=price,
        shares=shares,
        amount=price * shares,
        trade_date=d,
        note=None,
    ))


def _add_price(session: Session, symbol: str, market: str, d: date, close: float) -> None:
    session.add(RawPrice(
        symbol=symbol, market=market, trade_date=d,
        open=close, high=close * 1.01, low=close * 0.99,
        close=close, volume=1_000_000.0, adj_factor=None, source='test',
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
        # Must be a valid ISO-8601 string containing 'T'
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
        """If sell_shares > buy_shares (data error), position is excluded."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=50.0,
                   d=ASOF - timedelta(days=2))
        _add_trade(mem_session, SYMBOL, MARKET, 'sell', price=12.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert snap.positions == []


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

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
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

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        pos = snap.positions[0]
        assert abs(pos.unrealized_pnl - (-200.0)) < 1e-4
        assert abs(pos.unrealized_pnl_pct - (-0.2)) < 1e-6

    def test_total_pnl_sums_all_positions(self, mem_session: Session) -> None:
        # position 1: 100 @ 10.0, price 12.0 → +200
        # position 2: 50 @ 20.0, price 18.0 → −100
        # total = +100
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)

        sym2 = 'us.AAPL'
        _add_trade(mem_session, sym2, 'US', 'buy', price=20.0, shares=50.0,
                   d=ASOF - timedelta(days=1))
        _add_price(mem_session, sym2, 'US', ASOF, close=18.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        assert snap.total_unrealized_pnl is not None
        assert abs(snap.total_unrealized_pnl - 100.0) < 1e-4

    def test_no_price_gives_none_pnl(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        pos = snap.positions[0]
        assert pos.current_price is None
        assert pos.unrealized_pnl is None
        assert pos.unrealized_pnl_pct is None

    def test_total_pnl_none_when_no_prices(self, mem_session: Session) -> None:
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
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
        """Current price should use price on or before asof, not after."""
        _add_trade(mem_session, SYMBOL, MARKET, 'buy', price=10.0, shares=100.0,
                   d=ASOF - timedelta(days=1))
        # Add price on asof and a future price; should use asof price
        _add_price(mem_session, SYMBOL, MARKET, ASOF, close=12.0)
        _add_price(mem_session, SYMBOL, MARKET, ASOF + timedelta(days=1), close=999.0)
        mem_session.commit()

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
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

        snap = PortfolioTracker().snapshot(ASOF, mem_session)
        data = json.loads(snapshot_to_json(snap))
        assert len(data['positions']) == 1
        pos = data['positions'][0]
        assert pos['symbol'] == SYMBOL
        assert pos['market'] == MARKET
