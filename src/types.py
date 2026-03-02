from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MarketBarRecord:
    symbol: str
    market: str
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    adj_factor: float | None
    source: str


@dataclass
class FundamentalRecord:
    symbol: str
    market: str
    report_period: date
    publish_date: date
    roe: float | None
    revenue: float | None
    net_profit: float | None
    debt_ratio: float | None
    operating_cashflow: float | None
    source: str


@dataclass
class MacroRecord:
    series_code: str
    market: str
    obs_date: date
    value: float | None
    frequency: str | None
    source: str


@dataclass
class StrategyCardSpec:
    """Lightweight spec passed between CardGenerator and session helpers.

    Human-filled fields (thesis, position_pct) are None on creation;
    auto-filled fields are populated by CardGenerator.
    Status lifecycle: draft → active → closed.
    """
    symbol: str
    market: str
    # Auto-filled
    valuation_note: Optional[str]
    entry_price: Optional[float]
    entry_date: Optional[date]
    stop_loss_price: Optional[float]
    # Human-filled (left None in generated draft)
    thesis: Optional[str] = None
    position_pct: Optional[float] = None
    status: str = 'draft'
    close_reason: Optional[str] = None


@dataclass
class PositionSnapshot:
    """Current holding for a single (symbol, market) as of snapshot_date."""
    symbol: str
    market: str
    net_shares: float               # buy_shares - sell_shares
    avg_cost: Optional[float]       # weighted average buy price
    current_price: Optional[float]  # latest close from raw_price
    unrealized_pnl: Optional[float]     # (current_price - avg_cost) * net_shares
    unrealized_pnl_pct: Optional[float] # (current_price - avg_cost) / avg_cost


@dataclass
class PortfolioSnapshot:
    """Aggregate portfolio state at snapshot_date."""
    snapshot_date: date
    generated_at: str               # ISO-8601 timestamp
    positions: list[PositionSnapshot]
    total_unrealized_pnl: Optional[float]


@dataclass
class DecisionAdvice:
    """Recommendation for a single symbol — open position or pending strategy card."""
    symbol: str
    market: str
    action: str                      # 'hold' | 'trim' | 'exit' | 'enter' | 'watch'
    reason: str                      # machine-readable reason code
    # Position info (None when symbol has no open position)
    net_shares: Optional[float]
    avg_cost: Optional[float]
    current_price: Optional[float]
    unrealized_pnl: Optional[float]
    unrealized_pnl_pct: Optional[float]
    # Strategy card info (None when no matching card)
    card_id: Optional[int]
    card_status: Optional[str]       # 'draft' | 'active' | None
    stop_loss_price: Optional[float]


@dataclass
class DecisionReport:
    """Aggregated decision recommendations produced by DecisionAdvisor."""
    asof: date
    advice: list['DecisionAdvice']
    risk_status: str                 # from RiskReport: 'ok' | 'warning' | 'breach'
    risk_violations: int
    total_positions: int
    exit_count: int
    trim_count: int
    hold_count: int
    enter_count: int
    watch_count: int
    generated_at: str                # ISO-8601 UTC timestamp


@dataclass
class RiskViolation:
    """A single portfolio risk constraint violation."""
    check: str                  # 'position_concentration' | 'max_positions' | 'portfolio_drawdown'
    severity: str               # 'warning' | 'breach'
    symbol: Optional[str]       # set for per-position checks, None for portfolio-level
    market: Optional[str]       # set for per-position checks, None for portfolio-level
    current_value: float        # measured value (e.g. 0.25 for 25% concentration)
    threshold: float            # configured limit (e.g. 0.20 for 20%)
    message: str


@dataclass
class RiskReport:
    """Portfolio-level risk check results produced by RiskChecker."""
    asof: date
    status: str                          # 'ok' | 'warning' | 'breach'
    violations: list['RiskViolation']
    total_positions: int
    total_cost_basis: Optional[float]    # Σ(avg_cost × net_shares)
    total_market_value: Optional[float]  # Σ(current_price × net_shares)
    portfolio_drawdown_pct: Optional[float]  # negative = loss from cost basis
    generated_at: str                    # ISO-8601 UTC timestamp


@dataclass
class QualityIssue:
    rule: str
    severity: str
    table: str
    row_key: str
    message: str


@dataclass
class QualityReport:
    table: str
    run_date: str
    total_rows: int
    issue_count: int
    issues: list[QualityIssue]
