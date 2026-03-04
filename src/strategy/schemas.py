"""Pydantic schemas for StrategyCard 2.0 rule payloads."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpectedCycle(str, Enum):
    short = 'short'
    medium = 'medium'
    long = 'long'


class ReviewCadence(str, Enum):
    weekly = 'weekly'
    monthly = 'monthly'
    quarterly = 'quarterly'


class ValuationAnchor(BaseModel):
    model_config = ConfigDict(extra='forbid')

    core_metric: str = Field(min_length=1)
    fair_low: float
    fair_high: float
    extreme_low: float | None = None
    extreme_high: float | None = None

    @field_validator('fair_high')
    @classmethod
    def validate_fair_band(cls, v: float, info) -> float:
        low = info.data.get('fair_low')
        if low is not None and v < low:
            raise ValueError('fair_high must be >= fair_low')
        return v

    @field_validator('extreme_high')
    @classmethod
    def validate_extreme_high(cls, v: float | None, info) -> float | None:
        if v is None:
            return None
        fair_high = info.data.get('fair_high')
        if fair_high is not None and v < fair_high:
            raise ValueError('extreme_high must be >= fair_high')
        return v

    @field_validator('extreme_low')
    @classmethod
    def validate_extreme_low(cls, v: float | None, info) -> float | None:
        if v is None:
            return None
        fair_low = info.data.get('fair_low')
        if fair_low is not None and v > fair_low:
            raise ValueError('extreme_low must be <= fair_low')
        return v


class TierRule(BaseModel):
    model_config = ConfigDict(extra='forbid')

    trigger: str = Field(min_length=1)
    pct: float = Field(ge=0.0, le=1.0)


class PositionRules(BaseModel):
    model_config = ConfigDict(extra='forbid')

    initial_pct: float = Field(ge=0.0, le=1.0)
    add_tiers: list[TierRule] = Field(default_factory=list)
    reduce_tiers: list[TierRule] = Field(default_factory=list)
    max_pct: float = Field(ge=0.0, le=1.0)
    min_pct: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator('max_pct')
    @classmethod
    def validate_max_pct(cls, v: float, info) -> float:
        min_pct = info.data.get('min_pct')
        if min_pct is not None and v < min_pct:
            raise ValueError('max_pct must be >= min_pct')
        return v


class EntryRules(BaseModel):
    model_config = ConfigDict(extra='forbid')

    trigger_conditions: list[str] = Field(default_factory=list)
    filter_conditions: list[str] = Field(default_factory=list)


class ThresholdRule(BaseModel):
    model_config = ConfigDict(extra='forbid')

    metric: str = Field(min_length=1)
    threshold: float


class StopLossRule(BaseModel):
    model_config = ConfigDict(extra='forbid')

    method: str = Field(min_length=1)
    value: float = Field(gt=0.0)


class ExitRules(BaseModel):
    model_config = ConfigDict(extra='forbid')

    take_profit: ThresholdRule | None = None
    stop_loss: StopLossRule | None = None
    thesis_break: str | None = None


class RiskRules(BaseModel):
    model_config = ConfigDict(extra='forbid')

    stock_max_loss_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    stock_max_position_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    sector_max_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    portfolio_max_drawdown_pct: float | None = Field(default=None, ge=0.0, le=1.0)

