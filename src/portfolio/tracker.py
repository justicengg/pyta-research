"""Portfolio tracker — 大呆子（策略官）持仓聚合层.

Computes a point-in-time PortfolioSnapshot by aggregating the append-only
trade_log table up to a given asof date.

Design decisions
----------------
F1 — Direction guard
    ``direction`` is constrained to ``('buy', 'sell')`` at both DB level (CHECK
    constraint) and application level.  An unknown direction raises
    ``ValueError`` immediately rather than silently corrupting holdings.

F2 — Source-aware price lookup
    ``raw_price`` is source-versioned: the same symbol+date can appear under
    multiple sources (e.g. 'baostock' for CN, 'yfinance' for US).  The caller
    supplies ``price_source_cn`` and ``price_source_us`` so the tracker always
    pulls from a deterministic, market-appropriate source.

F3 — Batched price query (N+1 eliminated)
    All open-position prices are fetched in a single subquery per source group
    (at most 2 round-trips total: one for CN, one for US) rather than one query
    per position.

Aggregate logic
---------------
1. Fetch all TradeLog rows where trade_date <= asof.
2. Group by (symbol, market).
3. net_shares  = Σ buy_shares  − Σ sell_shares
4. Skip positions where net_shares <= 0 (closed or over-sold).
5. avg_cost    = Σ(price × shares for buys) / Σ(buy_shares)
6. current_price = latest raw_price.close on or before asof for the preferred
   source.
7. unrealized_pnl     = (current_price − avg_cost) × net_shares
8. unrealized_pnl_pct = (current_price − avg_cost) / avg_cost
9. total_unrealized_pnl = Σ unrealized_pnl for all open positions that have a
   current_price.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.db.models import RawPrice, TradeLog
from src.types import PortfolioSnapshot, PositionSnapshot


class PortfolioTracker:
    """Compute a point-in-time portfolio snapshot from the trade_log."""

    def snapshot(
        self,
        asof: date,
        session: Session,
        price_source_cn: str = 'baostock',
        price_source_us: str = 'yfinance',
    ) -> PortfolioSnapshot:
        """Aggregate trade_log up to *asof* and return a PortfolioSnapshot.

        Parameters
        ----------
        asof:
            Cut-off date (inclusive).  Trades after this date are excluded.
        session:
            SQLAlchemy session to query against.
        price_source_cn:
            Preferred ``raw_price.source`` value for CN-market symbols.
            Defaults to ``'baostock'`` (matches scheduler ingest source).
        price_source_us:
            Preferred ``raw_price.source`` value for US-market symbols.
            Defaults to ``'yfinance'``.

        Raises
        ------
        ValueError
            If a trade_log row contains a direction other than ``'buy'`` or
            ``'sell'``.  (Defense-in-depth; the DB CHECK constraint is the
            primary guard.)
        """
        # 1. Fetch all trades on or before asof
        stmt = (
            select(TradeLog)
            .where(TradeLog.trade_date <= asof)
            .order_by(TradeLog.trade_date)
        )
        trades = list(session.scalars(stmt).all())

        # 2. Group by (symbol, market) — raise immediately on bad direction (F1)
        buy_shares: dict[tuple[str, str], float] = defaultdict(float)
        sell_shares: dict[tuple[str, str], float] = defaultdict(float)
        buy_cost: dict[tuple[str, str], float] = defaultdict(float)   # Σ(price×shares) for buys

        for t in trades:
            key = (t.symbol, t.market)
            if t.direction == 'buy':
                s = float(t.shares)
                buy_shares[key] += s
                buy_cost[key] += float(t.price) * s
            elif t.direction == 'sell':
                sell_shares[key] += float(t.shares)
            else:
                raise ValueError(
                    f"TradeLog id={t.id}: unknown direction {t.direction!r}; "
                    f"expected 'buy' or 'sell'"
                )

        # 3. Identify open positions (net_shares > 0)
        all_keys = set(buy_shares.keys()) | set(sell_shares.keys())
        open_keys: list[tuple[str, str]] = []
        position_meta: dict[tuple[str, str], tuple[float, float | None]] = {}

        for key in all_keys:
            net = buy_shares[key] - sell_shares[key]
            if net <= 0:
                continue  # closed or flat — skip
            avg_cost = (
                buy_cost[key] / buy_shares[key]
                if buy_shares[key] > 0
                else None
            )
            open_keys.append(key)
            position_meta[key] = (net, avg_cost)

        # 4. Batch-fetch latest prices (one query per source group — F2+F3)
        source_by_market = {'CN': price_source_cn, 'US': price_source_us}
        prices = self._batch_get_prices(open_keys, asof, session, source_by_market)

        # 5. Build PositionSnapshot list
        positions: list[PositionSnapshot] = []
        for key in open_keys:
            symbol, market = key
            net, avg_cost = position_meta[key]
            current_price = prices.get(key)

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

        # 6. Aggregate total PnL
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
    def _batch_get_prices(
        open_keys: list[tuple[str, str]],
        asof: date,
        session: Session,
        source_by_market: dict[str, str],
    ) -> dict[tuple[str, str], float | None]:
        """Batch-fetch the latest close price for every open position.

        Groups positions by preferred source (derived from market), then issues
        **one subquery per source group** (typically ≤ 2 round-trips total)
        instead of one query per position.

        Returns
        -------
        dict mapping ``(symbol, market)`` → ``float | None``.
        Positions with no matching price data map to ``None``.
        """
        if not open_keys:
            return {}

        # Fallback source for markets not listed in source_by_market
        default_source = next(iter(source_by_market.values()), 'yfinance')

        # Group position keys by their preferred price source
        by_source: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for key in open_keys:
            _, market = key
            source = source_by_market.get(market, default_source)
            by_source[source].append(key)

        result: dict[tuple[str, str], float | None] = {k: None for k in open_keys}

        for source, keys in by_source.items():
            # OR-filter: restrict subquery to the (symbol, market) pairs we need
            symbol_market_filter = or_(*(
                (RawPrice.symbol == sym) & (RawPrice.market == mkt)
                for sym, mkt in keys
            ))

            # Subquery: max(trade_date) per (symbol, market) for this source
            max_date_sq = (
                select(
                    RawPrice.symbol,
                    RawPrice.market,
                    func.max(RawPrice.trade_date).label('max_date'),
                )
                .where(
                    RawPrice.source == source,
                    RawPrice.trade_date <= asof,
                    RawPrice.close.isnot(None),
                    symbol_market_filter,
                )
                .group_by(RawPrice.symbol, RawPrice.market)
                .subquery()
            )

            # Join back to raw_price to retrieve the actual close values
            stmt = (
                select(RawPrice.symbol, RawPrice.market, RawPrice.close)
                .join(
                    max_date_sq,
                    (RawPrice.symbol == max_date_sq.c.symbol)
                    & (RawPrice.market == max_date_sq.c.market)
                    & (RawPrice.trade_date == max_date_sq.c.max_date),
                )
                .where(RawPrice.source == source)
            )

            for row in session.execute(stmt):
                key = (row.symbol, row.market)
                if key in result:
                    result[key] = float(row.close)

        return result
