"""Unit tests for src/risk/checker.py — RiskChecker.

Test matrix
-----------
TestRiskCheckerOk              — happy-path: no violations
TestPositionConcentration      — C1 position concentration (warning)
TestMaxPositions               — C2 max open positions (warning)
TestPortfolioDrawdown          — C3 portfolio drawdown (breach)
TestCombinedViolations         — multiple checks fire simultaneously
TestRiskReportJson             — report_to_json round-trip
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from src.risk.checker import RiskChecker
from src.risk.report import report_to_json
from src.types import PortfolioSnapshot, PositionSnapshot

# ── helpers ──────────────────────────────────────────────────────────────────

ASOF = date(2026, 3, 1)


def _snap(positions: list[PositionSnapshot], total_pnl: float | None = None) -> PortfolioSnapshot:
    computed = (
        sum(p.unrealized_pnl for p in positions if p.unrealized_pnl is not None)
        if total_pnl is None
        else total_pnl
    )
    return PortfolioSnapshot(
        snapshot_date=ASOF,
        generated_at='2026-03-01T00:00:00+00:00',
        positions=positions,
        total_unrealized_pnl=computed if positions else None,
    )


def _pos(
    symbol: str,
    market: str = 'CN',
    net_shares: float = 100.0,
    avg_cost: float | None = 10.0,
    current_price: float | None = 11.0,
) -> PositionSnapshot:
    pnl = (
        (current_price - avg_cost) * net_shares
        if current_price is not None and avg_cost is not None
        else None
    )
    pnl_pct = (
        (current_price - avg_cost) / avg_cost
        if current_price is not None and avg_cost is not None
        else None
    )
    return PositionSnapshot(
        symbol=symbol,
        market=market,
        net_shares=net_shares,
        avg_cost=avg_cost,
        current_price=current_price,
        unrealized_pnl=pnl,
        unrealized_pnl_pct=pnl_pct,
    )


CHECKER = RiskChecker()


# ── TestRiskCheckerOk ─────────────────────────────────────────────────────────

class TestRiskCheckerOk:
    def test_empty_portfolio_is_ok(self):
        report = CHECKER.check(_snap([]))
        assert report.status == 'ok'
        assert report.violations == []
        assert report.total_positions == 0
        assert report.total_cost_basis is None
        assert report.total_market_value is None
        assert report.portfolio_drawdown_pct is None

    def test_single_position_within_limits_is_ok(self):
        # 1 position at cost 10, price 11 → no drawdown; disable C1 with high threshold
        report = CHECKER.check(
            _snap([_pos('A', net_shares=100, avg_cost=10, current_price=11)]),
            max_position_pct=1.0,  # C1 disabled: single position is always 100%
        )
        assert report.status == 'ok'
        assert report.violations == []

    def test_two_equal_positions_no_violations(self):
        # Each position is 50% of portfolio → within default 20%? No, 50% > 20%
        # So use 3 positions with equal weight ~33% → still over 20%
        # Use 6 positions with equal weight ~17% → under 20%
        positions = [_pos(str(i), net_shares=100, avg_cost=10, current_price=10) for i in range(6)]
        report = CHECKER.check(_snap(positions, total_pnl=0.0))
        assert report.status == 'ok'
        assert not any(v.check == 'position_concentration' for v in report.violations)

    def test_portfolio_with_profit_no_violation(self):
        # Large profit → drawdown is positive, no C3 violation; disable C1 (single pos)
        pos = _pos('X', net_shares=100, avg_cost=10, current_price=20)  # +100% return
        report = CHECKER.check(_snap([pos]), max_position_pct=1.0)
        assert report.status == 'ok'
        assert report.portfolio_drawdown_pct is not None
        assert report.portfolio_drawdown_pct > 0

    def test_aggregates_computed_correctly(self):
        # Two positions: A cost=10 price=12 shares=100; B cost=5 price=6 shares=200
        a = _pos('A', net_shares=100, avg_cost=10, current_price=12)
        b = _pos('B', net_shares=200, avg_cost=5, current_price=6)
        snap = _snap([a, b])
        report = CHECKER.check(snap, max_position_pct=0.99)  # disable C1
        assert report.total_cost_basis == pytest.approx(10 * 100 + 5 * 200)   # 2000
        assert report.total_market_value == pytest.approx(12 * 100 + 6 * 200) # 2400
        assert report.portfolio_drawdown_pct == pytest.approx(400 / 2000)     # +20%


# ── TestPositionConcentration ─────────────────────────────────────────────────

class TestPositionConcentration:
    def test_single_position_is_100pct_concentration(self):
        # One position = 100% of portfolio → exceeds any reasonable limit
        report = CHECKER.check(
            _snap([_pos('A', net_shares=100, avg_cost=10, current_price=10)]),
            max_position_pct=0.20,
        )
        assert report.status == 'warning'
        violations = [v for v in report.violations if v.check == 'position_concentration']
        assert len(violations) == 1
        assert violations[0].symbol == 'A'
        assert violations[0].severity == 'warning'
        assert violations[0].current_value == pytest.approx(1.0)
        assert violations[0].threshold == 0.20

    def test_one_heavy_position_among_many(self):
        # One position with 50% of value, rest spread across 5 with 10% each
        heavy = _pos('HEAVY', net_shares=500, avg_cost=10, current_price=10)  # value = 5000
        others = [_pos(str(i), net_shares=100, avg_cost=10, current_price=10) for i in range(5)]
        # total market value = 5000 + 5*1000 = 10000; HEAVY = 50%
        snap = _snap([heavy] + others, total_pnl=0.0)
        report = CHECKER.check(snap, max_position_pct=0.20)
        violations = [v for v in report.violations if v.check == 'position_concentration']
        assert len(violations) == 1
        assert violations[0].symbol == 'HEAVY'
        assert violations[0].current_value == pytest.approx(0.5)

    def test_exactly_at_threshold_no_violation(self):
        # Two equal positions → each is exactly 50%. threshold = 0.51 → no violation
        a = _pos('A', net_shares=100, avg_cost=10, current_price=10)
        b = _pos('B', net_shares=100, avg_cost=10, current_price=10)
        snap = _snap([a, b], total_pnl=0.0)
        report = CHECKER.check(snap, max_position_pct=0.51)  # 51% threshold > 50% actual
        assert not any(v.check == 'position_concentration' for v in report.violations)

    def test_no_price_positions_skip_concentration(self):
        # Position with no current_price → cannot compute market value → C1 skipped
        pos = _pos('A', current_price=None)
        report = CHECKER.check(_snap([pos]))
        assert not any(v.check == 'position_concentration' for v in report.violations)
        assert report.total_market_value is None


# ── TestMaxPositions ──────────────────────────────────────────────────────────

class TestMaxPositions:
    def test_positions_equal_to_limit_no_violation(self):
        positions = [_pos(str(i)) for i in range(5)]
        report = CHECKER.check(_snap(positions, total_pnl=0.0), max_positions=5)
        assert not any(v.check == 'max_positions' for v in report.violations)

    def test_positions_exceed_limit_warning(self):
        positions = [_pos(str(i)) for i in range(11)]
        snap = _snap(positions, total_pnl=0.0)
        report = CHECKER.check(snap, max_positions=10)
        violations = [v for v in report.violations if v.check == 'max_positions']
        assert len(violations) == 1
        assert violations[0].severity == 'warning'
        assert violations[0].current_value == 11.0
        assert violations[0].threshold == 10.0
        assert violations[0].symbol is None

    def test_max_positions_status_is_warning_not_breach(self):
        positions = [_pos(str(i)) for i in range(11)]
        snap = _snap(positions, total_pnl=0.0)
        report = CHECKER.check(snap, max_positions=10, max_drawdown_pct=0.15)
        assert report.status == 'warning'


# ── TestPortfolioDrawdown ─────────────────────────────────────────────────────

class TestPortfolioDrawdown:
    def test_drawdown_exceeds_threshold_is_breach(self):
        # cost=10, price=8 → -20% drawdown; threshold=15% → breach
        pos = _pos('A', net_shares=100, avg_cost=10, current_price=8)
        snap = _snap([pos])
        report = CHECKER.check(snap, max_drawdown_pct=0.15)
        violations = [v for v in report.violations if v.check == 'portfolio_drawdown']
        assert len(violations) == 1
        assert violations[0].severity == 'breach'
        assert violations[0].current_value == pytest.approx(-0.2)
        assert violations[0].threshold == -0.15
        assert report.status == 'breach'

    def test_drawdown_exactly_at_threshold_no_breach(self):
        # cost=10, price=8.5 → -15% drawdown; threshold=15% → NOT breached (strictly less)
        pos = _pos('A', net_shares=100, avg_cost=10, current_price=8.5)
        snap = _snap([pos])
        report = CHECKER.check(snap, max_drawdown_pct=0.15)
        assert not any(v.check == 'portfolio_drawdown' for v in report.violations)

    def test_no_avg_cost_skips_drawdown_check(self):
        # Position with no avg_cost → no cost basis → C3 skipped
        pos = _pos('A', avg_cost=None, current_price=10)
        report = CHECKER.check(_snap([pos]))
        assert report.total_cost_basis is None
        assert report.portfolio_drawdown_pct is None
        assert not any(v.check == 'portfolio_drawdown' for v in report.violations)


# ── TestCombinedViolations ────────────────────────────────────────────────────

class TestCombinedViolations:
    def test_breach_overrides_warning_in_status(self):
        # C2 (warning) + C3 (breach) → overall status should be 'breach'
        positions = [_pos(str(i), avg_cost=10, current_price=8) for i in range(11)]
        snap = _snap(positions, total_pnl=-200.0 * 11)
        # total_cost = 10*100*11 = 11000; total_pnl = -2200 → -20% drawdown
        # Rebuild properly
        pnl_total = sum(p.unrealized_pnl for p in positions if p.unrealized_pnl is not None)
        snap2 = PortfolioSnapshot(
            snapshot_date=ASOF,
            generated_at='2026-03-01T00:00:00+00:00',
            positions=positions,
            total_unrealized_pnl=pnl_total,
        )
        report = CHECKER.check(snap2, max_positions=10, max_drawdown_pct=0.15)
        assert report.status == 'breach'
        checks = {v.check for v in report.violations}
        assert 'max_positions' in checks
        assert 'portfolio_drawdown' in checks

    def test_report_metadata_always_present(self):
        report = CHECKER.check(_snap([]))
        assert report.asof == ASOF
        assert report.generated_at  # non-empty ISO string
        assert report.total_positions == 0


# ── TestRiskReportJson ────────────────────────────────────────────────────────

class TestRiskReportJson:
    def test_json_round_trip_ok_report(self):
        report = CHECKER.check(_snap([]))
        payload = json.loads(report_to_json(report))
        assert payload['status'] == 'ok'
        assert payload['violations'] == []
        assert payload['asof'] == ASOF.isoformat()
        assert 'generated_at' in payload

    def test_json_round_trip_with_violation(self):
        pos = _pos('A', net_shares=100, avg_cost=10, current_price=8)
        snap = _snap([pos])
        report = CHECKER.check(snap, max_drawdown_pct=0.15)
        payload = json.loads(report_to_json(report))
        assert payload['status'] == 'breach'
        assert len(payload['violations']) == 2  # C1 (concentration) + C3 (drawdown)
        checks = {v['check'] for v in payload['violations']}
        assert 'portfolio_drawdown' in checks
        assert 'position_concentration' in checks
