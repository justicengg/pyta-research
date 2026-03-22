"""Canonical security data schema — the single internal data model all agents consume.

Every external data source (yfinance, Alpha Vantage, customer Excel, etc.) maps
to this schema before being passed to sandbox agents.  Non-standard fields go
into raw_payload so nothing is ever silently dropped.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PriceSnapshot(BaseModel):
    """Latest price data — always real-time or end-of-day."""
    current: float | None = None        # 最新价
    prev_close: float | None = None     # 前收盘价
    open: float | None = None           # 今开盘
    high_52w: float | None = None       # 52 周高
    low_52w: float | None = None        # 52 周低
    change_1d_pct: float | None = None  # 日涨跌幅 %
    change_5d_pct: float | None = None  # 5 日涨跌幅 %
    volume: int | None = None           # 今日成交量
    avg_volume_10d: int | None = None   # 10 日均量


class Fundamentals(BaseModel):
    """Core fundamental indicators."""
    market_cap: float | None = None      # 市值（美元）
    pe_ratio: float | None = None        # 市盈率 TTM
    forward_pe: float | None = None      # 预期市盈率
    pb_ratio: float | None = None        # 市净率
    eps_ttm: float | None = None         # EPS TTM
    revenue_ttm: float | None = None     # 营收 TTM（美元）
    revenue_growth: float | None = None  # 营收同比增速
    gross_margin: float | None = None    # 毛利率
    debt_to_equity: float | None = None  # 负债权益比
    dividend_yield: float | None = None  # 股息率


class CanonicalSecurityData(BaseModel):
    """Single unified view of a security — consumed by all sandbox agents."""
    symbol: str
    market: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None

    price: PriceSnapshot = Field(default_factory=PriceSnapshot)
    fundamentals: Fundamentals = Field(default_factory=Fundamentals)

    fetched_at: datetime
    source: str = "yfinance"

    # Non-canonical fields from the upstream API — never discarded
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def to_agent_context(self) -> dict[str, Any]:
        """Return a compact dict suitable for injection into agent prompts.

        Keeps only fields with real values so the prompt doesn't include
        a wall of nulls.
        """
        p = self.price
        f = self.fundamentals

        price_block: dict[str, Any] = {}
        if p.current is not None:
            price_block["current"] = round(p.current, 2)
        if p.change_1d_pct is not None:
            price_block["change_1d_pct"] = round(p.change_1d_pct, 2)
        if p.change_5d_pct is not None:
            price_block["change_5d_pct"] = round(p.change_5d_pct, 2)
        if p.high_52w is not None:
            price_block["high_52w"] = round(p.high_52w, 2)
        if p.low_52w is not None:
            price_block["low_52w"] = round(p.low_52w, 2)
        if p.volume is not None:
            price_block["volume"] = p.volume
        if p.avg_volume_10d is not None:
            price_block["avg_volume_10d"] = p.avg_volume_10d

        fund_block: dict[str, Any] = {}
        if f.market_cap is not None:
            fund_block["market_cap_bn"] = round(f.market_cap / 1e9, 1)
        if f.pe_ratio is not None:
            fund_block["pe_ttm"] = round(f.pe_ratio, 1)
        if f.forward_pe is not None:
            fund_block["pe_forward"] = round(f.forward_pe, 1)
        if f.pb_ratio is not None:
            fund_block["pb"] = round(f.pb_ratio, 2)
        if f.revenue_ttm is not None:
            fund_block["revenue_ttm_bn"] = round(f.revenue_ttm / 1e9, 1)
        if f.revenue_growth is not None:
            fund_block["revenue_growth_pct"] = round(f.revenue_growth * 100, 1)
        if f.gross_margin is not None:
            fund_block["gross_margin_pct"] = round(f.gross_margin * 100, 1)
        if f.eps_ttm is not None:
            fund_block["eps_ttm"] = round(f.eps_ttm, 2)
        if f.debt_to_equity is not None:
            fund_block["debt_to_equity"] = round(f.debt_to_equity, 2)

        result: dict[str, Any] = {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "currency": self.currency,
            "data_as_of": self.fetched_at.strftime("%Y-%m-%d %H:%M UTC"),
            "source": self.source,
        }
        if price_block:
            result["price"] = price_block
        if fund_block:
            result["fundamentals"] = fund_block

        return result
