from datetime import datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    asof_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    factor_name: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_value: Mapped[float | None] = mapped_column(Numeric(20, 8))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
