"""Deterministic Layer-1 environment classification and normalization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.sandbox.schemas.environment import EnvironmentBucket, EnvironmentEvidence, EnvironmentState, NormalizedSignal

ENVIRONMENT_LABELS = {
    "geopolitics": "地缘政治",
    "macro_policy": "宏观政策",
    "market_sentiment": "市场情绪",
    "fundamentals": "公司基本面",
    "alternative_data": "另类数据",
}

ENVIRONMENT_ORDER = [
    "geopolitics",
    "macro_policy",
    "market_sentiment",
    "fundamentals",
    "alternative_data",
]

KEYWORD_RULES: dict[str, list[str]] = {
    "geopolitics": ["tariff", "sanction", "war", "geopolit", "出口", "制裁", "关税", "冲突", "地缘"],
    "macro_policy": ["fed", "fomc", "rate", "cpi", "ppi", "policy", "宏观", "利率", "降息", "加息", "监管", "政策"],
    "market_sentiment": ["sentiment", "fear", "greed", "panic", "social", "情绪", "舆情", "热度", "恐慌"],
    "fundamentals": ["earnings", "revenue", "margin", "guidance", "财报", "利润", "收入", "基本面", "订单"],
    "alternative_data": ["download", "traffic", "hiring", "satellite", "另类", "下载量", "流量", "招聘", "渠道"],
}


def build_environment_state(
    *,
    ticker: str | None,
    market: str | None,
    events: list[dict[str, Any]],
) -> EnvironmentState:
    signals: list[NormalizedSignal] = []
    for event in events:
        signals.extend(_normalize_event_to_signals(event, ticker, market))

    buckets = [_build_bucket(environment_type, signals) for environment_type in ENVIRONMENT_ORDER]
    return EnvironmentState(
        symbol=ticker,
        market=market,
        buckets=buckets,
        global_risk_tone=_derive_global_risk_tone(buckets),
        updated_at=datetime.now(timezone.utc),
        version=1,
    )


def _normalize_event_to_signals(
    event: dict[str, Any],
    ticker: str | None,
    market: str | None,
) -> list[NormalizedSignal]:
    categories = _classify_event(event)
    content = str(event.get("content") or "").strip()
    title = content.splitlines()[0].strip() if content else str(event.get("event_type") or "input_event")
    timestamp = _coerce_datetime(event.get("timestamp"))
    symbol = event.get("symbol") or ticker
    market_label = event.get("market") or market

    return [
        NormalizedSignal(
            id=f"{event.get('event_id', 'event')}:{environment_type}:{index}",
            message_id=str(event.get("event_id") or "event"),
            environment_type=environment_type,
            title=title,
            summary=content or title,
            direction=_derive_direction(event),
            strength=_derive_strength(event),
            horizon=_derive_horizon(event),
            related_symbols=_compact_strings([symbol]),
            related_markets=_compact_strings([market_label]),
            entities=_compact_strings([symbol, event.get("source")]),
            tags=categories,
            detected_at=timestamp,
            evidence=[EnvironmentEvidence(kind="event", value=title)],
        )
        for index, environment_type in enumerate(categories)
    ]


def _classify_event(event: dict[str, Any]) -> list[str]:
    explicit_dimension = str(event.get("metadata", {}).get("dimension") or event.get("event_type") or "").lower()
    content = f"{event.get('event_type', '')} {event.get('content', '')}".lower()
    matches: set[str] = set()

    if "geo" in explicit_dimension:
        matches.add("geopolitics")
    if "macro" in explicit_dimension or "policy" in explicit_dimension:
        matches.add("macro_policy")
    if "sentiment" in explicit_dimension or "social" in explicit_dimension:
        matches.add("market_sentiment")
    if "fundamental" in explicit_dimension or "earning" in explicit_dimension:
        matches.add("fundamentals")
    if "alternative" in explicit_dimension or explicit_dimension.startswith("alt"):
        matches.add("alternative_data")

    for environment_type, keywords in KEYWORD_RULES.items():
        if any(keyword in content for keyword in keywords):
            matches.add(environment_type)

    if not matches:
        matches.add("market_sentiment")

    return [environment_type for environment_type in ENVIRONMENT_ORDER if environment_type in matches]


def _derive_direction(event: dict[str, Any]) -> str:
    explicit = str(event.get("metadata", {}).get("impact_direction") or "").lower()
    if explicit in {"positive", "negative", "neutral"}:
        return explicit
    content = str(event.get("content") or "").lower()
    if any(token in content for token in ["beat", "surge", "expand", "upgrade", "positive", "improve", "利好", "回暖", "增长", "超预期"]):
        return "positive"
    if any(token in content for token in ["cut", "downgrade", "panic", "risk-off", "negative", "miss", "利空", "下滑", "承压", "鹰派"]):
        return "negative"
    return "neutral"


def _derive_strength(event: dict[str, Any]) -> int:
    explicit = event.get("metadata", {}).get("impact_strength")
    try:
        numeric = float(explicit)
    except (TypeError, ValueError):
        numeric = 0.0
    if numeric >= 0.85:
        return 5
    if numeric >= 0.65:
        return 4
    if numeric >= 0.45:
        return 3
    if numeric >= 0.2:
        return 2

    content_length = len(str(event.get("content") or ""))
    if content_length > 320:
        return 4
    if content_length > 160:
        return 3
    return 2


def _derive_horizon(event: dict[str, Any]) -> str:
    content = f"{event.get('event_type', '')} {event.get('content', '')}".lower()
    if any(token in content for token in ["intraday", "today", "盘中", "今日", "短线", "次日"]):
        return "intraday"
    if any(token in content for token in ["week", "short", "短期", "几天", "几周"]):
        return "short_term"
    if any(token in content for token in ["quarter", "earnings", "财报", "季度", "中期"]):
        return "mid_term"
    return "long_term"


def _build_bucket(environment_type: str, signals: list[NormalizedSignal]) -> EnvironmentBucket:
    active_signals = [signal for signal in signals if signal.environment_type == environment_type]
    if not active_signals:
        return EnvironmentBucket(type=environment_type, display_name=ENVIRONMENT_LABELS[environment_type])

    return EnvironmentBucket(
        type=environment_type,
        display_name=ENVIRONMENT_LABELS[environment_type],
        active_signals=active_signals,
        dominant_direction=_dominant_direction(active_signals),
        aggregate_strength=sum(signal.strength for signal in active_signals),
        last_updated_at=max(signal.detected_at for signal in active_signals),
        status="active",
    )


def _dominant_direction(signals: list[NormalizedSignal]) -> str:
    positive = sum(signal.strength for signal in signals if signal.direction == "positive")
    negative = sum(signal.strength for signal in signals if signal.direction == "negative")
    if positive > 0 and negative > 0:
        return "mixed"
    if positive > 0:
        return "positive"
    if negative > 0:
        return "negative"
    return "neutral"


def _derive_global_risk_tone(buckets: list[EnvironmentBucket]) -> str:
    positive = sum(bucket.aggregate_strength for bucket in buckets if bucket.dominant_direction == "positive")
    negative = sum(bucket.aggregate_strength for bucket in buckets if bucket.dominant_direction == "negative")
    if positive > 0 and negative > 0:
        return "mixed"
    if negative > positive and negative > 0:
        return "risk_off"
    if positive > negative and positive > 0:
        return "risk_on"
    return "neutral"


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _compact_strings(values: list[Any]) -> list[str]:
    compact: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in compact:
            compact.append(text)
    return compact
