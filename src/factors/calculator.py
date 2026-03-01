"""Factor calculator — derives quantitative signals from raw_price and raw_fundamental.

Factors computed as of a given asof_date use only data whose trade/publish date <= asof_date
(Point-In-Time safe, no look-ahead bias).

Available factors
-----------------
Price-based (requires raw_price rows up to asof_date):
  momentum_5d        : (close[0] / close[5]) - 1   (5-trading-day return)
  momentum_20d       : (close[0] / close[20]) - 1  (20-trading-day return)
  volume_ratio_5_20  : avg_volume(5d) / avg_volume(20d) — relative activity

Fundamental-based (PIT: uses only records where publish_date <= asof_date):
  roe_latest         : ROE of most recently published quarter
  roe_trend          : roe[0] - roe[1]  (MoQ change)
  debt_ratio_latest  : debt_ratio of most recently published quarter
  revenue_yoy        : (revenue[0] / revenue[4]) - 1  (same quarter YoY)
  net_profit_yoy     : (net_profit[0] / net_profit[4]) - 1
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import RawFundamental, RawPrice

# Number of trading-day rows to fetch for price factor computation
_PRICE_LOOKBACK = 30


class FactorCalculator:
    """Computes all derived factors for a (symbol, market) pair as of asof_date."""

    def compute(self, symbol: str, market: str, asof: date, session: Session) -> list[dict]:
        """Return a list of factor row dicts ready for insert_derived_factors."""
        rows: list[dict] = []
        rows.extend(self._price_factors(symbol, market, asof, session))
        rows.extend(self._fundamental_factors(symbol, market, asof, session))
        return rows

    # ------------------------------------------------------------------
    # Price factors
    # ------------------------------------------------------------------

    def _price_factors(self, symbol: str, market: str, asof: date, session: Session) -> list[dict]:
        # Fetch latest _PRICE_LOOKBACK trading sessions on or before asof_date.
        # We query a 90-day window to ensure enough trading days are found even
        # around holidays, then take the most recent _PRICE_LOOKBACK rows.
        stmt = (
            select(RawPrice.trade_date, RawPrice.close, RawPrice.volume)
            .where(
                RawPrice.symbol == symbol,
                RawPrice.market == market,
                RawPrice.trade_date <= asof,
                RawPrice.trade_date >= asof - timedelta(days=90),
            )
            .order_by(RawPrice.trade_date.desc())
            .limit(_PRICE_LOOKBACK)
        )
        prices = session.execute(stmt).fetchall()

        if not prices:
            return []

        closes = [float(p.close) for p in prices if p.close is not None]
        volumes = [float(p.volume) for p in prices if p.volume is not None]

        rows: list[dict] = []

        # momentum_5d: requires indices 0 and 5 (6 rows)
        if len(closes) >= 6 and closes[5] != 0:
            rows.append(self._make_row(symbol, market, asof, 'momentum_5d', closes[0] / closes[5] - 1.0))

        # momentum_20d: requires indices 0 and 20 (21 rows)
        if len(closes) >= 21 and closes[20] != 0:
            rows.append(self._make_row(symbol, market, asof, 'momentum_20d', closes[0] / closes[20] - 1.0))

        # volume_ratio_5_20: 5-day avg / 20-day avg
        if len(volumes) >= 20:
            vol_5 = sum(volumes[:5]) / 5.0
            vol_20 = sum(volumes[:20]) / 20.0
            if vol_20 > 0:
                rows.append(self._make_row(symbol, market, asof, 'volume_ratio_5_20', vol_5 / vol_20))

        return rows

    # ------------------------------------------------------------------
    # Fundamental factors (PIT)
    # ------------------------------------------------------------------

    def _fundamental_factors(self, symbol: str, market: str, asof: date, session: Session) -> list[dict]:
        # Point-In-Time: only include records where publish_date <= asof_date.
        # Fetch last 8 quarters ordered by report_period desc for trend / YoY.
        stmt = (
            select(
                RawFundamental.report_period,
                RawFundamental.roe,
                RawFundamental.revenue,
                RawFundamental.net_profit,
                RawFundamental.debt_ratio,
            )
            .where(
                RawFundamental.symbol == symbol,
                RawFundamental.market == market,
                RawFundamental.publish_date <= asof,
            )
            .order_by(RawFundamental.report_period.desc())
            .limit(8)
        )
        fundamentals = session.execute(stmt).fetchall()

        if not fundamentals:
            return []

        rows: list[dict] = []
        latest = fundamentals[0]

        # roe_latest
        if latest.roe is not None:
            rows.append(self._make_row(symbol, market, asof, 'roe_latest', float(latest.roe)))

        # debt_ratio_latest
        if latest.debt_ratio is not None:
            rows.append(self._make_row(symbol, market, asof, 'debt_ratio_latest', float(latest.debt_ratio)))

        # roe_trend: most-recent quarter minus previous quarter
        if len(fundamentals) >= 2:
            prev = fundamentals[1]
            if latest.roe is not None and prev.roe is not None:
                rows.append(
                    self._make_row(symbol, market, asof, 'roe_trend', float(latest.roe) - float(prev.roe))
                )

        # revenue_yoy / net_profit_yoy: same quarter one year ago = index 4
        if len(fundamentals) >= 5:
            yoy = fundamentals[4]
            if latest.revenue is not None and yoy.revenue is not None:
                base_rev = float(yoy.revenue)
                if base_rev != 0:
                    rows.append(
                        self._make_row(
                            symbol, market, asof, 'revenue_yoy',
                            float(latest.revenue) / base_rev - 1.0,
                        )
                    )
            if latest.net_profit is not None and yoy.net_profit is not None:
                base_np = float(yoy.net_profit)
                if base_np != 0:
                    rows.append(
                        self._make_row(
                            symbol, market, asof, 'net_profit_yoy',
                            float(latest.net_profit) / base_np - 1.0,
                        )
                    )

        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_row(symbol: str, market: str, asof: date, factor_name: str, factor_value: float | None) -> dict:
        return {
            'symbol': symbol,
            'market': market,
            'asof_date': asof,
            'factor_name': factor_name,
            'factor_value': factor_value,
        }
