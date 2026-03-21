from __future__ import annotations

import asyncio
from uuid import uuid4

from src.db.session import configure_engine, get_session
from src.sandbox.agents.runner import RunnerResult
from src.sandbox.orchestrator.secondary import SecondaryOrchestrator
from src.sandbox.schemas.agents import (
    AgentNarrative,
    AgentPerspective,
    MarketBias,
    ParticipantType,
    PerspectiveStatus,
)
from src.sandbox.schemas.memory import AgentSnapshot, SandboxSession
from tests.helpers.sandbox_assertions import assert_sandbox_records_consistent


class FakeRunner:
    async def run_all(self, **_: object) -> list[RunnerResult]:
        return [
            RunnerResult(
                agent_type=ParticipantType.TRADITIONAL_INSTITUTION,
                perspective=AgentPerspective(
                    agent_type=ParticipantType.TRADITIONAL_INSTITUTION,
                    perspective_type=ParticipantType.TRADITIONAL_INSTITUTION,
                    market_bias=MarketBias.NEUTRAL,
                    key_observations=["single signal is positive but incomplete"],
                    key_concerns=["missing quantified contribution"],
                    analytical_focus=["earnings follow-through"],
                    confidence=0.45,
                    perspective_status=PerspectiveStatus.LIVE,
                ),
                narrative=AgentNarrative(
                    agent_type=ParticipantType.TRADITIONAL_INSTITUTION,
                    content="Institutional read stays cautious but constructive.",
                    trace_id=uuid4(),
                ),
            ),
            RunnerResult(
                agent_type=ParticipantType.QUANT_INSTITUTION,
                perspective=None,
                narrative=None,
                error="timeout",
                timed_out=True,
            ),
            RunnerResult(
                agent_type=ParticipantType.RETAIL,
                perspective=None,
                narrative=None,
                error="malformed-json",
            ),
            RunnerResult(
                agent_type=ParticipantType.OFFSHORE_CAPITAL,
                perspective=AgentPerspective(
                    agent_type=ParticipantType.OFFSHORE_CAPITAL,
                    perspective_type=ParticipantType.OFFSHORE_CAPITAL,
                    market_bias=MarketBias.BULLISH,
                    key_observations=["signal supports global tech allocation interest"],
                    key_concerns=["still need liquidity confirmation"],
                    analytical_focus=["cross-market attractiveness"],
                    confidence=0.52,
                    perspective_status=PerspectiveStatus.LIVE,
                ),
                narrative=AgentNarrative(
                    agent_type=ParticipantType.OFFSHORE_CAPITAL,
                    content="Offshore capital sees secular upside but wants validation.",
                    trace_id=uuid4(),
                ),
            ),
            RunnerResult(
                agent_type=ParticipantType.SHORT_TERM_CAPITAL,
                perspective=AgentPerspective(
                    agent_type=ParticipantType.SHORT_TERM_CAPITAL,
                    perspective_type=ParticipantType.SHORT_TERM_CAPITAL,
                    market_bias=MarketBias.BULLISH,
                    key_observations=["theme has near-term trading heat"],
                    key_concerns=["follow-up catalyst required"],
                    analytical_focus=["headline continuation"],
                    confidence=0.61,
                    perspective_status=PerspectiveStatus.LIVE,
                ),
                narrative=AgentNarrative(
                    agent_type=ParticipantType.SHORT_TERM_CAPITAL,
                    content="Short-term capital is watching for catalyst continuation.",
                    trace_id=uuid4(),
                ),
            ),
        ]


def test_orchestrator_persists_fallback_and_degraded_paths(migrated_db: str):
    configure_engine(migrated_db)
    orchestrator = SecondaryOrchestrator(runner=FakeRunner())

    with get_session() as session:
        sandbox = SandboxSession(
            ticker="0700.HK",
            market="HK",
            task_scope="secondary market simulation for 0700.HK",
            narrative_guide="Focus on divergence.",
            round_timeout_ms=5000,
            status="running",
            current_round=0,
            total_rounds=0,
            agent_instance_ids=[agent.value for agent in ParticipantType],
        )
        session.add(sandbox)
        session.flush()
        session.add(
            AgentSnapshot(
                sandbox_id=sandbox.id,
                round=1,
                agent_id=ParticipantType.QUANT_INSTITUTION.value,
                perspective_type=ParticipantType.QUANT_INSTITUTION.value,
                perspective_status=PerspectiveStatus.LIVE.value,
                key_observations=["previous quant read still usable"],
                key_concerns=["need order flow confirmation"],
                analytical_focus=["liquidity follow-through"],
                confidence=0.4,
                source_trace_id=uuid4(),
            )
        )
        session.flush()
        sandbox_id = sandbox.id

    with get_session() as session:
        result = asyncio.run(
            orchestrator.run(
                session=session,
                sandbox_id=sandbox_id,
                ticker="0700.HK",
                market="HK",
                events=[
                    {
                        "event_id": "evt-1",
                        "event_type": "news",
                        "content": "Tencent announced stronger-than-expected AI collaboration progress.",
                        "source": "gnews",
                        "timestamp": "2026-03-21T10:00:00Z",
                        "symbol": "0700.HK",
                        "metadata": {"lang": "en"},
                    }
                ],
                round_timeout_ms=5000,
                narrative_guide="Focus on divergence.",
                round_number=2,
            )
        )

        assert result.round_complete.data_quality == "degraded"
        status_map = {item.agent_type.value: item.perspective_status.value for item in result.round_complete.per_agent_status}
        assert status_map["quant_institution"] == "reused_last_round"
        assert status_map["retail"] == "degraded"

        bundle = assert_sandbox_records_consistent(
            session,
            sandbox_id,
            expected_round=2,
            expected_report_count=1,
            expected_checkpoint_count=1,
            min_event_count=11,
            expected_snapshot_count=6,
        )
        checkpoint = bundle.checkpoints[0]
        assert checkpoint.reused_agent_ids == ["quant_institution"]
        assert checkpoint.degraded_agent_ids == ["retail"]
        assert bundle.reports[0].data_quality == "degraded"
