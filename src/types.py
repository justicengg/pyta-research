from dataclasses import dataclass
from datetime import date


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
