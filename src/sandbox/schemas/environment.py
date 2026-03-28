"""Environment-layer schema models for secondary-market sandbox."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EnvironmentType = Literal[
    "geopolitics",
    "macro_policy",
    "market_sentiment",
    "fundamentals",
    "alternative_data",
]
SignalDirection = Literal["positive", "negative", "mixed", "neutral"]
TimeHorizon = Literal["intraday", "short_term", "mid_term", "long_term"]
RiskTone = Literal["risk_on", "risk_off", "mixed", "neutral"]
EnvironmentStatus = Literal["idle", "active", "cooling"]
EvidenceKind = Literal["quote", "metric", "event"]


class EnvironmentEvidence(BaseModel):
    kind: EvidenceKind
    value: str


class NormalizedSignal(BaseModel):
    id: str
    message_id: str
    environment_type: EnvironmentType
    title: str
    summary: str
    direction: SignalDirection
    strength: int = Field(ge=1, le=5)
    horizon: TimeHorizon
    related_symbols: list[str] = Field(default_factory=list)
    related_markets: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    detected_at: datetime
    expires_at: datetime | None = None
    evidence: list[EnvironmentEvidence] = Field(default_factory=list)


class EnvironmentBucket(BaseModel):
    type: EnvironmentType
    display_name: str
    active_signals: list[NormalizedSignal] = Field(default_factory=list)
    dominant_direction: SignalDirection = "neutral"
    aggregate_strength: int = 0
    last_updated_at: datetime | None = None
    status: EnvironmentStatus = "idle"


class EnvironmentState(BaseModel):
    sandbox_id: UUID | None = None
    symbol: str | None = None
    market: str | None = None
    buckets: list[EnvironmentBucket] = Field(default_factory=list)
    global_risk_tone: RiskTone = "neutral"
    updated_at: datetime
    version: int = 1
