from datetime import date

from src.db.session import configure_engine, get_session, insert_raw_fundamental, insert_raw_macro, insert_raw_price


def test_insert_and_dedupe(migrated_db: str):
    configure_engine(migrated_db)
    with get_session() as session:
        rows = [
            {
                'symbol': 'SPY',
                'market': 'US',
                'trade_date': date(2026, 1, 1),
                'open': 1,
                'high': 1,
                'low': 1,
                'close': 1,
                'volume': 1,
                'adj_factor': None,
                'source': 'yfinance',
            }
        ]
        assert insert_raw_price(session, rows) == 1
        assert insert_raw_price(session, rows) == 0

        f_rows = [
            {
                'symbol': '600000',
                'market': 'CN',
                'report_period': date(2025, 12, 31),
                'publish_date': date(2026, 1, 30),
                'roe': 0.1,
                'revenue': 10,
                'net_profit': 1,
                'debt_ratio': 0.2,
                'operating_cashflow': 2,
                'source': 'fundamental',
            }
        ]
        assert insert_raw_fundamental(session, f_rows) == 1
        assert insert_raw_fundamental(session, f_rows) == 0

        m_rows = [
            {
                'series_code': 'CPIAUCSL',
                'market': 'US',
                'obs_date': date(2026, 1, 1),
                'value': 300,
                'frequency': 'month',
                'source': 'fred',
            }
        ]
        assert insert_raw_macro(session, m_rows) == 1
        assert insert_raw_macro(session, m_rows) == 0
