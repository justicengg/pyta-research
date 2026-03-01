from datetime import date

from src.fetchers.base import DataFetcher
from src.fetchers.fundamental.fundamental_fetcher import FundamentalFetcher
from src.fetchers.macro.macro_fetcher import MacroFetcher
from src.fetchers.market.baostock_fetcher import BaostockFetcher


def test_incremental_start():
    requested = date(2026, 1, 1)
    assert DataFetcher.incremental_start(None, requested) == requested
    assert DataFetcher.incremental_start(date(2026, 1, 10), requested) == date(2026, 1, 11)


def test_market_fetcher_dedup_and_incremental():
    rows = [
        {'trade_date': '2026-01-11', 'open': 1, 'high': 2, 'low': 1, 'close': 2, 'volume': 10, 'adj_factor': 1},
        {'trade_date': '2026-01-11', 'open': 1, 'high': 2, 'low': 1, 'close': 2, 'volume': 10, 'adj_factor': 1},
    ]

    result = BaostockFetcher().fetch(
        symbol='sh.600000',
        market='CN',
        start=date(2026, 1, 1),
        end=date(2026, 1, 20),
        incremental=True,
        last_date=date(2026, 1, 10),
        adapter=lambda **_: rows,
    )
    assert len(result) == 1
    assert result[0]['trade_date'] == date(2026, 1, 11)


def test_fundamental_point_in_time_filter():
    rows = [
        {
            'report_period': '2025-12-31',
            'publish_date': '2026-01-20',
            'roe': 0.1,
            'revenue': 100,
            'net_profit': 10,
            'debt_ratio': 0.3,
            'operating_cashflow': 5,
        },
        {
            'report_period': '2025-09-30',
            'publish_date': '2025-10-31',
            'roe': 0.2,
            'revenue': 120,
            'net_profit': 12,
            'debt_ratio': 0.2,
            'operating_cashflow': 8,
        },
    ]

    result = FundamentalFetcher().fetch(
        symbol='600000', market='CN', asof=date(2025, 12, 31), adapter=lambda **_: rows
    )
    assert len(result) == 1
    assert result[0]['publish_date'] == date(2025, 10, 31)


def test_macro_frequency_mapping():
    result = MacroFetcher().fetch(
        series='CPIAUCSL',
        market='US',
        source='fred',
        start=date(2025, 1, 1),
        end=date(2025, 1, 31),
        adapter=lambda **_: [{'obs_date': '2025-01-01', 'value': 300.0, 'frequency': 'M'}],
    )
    assert result[0]['frequency'] == 'month'
