"""Unit tests for FactorCalculator.

Uses an in-memory SQLite database created directly from the ORM metadata
(no Alembic needed) to keep unit tests fast.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import DerivedFactor, RawFundamental, RawPrice
from src.factors.calculator import FactorCalculator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_session() -> Session:
    """Spin up a fresh in-memory SQLite DB and yield a session."""
    engine = create_engine('sqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    with SL() as session:
        yield session


def _price_row(symbol: str, market: str, trade_date: date, close: float, volume: float = 1_000_000.0) -> dict:
    return {
        'symbol': symbol,
        'market': market,
        'trade_date': trade_date,
        'open': close,
        'high': close,
        'low': close,
        'close': close,
        'volume': volume,
        'adj_factor': None,
        'source': 'test',
    }


def _fundamental_row(
    symbol: str,
    market: str,
    report_period: date,
    publish_date: date,
    roe: float | None = 0.10,
    revenue: float | None = 1_000_000.0,
    net_profit: float | None = 100_000.0,
    debt_ratio: float | None = 0.40,
) -> dict:
    return {
        'symbol': symbol,
        'market': market,
        'report_period': report_period,
        'publish_date': publish_date,
        'roe': roe,
        'revenue': revenue,
        'net_profit': net_profit,
        'debt_ratio': debt_ratio,
        'operating_cashflow': None,
        'source': 'test',
    }


# ---------------------------------------------------------------------------
# Price factor tests
# ---------------------------------------------------------------------------

class TestPriceFactors:
    def test_returns_empty_when_no_price_data(self, mem_session: Session) -> None:
        rows = FactorCalculator().compute('sh.600000', 'CN', date(2026, 3, 1), mem_session)
        assert rows == []

    def test_no_factors_with_fewer_than_6_rows(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        for i in range(5):
            mem_session.add(RawPrice(**_price_row('sh.600000', 'CN', asof - timedelta(days=i), 10.0)))
        mem_session.commit()

        rows = FactorCalculator().compute('sh.600000', 'CN', asof, mem_session)
        names = {r['factor_name'] for r in rows}
        assert 'momentum_5d' not in names
        assert 'momentum_20d' not in names

    def test_momentum_5d_computed_correctly(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        # 21 days of prices; close on asof = 11.0, close 5 days ago = 10.0 → +10%
        closes = [11.0] + [10.0] * 20
        for i, c in enumerate(closes):
            mem_session.add(RawPrice(**_price_row('sh.600000', 'CN', asof - timedelta(days=i), c)))
        mem_session.commit()

        rows = FactorCalculator().compute('sh.600000', 'CN', asof, mem_session)
        factor = next(r for r in rows if r['factor_name'] == 'momentum_5d')
        assert abs(factor['factor_value'] - 0.10) < 1e-9

    def test_momentum_20d_computed_correctly(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        # close[0]=12, close[20]=10 → +20%
        closes = [12.0] + [10.0] * 20
        for i, c in enumerate(closes):
            mem_session.add(RawPrice(**_price_row('sh.600000', 'CN', asof - timedelta(days=i), c)))
        mem_session.commit()

        rows = FactorCalculator().compute('sh.600000', 'CN', asof, mem_session)
        factor = next(r for r in rows if r['factor_name'] == 'momentum_20d')
        assert abs(factor['factor_value'] - 0.20) < 1e-9

    def test_volume_ratio_5_20_computed_correctly(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        # First 5 rows volume=2e6, next 15 rows volume=1e6
        # avg(5) = 2e6, avg(20) = (5*2e6 + 15*1e6)/20 = 1.25e6 → ratio = 2/1.25 = 1.6
        for i in range(20):
            vol = 2_000_000.0 if i < 5 else 1_000_000.0
            mem_session.add(RawPrice(**_price_row('sh.600000', 'CN', asof - timedelta(days=i), 10.0, vol)))
        mem_session.commit()

        rows = FactorCalculator().compute('sh.600000', 'CN', asof, mem_session)
        factor = next(r for r in rows if r['factor_name'] == 'volume_ratio_5_20')
        assert abs(factor['factor_value'] - 1.6) < 1e-9

    def test_pit_excludes_future_prices(self, mem_session: Session) -> None:
        """Prices after asof_date must not contribute to factors."""
        asof = date(2026, 3, 1)
        # Add 21 prices starting from asof+1 (all in the future)
        for i in range(21):
            mem_session.add(RawPrice(**_price_row('sh.600000', 'CN', asof + timedelta(days=i + 1), 10.0)))
        mem_session.commit()

        rows = FactorCalculator().compute('sh.600000', 'CN', asof, mem_session)
        assert rows == []


# ---------------------------------------------------------------------------
# Fundamental factor tests
# ---------------------------------------------------------------------------

class TestFundamentalFactors:
    def test_returns_empty_when_no_fundamental_data(self, mem_session: Session) -> None:
        rows = FactorCalculator().compute('600000', 'CN', date(2026, 3, 1), mem_session)
        assert rows == []

    def test_roe_latest_and_debt_ratio_latest(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        pub = asof - timedelta(days=10)
        mem_session.add(
            RawFundamental(**_fundamental_row('600000', 'CN', date(2025, 12, 31), pub, roe=0.15, debt_ratio=0.45))
        )
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        by_name = {r['factor_name']: r['factor_value'] for r in rows}

        assert abs(by_name['roe_latest'] - 0.15) < 1e-9
        assert abs(by_name['debt_ratio_latest'] - 0.45) < 1e-9

    def test_roe_trend_two_quarters(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        pub = asof - timedelta(days=10)
        # Q1 latest ROE=0.18, Q0 previous ROE=0.12 → trend = +0.06
        mem_session.add(RawFundamental(**_fundamental_row('600000', 'CN', date(2025, 12, 31), pub, roe=0.18)))
        mem_session.add(RawFundamental(**_fundamental_row('600000', 'CN', date(2025, 9, 30), pub, roe=0.12)))
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        by_name = {r['factor_name']: r['factor_value'] for r in rows}
        assert abs(by_name['roe_trend'] - 0.06) < 1e-9

    def test_revenue_yoy_requires_5_quarters(self, mem_session: Session) -> None:
        """revenue_yoy should not appear when fewer than 5 quarters are available."""
        asof = date(2026, 3, 1)
        pub = asof - timedelta(days=10)
        for i in range(4):
            period = date(2025, 12, 31) - timedelta(days=90 * i)
            mem_session.add(RawFundamental(**_fundamental_row('600000', 'CN', period, pub)))
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        names = {r['factor_name'] for r in rows}
        assert 'revenue_yoy' not in names
        assert 'net_profit_yoy' not in names

    def test_revenue_yoy_and_net_profit_yoy_with_5_quarters(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        pub = asof - timedelta(days=10)
        # Periods: [2025-12-31, 2025-09-30, 2025-06-30, 2025-03-31, 2024-12-31]
        periods = [
            date(2025, 12, 31),
            date(2025, 9, 30),
            date(2025, 6, 30),
            date(2025, 3, 31),
            date(2024, 12, 31),
        ]
        # revenue grows 20% YoY: latest=1_200_000, yoy(index4)=1_000_000 → yoy=0.20
        revenues = [1_200_000.0, 1_100_000.0, 1_050_000.0, 1_020_000.0, 1_000_000.0]
        net_profits = [120_000.0, 110_000.0, 105_000.0, 102_000.0, 100_000.0]
        for p, rev, np in zip(periods, revenues, net_profits):
            mem_session.add(
                RawFundamental(**_fundamental_row('600000', 'CN', p, pub, revenue=rev, net_profit=np))
            )
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        by_name = {r['factor_name']: r['factor_value'] for r in rows}
        assert abs(by_name['revenue_yoy'] - 0.20) < 1e-9
        assert abs(by_name['net_profit_yoy'] - 0.20) < 1e-9

    def test_pit_excludes_unpublished_fundamentals(self, mem_session: Session) -> None:
        """Fundamentals whose publish_date > asof_date must be excluded."""
        asof = date(2026, 3, 1)
        # publish_date is 10 days in the future
        future_pub = asof + timedelta(days=10)
        mem_session.add(
            RawFundamental(**_fundamental_row('600000', 'CN', date(2025, 12, 31), future_pub))
        )
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        assert rows == []


# ---------------------------------------------------------------------------
# Row format test
# ---------------------------------------------------------------------------

class TestRowFormat:
    def test_output_rows_have_required_keys(self, mem_session: Session) -> None:
        asof = date(2026, 3, 1)
        pub = asof - timedelta(days=5)
        mem_session.add(RawFundamental(**_fundamental_row('600000', 'CN', date(2025, 12, 31), pub)))
        mem_session.commit()

        rows = FactorCalculator().compute('600000', 'CN', asof, mem_session)
        assert rows, 'expected at least one factor row'
        for row in rows:
            assert set(row.keys()) == {'symbol', 'market', 'asof_date', 'factor_name', 'factor_value'}
            assert row['symbol'] == '600000'
            assert row['market'] == 'CN'
            assert row['asof_date'] == asof
