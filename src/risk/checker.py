"""Risk checker — 大善人（总监）风控检查层.

Evaluates a PortfolioSnapshot against configurable thresholds and returns a
RiskReport describing any violations found.

Checks
------
C1 — position_concentration
    Each position's market value (current_price × net_shares) must not exceed
    *max_position_pct* of the total portfolio market value.
    Severity: warning.
    Skipped when no position has a current_price (no market value available).

C2 — max_positions
    The number of open positions must not exceed *max_positions*.
    Severity: warning.

C3 — portfolio_drawdown
    Total unrealized PnL / total cost basis must not breach *-max_drawdown_pct*
    (i.e. portfolio must not be down more than *max_drawdown_pct* from cost).
    Severity: breach.
    Skipped when no position has an avg_cost (no cost basis computable).

Overall status
--------------
* 'ok'      — no violations
* 'warning' — at least one violation, all severity='warning'
* 'breach'  — at least one severity='breach' violation
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.types import PortfolioSnapshot, RiskReport, RiskViolation


class RiskChecker:
    """Evaluate portfolio risk constraints and return a RiskReport."""

    def check(
        self,
        portfolio: PortfolioSnapshot,
        max_position_pct: float = 0.20,
        max_positions: int = 10,
        max_drawdown_pct: float = 0.15,
    ) -> RiskReport:
        """Run all risk checks against *portfolio* and return a RiskReport.

        Parameters
        ----------
        portfolio:
            Point-in-time portfolio snapshot to evaluate.
        max_position_pct:
            Maximum fraction any single position may represent of total
            portfolio market value.  E.g. 0.20 = 20%.  (C1)
        max_positions:
            Maximum number of concurrent open positions allowed.  (C2)
        max_drawdown_pct:
            Maximum tolerable portfolio drawdown from cost basis before a
            breach is raised.  E.g. 0.15 = 15% loss triggers breach.  (C3)
        """
        violations: list[RiskViolation] = []
        positions = portfolio.positions
        total_positions = len(positions)

        # ── Derived aggregates ──────────────────────────────────────────────
        total_market_value: Optional[float] = None
        total_cost_basis: Optional[float] = None

        mv_sum = sum(
            p.current_price * p.net_shares
            for p in positions
            if p.current_price is not None
        )
        cb_sum = sum(
            p.avg_cost * p.net_shares
            for p in positions
            if p.avg_cost is not None
        )

        if mv_sum > 0:
            total_market_value = mv_sum
        if cb_sum > 0:
            total_cost_basis = cb_sum

        # Portfolio drawdown %
        portfolio_drawdown_pct: Optional[float] = None
        if total_cost_basis is not None and total_cost_basis > 0:
            pnl = portfolio.total_unrealized_pnl or 0.0
            portfolio_drawdown_pct = pnl / total_cost_basis

        # ── C1 — position concentration ─────────────────────────────────────
        if total_market_value is not None and total_market_value > 0:
            for p in positions:
                if p.current_price is None:
                    continue
                position_mv = p.current_price * p.net_shares
                concentration = position_mv / total_market_value
                if concentration > max_position_pct:
                    violations.append(RiskViolation(
                        check='position_concentration',
                        severity='warning',
                        symbol=p.symbol,
                        market=p.market,
                        current_value=round(concentration, 6),
                        threshold=max_position_pct,
                        message=(
                            f"{p.symbol}/{p.market} concentration "
                            f"{concentration:.1%} exceeds limit {max_position_pct:.1%}"
                        ),
                    ))

        # ── C2 — max positions ───────────────────────────────────────────────
        if total_positions > max_positions:
            violations.append(RiskViolation(
                check='max_positions',
                severity='warning',
                symbol=None,
                market=None,
                current_value=float(total_positions),
                threshold=float(max_positions),
                message=(
                    f"Open positions {total_positions} exceeds limit {max_positions}"
                ),
            ))

        # ── C3 — portfolio drawdown ──────────────────────────────────────────
        if (
            portfolio_drawdown_pct is not None
            and portfolio_drawdown_pct < -max_drawdown_pct
        ):
            violations.append(RiskViolation(
                check='portfolio_drawdown',
                severity='breach',
                symbol=None,
                market=None,
                current_value=round(portfolio_drawdown_pct, 6),
                threshold=-max_drawdown_pct,
                message=(
                    f"Portfolio drawdown {portfolio_drawdown_pct:.1%} "
                    f"breaches limit -{max_drawdown_pct:.1%}"
                ),
            ))

        # ── Overall status ───────────────────────────────────────────────────
        if not violations:
            status = 'ok'
        elif any(v.severity == 'breach' for v in violations):
            status = 'breach'
        else:
            status = 'warning'

        return RiskReport(
            asof=portfolio.snapshot_date,
            status=status,
            violations=violations,
            total_positions=total_positions,
            total_cost_basis=total_cost_basis,
            total_market_value=total_market_value,
            portfolio_drawdown_pct=portfolio_drawdown_pct,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
