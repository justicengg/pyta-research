"""Portfolio tracker — 大呆子（策略官）持仓聚合层.

Computes a point-in-time PortfolioSnapshot by aggregating the append-only
trade_log table up to a given asof date.

Logic
-----
1. Fetch all TradeLog rows where trade_date <= asof.
2. Group by (symbol, market).
3. net_shares  = Σ buy_shares  − Σ sell_shares
4. Skip positions where net_shares <= 0 (closed or over-sold).
5. avg_cost    = Σ(price × shares for buys) / Σ(buy_shares)
6. current_price = latest raw_price.close on or before asof.
7. unrealized_pnl     = (current_price − avg_cost) × net_shares
8. unrealized_pnl_pct = (current_price − avg_cost) / avg_cost
9. total_unrealized_pnl = Σ unrealized_pnl for all open positions.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import RawPrice, TradeLog
from src.types import PortfolioSnapshot, PositionSnapshot


class PortfolioTracker:
    """Compute a point-in-time portfolio snapshot from the trade_log."""

    def snapshot(self, asof: date, session: Session) -> PortfolioSnapshot:
        """Aggregate trade_log up to *asof* and return a PortfolioSnapshot."""
        # 1. Fetch all trades on or before asof
        stmt = (
            select(TradeLog)
            .where(TradeLog.trade_date <= asof)
            .order_by(TradeLog.trade_date)
        )
        trades = list(session.scalars(stmt).all())

        # 2. Group by (symbol, market)
        buy_shares: dict[tuple[str, str], float] = defaultdict(float)
        sell_shares: dict[tuple[str, str], float] = defaultdict(float)
        buy_cost: dict[tuple[str, str], float] = defaultdict(float)   # Σ(price×shares) for buys

        for t in trades:
            key = (t.symbol, t.market)
            if t.direction == 'buy':
                s = float(t.shares)
                buy_shares[key] += s
                buy_cost[key] += float(t.price) * s
            else:  # 'sell'
                sell_shares[key] += float(t.shares)

        # 3. Build PositionSnapshot for each open position
        positions: list[PositionSnapshot] = []
        all_keys = set(buy_shares.keys()) | set(sell_shares.keys())

        for key in all_keys:
            symbol, market = key
            net = buy_shares[key] - sell_shares[key]
            if net <= 0:
                continue  # closed or flat

            avg_cost = (
                buy_cost[key] / buy_shares[key]
                if buy_shares[key] > 0
                else None
            )
            current_price = self._get_current_price(symbol, market, asof, session)

            if avg_cost is not None and current_price is not None:
                unrealized_pnl = (current_price - avg_cost) * net
                unrealized_pnl_pct = (current_price - avg_cost) / avg_cost
            else:
                unrealized_pnl = None
                unrealized_pnl_pct = None

            positions.append(PositionSnapshot(
                symbol=symbol,
                market=market,
                net_shares=net,
                avg_cost=avg_cost,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            ))

        # 4. Aggregate total PnL
        pnl_values = [p.unrealized_pnl for p in positions if p.unrealized_pnl is not None]
        total_unrealized_pnl: float | None = sum(pnl_values) if pnl_values else None

        return PortfolioSnapshot(
            snapshot_date=asof,
            generated_at=datetime.now(timezone.utc).isoformat(),
            positions=positions,
            total_unrealized_pnl=total_unrealized_pnl,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_current_price(
        symbol: str,
        market: str,
        asof: date,
        session: Session,
    ) -> float | None:
        """Return the latest close price on or before *asof*."""
        stmt = (
            select(RawPrice.close)
            .where(
                RawPrice.symbol == symbol,
                RawPrice.market == market,
                RawPrice.trade_date <= asof,
                RawPrice.close.isnot(None),
            )
            .order_by(RawPrice.trade_date.desc())
            .limit(1)
        )
        result = session.scalar(stmt)
        return float(result) if result is not None else None
