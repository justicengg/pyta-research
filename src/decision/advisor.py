"""Decision advisor — 大善人（总监）决策层.

Evaluates the current portfolio state against active/draft strategy cards and
produces a DecisionReport with per-symbol action recommendations.

Decision rules (thresholds configurable via settings / method params)
---------------------------------------------------------------------
For open positions:
  R1 — stop_loss_hit     current_price ≤ stop_loss_price  → action='exit'
  R2 — concentration     position flagged in RiskReport    → action='trim'
  R3 — default                                             → action='hold'

For strategy cards with no open position:
  R4 — card_active       card.status == 'active'           → action='enter'
  R5 — card_draft        card.status == 'draft'            → action='watch'

Rule priority: R1 > R2 > R3  (stop-loss always beats trim)
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import StrategyCard
from src.portfolio.tracker import PortfolioTracker
from src.risk.checker import RiskChecker
from src.types import DecisionAdvice, DecisionReport


class DecisionAdvisor:
    """Produce a DecisionReport by evaluating portfolio + strategy cards."""

    def evaluate(
        self,
        asof: date,
        session: Session,
        price_source_cn: str = 'baostock',
        price_source_us: str = 'yfinance',
        max_position_pct: float = 0.20,
        max_positions: int = 10,
        max_drawdown_pct: float = 0.15,
    ) -> DecisionReport:
        """Evaluate the portfolio and return a DecisionReport.

        Parameters
        ----------
        asof:
            Cut-off date (inclusive). Trades and prices after this date are
            excluded.
        session:
            SQLAlchemy session to query against.
        price_source_cn / price_source_us:
            Preferred ``raw_price.source`` per market, forwarded to
            ``PortfolioTracker``.
        max_position_pct / max_positions / max_drawdown_pct:
            Risk thresholds forwarded to ``RiskChecker``.
        """
        # 1. Portfolio snapshot
        portfolio = PortfolioTracker().snapshot(
            asof=asof,
            session=session,
            price_source_cn=price_source_cn,
            price_source_us=price_source_us,
        )

        # 2. Risk report (feeds concentration violations into R2)
        risk_report = RiskChecker().check(
            portfolio=portfolio,
            max_position_pct=max_position_pct,
            max_positions=max_positions,
            max_drawdown_pct=max_drawdown_pct,
        )

        # 3. Fetch active / draft strategy cards
        stmt = (
            select(StrategyCard)
            .where(StrategyCard.status.in_(['draft', 'active']))
        )
        cards = list(session.scalars(stmt).all())

        # 4. Index open positions by (symbol, market)
        position_index = {(p.symbol, p.market): p for p in portfolio.positions}

        # 5. Symbols flagged with concentration breach (C1, severity=warning)
        concentration_keys = {
            (v.symbol, v.market)
            for v in risk_report.violations
            if v.check == 'position_concentration'
        }

        # 6. Card index: (symbol, market) → StrategyCard
        #    When both active and draft exist, prefer active.
        card_index: dict[tuple[str, str], StrategyCard] = {}
        for card in sorted(cards, key=lambda c: 0 if c.status == 'active' else 1):
            key = (card.symbol, card.market)
            if key not in card_index:
                card_index[key] = card

        advice: list[DecisionAdvice] = []

        # 7. Evaluate every open position (R1 / R2 / R3)
        for key, pos in position_index.items():
            card = card_index.get(key)
            stop_loss_price = (
                float(card.stop_loss_price)
                if card and card.stop_loss_price is not None
                else None
            )

            # R1 — stop-loss hit (highest priority)
            if (
                stop_loss_price is not None
                and pos.current_price is not None
                and pos.current_price <= stop_loss_price
            ):
                action, reason = 'exit', 'stop_loss_hit'

            # R2 — concentration breach → trim
            elif key in concentration_keys:
                action, reason = 'trim', 'concentration_breach'

            # R3 — default hold
            else:
                action, reason = 'hold', 'within_limits'

            advice.append(DecisionAdvice(
                symbol=pos.symbol,
                market=pos.market,
                action=action,
                reason=reason,
                net_shares=pos.net_shares,
                avg_cost=pos.avg_cost,
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_pct=pos.unrealized_pnl_pct,
                card_id=card.id if card else None,
                card_status=card.status if card else None,
                stop_loss_price=stop_loss_price,
            ))

        # 8. Evaluate cards with no open position (R4 / R5)
        for key, card in card_index.items():
            if key in position_index:
                continue  # already handled above

            if card.status == 'active':
                action, reason = 'enter', 'card_active'
            else:
                action, reason = 'watch', 'card_draft'

            advice.append(DecisionAdvice(
                symbol=card.symbol,
                market=card.market,
                action=action,
                reason=reason,
                net_shares=None,
                avg_cost=None,
                current_price=None,
                unrealized_pnl=None,
                unrealized_pnl_pct=None,
                card_id=card.id,
                card_status=card.status,
                stop_loss_price=(
                    float(card.stop_loss_price)
                    if card.stop_loss_price is not None
                    else None
                ),
            ))

        # 9. Aggregate action counts
        counts: dict[str, int] = {a: 0 for a in ('exit', 'trim', 'hold', 'enter', 'watch')}
        for a in advice:
            counts[a.action] += 1

        return DecisionReport(
            asof=asof,
            advice=advice,
            risk_status=risk_report.status,
            risk_violations=len(risk_report.violations),
            total_positions=len(portfolio.positions),
            exit_count=counts['exit'],
            trim_count=counts['trim'],
            hold_count=counts['hold'],
            enter_count=counts['enter'],
            watch_count=counts['watch'],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
