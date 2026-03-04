from datetime import datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class RawPrice(Base):
    __tablename__ = 'raw_price'
    __table_args__ = (
        UniqueConstraint('symbol', 'market', 'trade_date', 'source', name='uq_raw_price_key'),
        Index('ix_raw_price_market_symbol_trade_date', 'market', 'symbol', 'trade_date'),
        Index('ix_raw_price_quality_status', 'quality_status'),
        Index('ix_raw_price_ingested_at', 'ingested_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric(18, 6))
    high: Mapped[float | None] = mapped_column(Numeric(18, 6))
    low: Mapped[float | None] = mapped_column(Numeric(18, 6))
    close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[float | None] = mapped_column(Numeric(24, 6))
    adj_factor: Mapped[float | None] = mapped_column(Numeric(18, 8))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False, default='pending', server_default='pending')


class RawFundamental(Base):
    __tablename__ = 'raw_fundamental'
    __table_args__ = (
        UniqueConstraint('symbol', 'market', 'report_period', 'publish_date', 'source', name='uq_raw_fundamental_key'),
        Index('ix_raw_fundamental_market_symbol_report_period', 'market', 'symbol', 'report_period'),
        Index('ix_raw_fundamental_quality_status', 'quality_status'),
        Index('ix_raw_fundamental_ingested_at', 'ingested_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    report_period: Mapped[datetime] = mapped_column(Date, nullable=False)
    publish_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    roe: Mapped[float | None] = mapped_column(Numeric(18, 6))
    revenue: Mapped[float | None] = mapped_column(Numeric(24, 6))
    net_profit: Mapped[float | None] = mapped_column(Numeric(24, 6))
    debt_ratio: Mapped[float | None] = mapped_column(Numeric(18, 6))
    operating_cashflow: Mapped[float | None] = mapped_column(Numeric(24, 6))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False, default='pending', server_default='pending')


class RawMacro(Base):
    __tablename__ = 'raw_macro'
    __table_args__ = (
        UniqueConstraint('series_code', 'market', 'obs_date', 'source', name='uq_raw_macro_key'),
        Index('ix_raw_macro_market_series_code_obs_date', 'market', 'series_code', 'obs_date'),
        Index('ix_raw_macro_quality_status', 'quality_status'),
        Index('ix_raw_macro_ingested_at', 'ingested_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_code: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    obs_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(24, 8))
    frequency: Mapped[str | None] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality_status: Mapped[str] = mapped_column(String(16), nullable=False, default='pending', server_default='pending')


class DerivedFactor(Base):
    __tablename__ = 'derived_factors'
    __table_args__ = (
        UniqueConstraint('symbol', 'market', 'asof_date', 'factor_name', name='uq_derived_factor_key'),
        Index('ix_derived_factors_market_symbol_asof_date', 'market', 'symbol', 'asof_date'),
        Index('ix_derived_factors_factor_name_asof_date', 'factor_name', 'asof_date'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    asof_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    factor_name: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_value: Mapped[float | None] = mapped_column(Numeric(20, 8))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StrategyCard(Base):
    """Draft / active / paused / closed strategy card produced by 大呆子（策略官）.

    Human-filled fields (thesis, position_pct) are left NULL on creation and
    filled in after human review.  Auto-filled fields (valuation_note,
    entry_price, stop_loss_price, entry_date) are populated by CardGenerator.
    """
    __tablename__ = 'strategy_card'
    __table_args__ = (
        Index('ix_strategy_card_symbol_market', 'symbol', 'market'),
        Index('ix_strategy_card_status', 'status'),
        Index('ix_strategy_card_created_at', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    # Human-filled
    thesis: Mapped[str | None] = mapped_column(Text)
    position_pct: Mapped[float | None] = mapped_column(Numeric(6, 4))
    # Auto-filled by CardGenerator
    valuation_note: Mapped[str | None] = mapped_column(Text)
    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    entry_date: Mapped[datetime | None] = mapped_column(Date)
    stop_loss_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    # StrategyCard 2.0 fields (nullable for backward compatibility)
    industry: Mapped[str | None] = mapped_column(String(64))
    expected_cycle: Mapped[str | None] = mapped_column(String(32))
    valuation_anchor: Mapped[dict | None] = mapped_column(JSON)
    position_rules: Mapped[dict | None] = mapped_column(JSON)
    entry_rules: Mapped[dict | None] = mapped_column(JSON)
    exit_rules: Mapped[dict | None] = mapped_column(JSON)
    risk_rules: Mapped[dict | None] = mapped_column(JSON)
    review_cadence: Mapped[str | None] = mapped_column(String(16))
    rules_version: Mapped[int | None] = mapped_column(Integer, default=1, server_default='1')
    # Lifecycle
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='draft', server_default='draft')
    close_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TradeLog(Base):
    """Append-only record of actual buy / sell executions.

    Design: rows are NEVER deleted or updated — each trade is immutable once
    recorded.  Portfolio snapshots are computed by aggregating this log.
    card_id is a soft reference to strategy_card.id (no FK constraint so that
    ad-hoc trades without a strategy card can be recorded).
    """
    __tablename__ = 'trade_log'
    __table_args__ = (
        CheckConstraint("direction IN ('buy', 'sell')", name='ck_trade_log_direction'),
        Index('ix_trade_log_symbol_market_trade_date', 'symbol', 'market', 'trade_date'),
        Index('ix_trade_log_trade_date', 'trade_date'),
        Index('ix_trade_log_card_id', 'card_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    card_id: Mapped[int | None] = mapped_column(Integer)        # soft ref to strategy_card.id
    direction: Mapped[str] = mapped_column(String(8), nullable=False)   # 'buy' | 'sell'
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(24, 6), nullable=False)  # price * shares
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
