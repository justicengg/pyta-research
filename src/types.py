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
