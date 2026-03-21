"""Developer CLI for secondary-market sandbox workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from uuid import UUID

from src.db.session import get_session
from src.sandbox.agents.runner import SecondaryAgentRunner
from src.sandbox.cli_helpers import (
    fetch_event_summaries,
    fetch_input_events,
    fetch_latest_checkpoint,
    fetch_latest_report,
    fetch_sandbox,
    fetch_snapshot_summaries,
    load_events_file,
    serialize_checkpoint,
    serialize_report,
    write_json,
)
from src.sandbox.orchestrator.secondary import SecondaryOrchestrator
from src.sandbox.schemas.agents import ParticipantType


def _dump(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    if "sandbox_id" in payload:
        print(f"sandbox_id: {payload['sandbox_id']}")
    if "quality" in payload:
        print(f"quality: {payload['quality']}")
    if "stop_reason" in payload:
        print(f"stop_reason: {payload['stop_reason']}")
    if "session_status" in payload:
        print(f"session_status: {payload['session_status']}")
    if payload.get("per_agent_status"):
        print("agents:")
        for item in payload["per_agent_status"]:
            print(f"  - {item['agent_type']}: {item['perspective_status']} | {item['summary']}")
    if payload.get("perspective_synthesis"):
        print("perspective_synthesis:")
        for agent, text in payload["perspective_synthesis"].items():
            print(f"  - {agent}: {text}")
    if payload.get("tracking_signals"):
        print("tracking_signals:")
        for signal in payload["tracking_signals"]:
            print(f"  - {signal}")
    if payload.get("key_tensions"):
        print("key_tensions:")
        for item in payload["key_tensions"]:
            desc = item.get("description", item)
            print(f"  - {desc}")
    if payload.get("events"):
        print("events:")
        for item in payload["events"]:
            print(f"  - round {item['round']} {item['event_type']} {item['source']} status={item['perspective_status']}")
    if payload.get("snapshots"):
        print("snapshots:")
        for item in payload["snapshots"]:
            print(f"  - round {item['round']} {item['agent_id']} {item['perspective_status']} conf={item['confidence']}")


async def _run_secondary(args: argparse.Namespace) -> None:
    events = load_events_file(args.input)
    orchestrator = SecondaryOrchestrator()
    with get_session() as session:
        result = await orchestrator.run(
            session=session,
            ticker=args.ticker,
            market=args.market,
            events=events,
            round_timeout_ms=args.timeout_ms,
            narrative_guide=args.narrative_guide,
        )
        payload = {
            "sandbox_id": str(result.sandbox_id),
            "quality": result.round_complete.data_quality,
            "stop_reason": result.round_complete.stop_reason,
            "per_agent_status": [
                {
                    "agent_type": item.agent_type.value,
                    "perspective_status": item.perspective_status.value,
                    "summary": item.summary,
                }
                for item in result.round_complete.per_agent_status
            ],
            "perspective_synthesis": {k.value: v for k, v in result.report.perspective_synthesis.items()},
            "key_tensions": [item.model_dump(mode="json") for item in result.report.key_tensions],
            "tracking_signals": result.report.tracking_signals,
            "report": result.report.model_dump(mode="json"),
        }
        if args.save_report:
            write_json(args.save_report, payload)
        _dump(payload, args.json)


def _inspect(args: argparse.Namespace) -> None:
    sandbox_id = UUID(args.sandbox_id)
    with get_session() as session:
        sandbox = fetch_sandbox(session, sandbox_id)
        if sandbox is None:
            raise SystemExit(f"Sandbox not found: {sandbox_id}")
        report = fetch_latest_report(session, sandbox_id)
        checkpoint = fetch_latest_checkpoint(session, sandbox_id)
        payload: dict[str, Any] = {
            "sandbox_id": str(sandbox.id),
            "ticker": sandbox.ticker,
            "market": sandbox.market,
            "session_status": sandbox.status,
            "current_round": sandbox.current_round,
            "latest_checkpoint": serialize_checkpoint(checkpoint),
            "report": serialize_report(report) if report else None,
        }
        if args.show_events:
            payload["events"] = fetch_event_summaries(session, sandbox_id)
        if args.show_snapshots:
            payload["snapshots"] = fetch_snapshot_summaries(session, sandbox_id)
        _dump(payload, args.json)


async def _replay_last(args: argparse.Namespace) -> None:
    sandbox_id = UUID(args.sandbox_id)
    orchestrator = SecondaryOrchestrator()
    with get_session() as session:
        sandbox = fetch_sandbox(session, sandbox_id)
        if sandbox is None:
            raise SystemExit(f"Sandbox not found: {sandbox_id}")
        input_events = fetch_input_events(session, sandbox_id)
        if not input_events:
            raise SystemExit(f"No persisted input events found for sandbox {sandbox_id}")
        round_number = (sandbox.current_round or 0) + 1
        result = await orchestrator.run(
            session=session,
            sandbox_id=sandbox_id,
            ticker=sandbox.ticker,
            market=sandbox.market,
            events=input_events,
            round_timeout_ms=args.timeout_ms or sandbox.round_timeout_ms,
            narrative_guide=args.narrative_guide or sandbox.narrative_guide,
            round_number=round_number,
        )
        payload = {
            "sandbox_id": str(result.sandbox_id),
            "quality": result.round_complete.data_quality,
            "stop_reason": result.round_complete.stop_reason,
            "round": result.round_complete.rounds_completed,
            "per_agent_status": [
                {
                    "agent_type": item.agent_type.value,
                    "perspective_status": item.perspective_status.value,
                    "summary": item.summary,
                }
                for item in result.round_complete.per_agent_status
            ],
            "perspective_synthesis": {k.value: v for k, v in result.report.perspective_synthesis.items()},
            "tracking_signals": result.report.tracking_signals,
        }
        _dump(payload, args.json)


async def _agent_dry_run(args: argparse.Namespace) -> None:
    events = load_events_file(args.input)
    agent_type = ParticipantType(args.agent)
    runner = SecondaryAgentRunner()
    result = await runner.run_one(
        agent_type=agent_type,
        ticker=args.ticker,
        market=args.market,
        round_number=1,
        events=events,
        narrative_guide=args.narrative_guide,
        timeout_ms=args.timeout_ms,
    )
    payload = {
        "agent_type": agent_type.value,
        "timed_out": result.timed_out,
        "used_stub": result.used_stub,
        "error": result.error,
        "perspective": result.perspective.model_dump(mode="json") if result.perspective else None,
        "narrative": result.narrative.model_dump(mode="json") if result.narrative else None,
    }
    _dump(payload, args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyta-sandbox", description="Developer CLI for PYTA secondary-market sandbox.")
    subparsers = parser.add_subparsers(dest="domain", required=True)

    sandbox = subparsers.add_parser("sandbox", help="Sandbox developer workflows.")
    sandbox_sub = sandbox.add_subparsers(dest="command", required=True)

    run_cmd = sandbox_sub.add_parser("run-secondary", help="Run one secondary-market sandbox round.")
    run_cmd.add_argument("--ticker", required=True)
    run_cmd.add_argument("--market", required=True)
    run_cmd.add_argument("--input", required=True, help="Path to a JSON file containing events or {events:[...]}.")
    run_cmd.add_argument("--timeout-ms", type=int, default=30000)
    run_cmd.add_argument("--narrative-guide")
    run_cmd.add_argument("--json", action="store_true")
    run_cmd.add_argument("--save-report")
    run_cmd.set_defaults(handler=lambda args: asyncio.run(_run_secondary(args)))

    inspect_cmd = sandbox_sub.add_parser("inspect", help="Inspect a persisted sandbox result.")
    inspect_cmd.add_argument("--sandbox-id", required=True)
    inspect_cmd.add_argument("--json", action="store_true")
    inspect_cmd.add_argument("--show-events", action="store_true")
    inspect_cmd.add_argument("--show-snapshots", action="store_true")
    inspect_cmd.set_defaults(handler=_inspect)

    replay_cmd = sandbox_sub.add_parser("replay-last", help="Replay the latest persisted input events for a sandbox.")
    replay_cmd.add_argument("--sandbox-id", required=True)
    replay_cmd.add_argument("--timeout-ms", type=int)
    replay_cmd.add_argument("--narrative-guide")
    replay_cmd.add_argument("--json", action="store_true")
    replay_cmd.set_defaults(handler=lambda args: asyncio.run(_replay_last(args)))

    dry_cmd = sandbox_sub.add_parser("agent-dry-run", help="Run a single agent against structured events.")
    dry_cmd.add_argument("--agent", required=True, choices=[agent.value for agent in ParticipantType])
    dry_cmd.add_argument("--ticker", required=True)
    dry_cmd.add_argument("--market", required=True)
    dry_cmd.add_argument("--input", required=True, help="Path to a JSON file containing events or {events:[...]}.")
    dry_cmd.add_argument("--timeout-ms", type=int, default=30000)
    dry_cmd.add_argument("--narrative-guide")
    dry_cmd.add_argument("--json", action="store_true")
    dry_cmd.set_defaults(handler=lambda args: asyncio.run(_agent_dry_run(args)))

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()

