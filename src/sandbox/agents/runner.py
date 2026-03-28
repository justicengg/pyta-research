"""Parallel runner for secondary-market sandbox agents."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.sandbox.agents.templates.secondary_prompts import (
    SECONDARY_SANDBOX_SYSTEM_PROMPT,
    build_secondary_user_prompt,
)
from src.sandbox.llm.client import SandboxLLMClient
from src.sandbox.schemas.agents import (
    AgentNarrative,
    AgentPerspective,
    MarketBias,
    ParticipantType,
    PerspectiveStatus,
)
from src.sandbox.schemas.reports import AgentActionSnapshot


@dataclass
class RunnerResult:
    agent_type: ParticipantType
    perspective: AgentPerspective | None
    action: AgentActionSnapshot | None
    narrative: AgentNarrative | None
    error: str | None = None
    timed_out: bool = False
    used_stub: bool = False


class SecondaryAgentRunner:
    def __init__(self, llm_client: SandboxLLMClient | None = None) -> None:
        self.llm_client = llm_client or SandboxLLMClient()

    async def run_all(
        self,
        *,
        ticker: str,
        market: str,
        round_number: int,
        events: list[dict[str, Any]],
        narrative_guide: str | None,
        timeout_ms: int,
        market_data: dict[str, Any] | None = None,
        environment_state: dict[str, Any] | None = None,
    ) -> list[RunnerResult]:
        tasks = [
            self._run_single(
                agent_type=agent_type,
                ticker=ticker,
                market=market,
                round_number=round_number,
                events=events,
                narrative_guide=narrative_guide,
                timeout_ms=timeout_ms,
                market_data=market_data,
                environment_state=environment_state,
            )
            for agent_type in ParticipantType
        ]
        return list(await asyncio.gather(*tasks))

    async def run_one(
        self,
        *,
        agent_type: ParticipantType,
        ticker: str,
        market: str,
        round_number: int,
        events: list[dict[str, Any]],
        narrative_guide: str | None,
        timeout_ms: int,
        market_data: dict[str, Any] | None = None,
        environment_state: dict[str, Any] | None = None,
    ) -> RunnerResult:
        return await self._run_single(
            agent_type=agent_type,
            ticker=ticker,
            market=market,
            round_number=round_number,
            events=events,
            narrative_guide=narrative_guide,
            timeout_ms=timeout_ms,
            market_data=market_data,
            environment_state=environment_state,
        )

    async def _run_single(
        self,
        *,
        agent_type: ParticipantType,
        ticker: str,
        market: str,
        round_number: int,
        events: list[dict[str, Any]],
        narrative_guide: str | None,
        timeout_ms: int,
        market_data: dict[str, Any] | None = None,
        environment_state: dict[str, Any] | None = None,
    ) -> RunnerResult:
        try:
            return await asyncio.wait_for(
                self._generate(
                    agent_type,
                    ticker,
                    market,
                    round_number,
                    events,
                    narrative_guide,
                    market_data,
                    environment_state,
                ),
                timeout=timeout_ms / 1000,
            )
        except asyncio.TimeoutError:
            return RunnerResult(agent_type=agent_type, perspective=None, action=None, narrative=None, timed_out=True, error="timeout")
        except Exception as exc:  # pragma: no cover - defensive branch
            return RunnerResult(agent_type=agent_type, perspective=None, action=None, narrative=None, error=str(exc))

    async def _generate(
        self,
        agent_type: ParticipantType,
        ticker: str,
        market: str,
        round_number: int,
        events: list[dict[str, Any]],
        narrative_guide: str | None,
        market_data: dict[str, Any] | None = None,
        environment_state: dict[str, Any] | None = None,
    ) -> RunnerResult:
        if self.llm_client.enabled:
            response = await self.llm_client.generate_json(
                SECONDARY_SANDBOX_SYSTEM_PROMPT,
                build_secondary_user_prompt(
                    agent_type,
                    ticker,
                    market,
                    round_number,
                    events,
                    narrative_guide,
                    market_data,
                    environment_state,
                    self._focused_signals(agent_type, environment_state),
                ),
            )
            payload = json.loads(response.content)
            perspective, narrative = self._parse_llm_payload(agent_type, payload)
            action = self._coerce_action_snapshot(agent_type, payload.get("action"), perspective, environment_state)
            return RunnerResult(agent_type=agent_type, perspective=perspective, action=action, narrative=narrative)

        perspective, action, narrative = self._stub_response(agent_type, ticker, market, events, environment_state)
        return RunnerResult(
            agent_type=agent_type,
            perspective=perspective,
            action=action,
            narrative=narrative,
            used_stub=True,
        )

    def _stub_response(
        self,
        agent_type: ParticipantType,
        ticker: str,
        market: str,
        events: list[dict[str, Any]],
        environment_state: dict[str, Any] | None,
    ) -> tuple[AgentPerspective, AgentActionSnapshot, AgentNarrative]:
        latest_event = events[0]["content"] if events else f"{ticker} 当前暂无事件"
        leading_environment = self._leading_environment_label(environment_state)
        focus_map = {
            ParticipantType.TRADITIONAL_INSTITUTION: ["估值与基本面", "中长期配置"],
            ParticipantType.QUANT_INSTITUTION: ["价格变化", "流动性信号"],
            ParticipantType.RETAIL: ["热点叙事", "情绪变化"],
            ParticipantType.OFFSHORE_CAPITAL: ["全球流动性", "风险偏好"],
            ParticipantType.SHORT_TERM_CAPITAL: ["题材热度", "事件驱动"],
        }
        perspective = AgentPerspective(
            agent_type=agent_type,
            perspective_type=agent_type,
            market_bias=MarketBias.NEUTRAL,
            key_observations=[f"{agent_type.value} 关注到：{latest_event}", f"当前主导环境变量：{leading_environment}"],
            key_concerns=[f"{market} 市场短期不确定性仍在"],
            analytical_focus=[leading_environment, *focus_map[agent_type]][:3],
            confidence=0.35,
            perspective_status=PerspectiveStatus.LIVE,
        )
        action = self._build_default_action_snapshot(agent_type, perspective, environment_state)
        narrative = AgentNarrative(
            agent_type=agent_type,
            content=f"{datetime.now(timezone.utc).isoformat()} {agent_type.value} 对 {ticker} 的初步观察已生成。",
            trace_id=uuid4(),
        )
        return perspective, action, narrative

    def _parse_llm_payload(
        self,
        agent_type: ParticipantType,
        payload: dict[str, Any],
    ) -> tuple[AgentPerspective, AgentNarrative]:
        raw_perspective = payload.get("perspective")
        if not isinstance(raw_perspective, dict):
            raise ValueError("LLM response missing perspective object")

        key_observations = self._coerce_string_list(raw_perspective.get("key_observations"))
        key_concerns = self._coerce_string_list(raw_perspective.get("key_concerns"))
        analytical_focus = self._coerce_string_list(raw_perspective.get("analytical_focus"))
        if not key_observations and not key_concerns and not analytical_focus:
            raise ValueError("LLM perspective object contains no useful fields")

        perspective = AgentPerspective(
            agent_type=agent_type,
            perspective_type=agent_type,
            market_bias=self._coerce_market_bias(raw_perspective.get("market_bias")),
            key_observations=key_observations,
            key_concerns=key_concerns,
            analytical_focus=analytical_focus,
            confidence=self._coerce_confidence(raw_perspective.get("confidence")),
            perspective_status=PerspectiveStatus.LIVE,
        )

        raw_narrative = payload.get("narrative")
        content = ""
        mentions: list[ParticipantType] = []
        if isinstance(raw_narrative, dict):
            content = self._coerce_narrative_content(raw_narrative)
            mentions = self._coerce_mentions(raw_narrative.get("mentions"))
        elif isinstance(raw_narrative, str):
            content = raw_narrative.strip()
        if not content:
            content = "；".join((key_observations + analytical_focus)[:2]) or f"{agent_type.value} perspective captured."

        narrative = AgentNarrative(
            agent_type=agent_type,
            content=content,
            mentions=mentions,
            trace_id=uuid4(),
        )
        return perspective, narrative

    def _coerce_action_snapshot(
        self,
        agent_type: ParticipantType,
        raw_action: Any,
        perspective: AgentPerspective,
        environment_state: dict[str, Any] | None,
    ) -> AgentActionSnapshot:
        if isinstance(raw_action, dict):
            action_bias = self._coerce_action_bias(raw_action.get("action_bias"))
            rationale_summary = self._coerce_text(
                raw_action.get("rationale_summary"),
                fallback="；".join((perspective.key_observations + perspective.analytical_focus)[:2]) or f"{agent_type.value} action captured.",
            )
            key_drivers = self._coerce_string_list(raw_action.get("key_drivers"))[:3]
            affected_environment_types = self._coerce_environment_types(raw_action.get("affected_environment_types"))
            horizon = self._coerce_time_horizon(raw_action.get("horizon"))
            confidence = self._coerce_confidence(raw_action.get("confidence"))
            return AgentActionSnapshot(
                agent_type=agent_type,
                action_bias=action_bias,
                confidence=confidence if confidence > 0 else perspective.confidence,
                rationale_summary=rationale_summary,
                key_drivers=key_drivers or perspective.analytical_focus[:3],
                affected_environment_types=affected_environment_types,
                horizon=horizon,
            )

        return self._build_default_action_snapshot(agent_type, perspective, environment_state)

    def _coerce_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            result: list[str] = []
            for item in value:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        result.append(text)
            return result
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return []

    def _coerce_market_bias(self, value: Any) -> MarketBias:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {bias.value for bias in MarketBias}:
                return MarketBias(normalized)
            if any(token in normalized for token in ("bull", "positive", "optimistic", "constructive")):
                return MarketBias.BULLISH
            if any(token in normalized for token in ("bear", "negative", "cautious", "defensive", "pessimistic")):
                return MarketBias.BEARISH
            if any(token in normalized for token in ("mix", "balanced", "split")):
                return MarketBias.MIXED
        return MarketBias.NEUTRAL

    def _coerce_confidence(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            text = value.strip()
            if text.endswith("%"):
                text = text[:-1].strip()
                try:
                    return max(0.0, min(1.0, float(text) / 100.0))
                except ValueError:
                    return 0.0
            try:
                value = float(text)
            except ValueError:
                return 0.0
        if isinstance(value, (int, float)):
            numeric = float(value)
            if 0.0 <= numeric <= 1.0:
                return numeric
            if 1.0 < numeric <= 100.0:
                return numeric / 100.0
        return 0.0

    def _coerce_narrative_content(self, value: dict[str, Any]) -> str:
        for key in ("content", "summary", "text", "message"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _coerce_mentions(self, value: Any) -> list[ParticipantType]:
        candidates: list[str] = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    candidates.append(item)
        elif isinstance(value, str):
            candidates = [part.strip() for part in re.split(r"[,;|]", value) if part.strip()]

        mentions: list[ParticipantType] = []
        for item in candidates:
            normalized = item.strip().lower()
            try:
                mentions.append(ParticipantType(normalized))
            except ValueError:
                continue
        return mentions

    def _coerce_action_bias(self, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"accumulate", "reduce", "hold", "watch", "hedge", "chase", "exit"}:
                return normalized
        return "watch"

    def _coerce_time_horizon(self, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"intraday", "short_term", "mid_term", "long_term"}:
                return normalized
        return "short_term"

    def _coerce_text(self, value: Any, fallback: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return fallback

    def _coerce_environment_types(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        supported = {"geopolitics", "macro_policy", "market_sentiment", "fundamentals", "alternative_data"}
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str) and item in supported and item not in normalized:
                normalized.append(item)
        return normalized

    def _focused_signals(
        self,
        agent_type: ParticipantType,
        environment_state: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if not environment_state:
            return []

        preference_map = {
            ParticipantType.TRADITIONAL_INSTITUTION: {"fundamentals", "macro_policy"},
            ParticipantType.QUANT_INSTITUTION: {"alternative_data", "market_sentiment", "macro_policy"},
            ParticipantType.RETAIL: {"market_sentiment", "fundamentals"},
            ParticipantType.OFFSHORE_CAPITAL: {"geopolitics", "macro_policy", "fundamentals"},
            ParticipantType.SHORT_TERM_CAPITAL: {"market_sentiment", "alternative_data"},
        }
        preferred = preference_map[agent_type]
        focused: list[dict[str, Any]] = []

        for bucket in environment_state.get("buckets", []):
            if bucket.get("type") not in preferred:
                continue
            focused.extend(bucket.get("active_signals", [])[:2])

        return focused[:4]

    def _leading_environment_label(self, environment_state: dict[str, Any] | None) -> str:
        if not environment_state:
            return "环境信号不足"

        buckets = environment_state.get("buckets", [])
        if not buckets:
            return "环境信号不足"

        ranked = sorted(
            buckets,
            key=lambda bucket: bucket.get("aggregate_strength", 0),
            reverse=True,
        )
        top = ranked[0]
        return str(top.get("display_name") or top.get("type") or "环境信号")

    def _build_default_action_snapshot(
        self,
        agent_type: ParticipantType,
        perspective: AgentPerspective,
        environment_state: dict[str, Any] | None,
    ) -> AgentActionSnapshot:
        action_bias = self._default_action_bias(agent_type, perspective.market_bias)
        return AgentActionSnapshot(
            agent_type=agent_type,
            action_bias=action_bias,
            confidence=perspective.confidence,
            rationale_summary="；".join((perspective.key_observations + perspective.analytical_focus)[:2]) or f"{agent_type.value} action captured.",
            key_drivers=(perspective.analytical_focus or perspective.key_concerns or perspective.key_observations)[:3],
            affected_environment_types=self._infer_affected_environment_types(environment_state),
            horizon=self._default_horizon(agent_type),
        )

    def _default_action_bias(self, agent_type: ParticipantType, market_bias: MarketBias) -> str:
        if market_bias == MarketBias.BULLISH:
            return "chase" if agent_type == ParticipantType.SHORT_TERM_CAPITAL else "accumulate"
        if market_bias == MarketBias.BEARISH:
            return "exit" if agent_type == ParticipantType.SHORT_TERM_CAPITAL else "reduce"
        if market_bias == MarketBias.MIXED:
            return "hedge"
        return "watch"

    def _default_horizon(self, agent_type: ParticipantType) -> str:
        if agent_type == ParticipantType.SHORT_TERM_CAPITAL:
            return "intraday"
        if agent_type == ParticipantType.RETAIL:
            return "short_term"
        if agent_type == ParticipantType.QUANT_INSTITUTION:
            return "short_term"
        if agent_type == ParticipantType.TRADITIONAL_INSTITUTION:
            return "long_term"
        return "mid_term"

    def _infer_affected_environment_types(self, environment_state: dict[str, Any] | None) -> list[str]:
        if not environment_state:
            return []
        active_types: list[str] = []
        for bucket in environment_state.get("buckets", []):
            if bucket.get("status") != "active":
                continue
            bucket_type = bucket.get("type")
            if isinstance(bucket_type, str) and bucket_type not in active_types:
                active_types.append(bucket_type)
        return active_types[:3]
