# 2026-03-28 Backend Split: Interaction Resolution

## Goal

Continue backend development for the Environment-driven sandbox by introducing the next layer after `Action Snapshot`:

1. `Interaction Resolution`
2. `Round-level market force summary`

## Current baseline

- `environment_state` exists
- `action snapshot` exists
- `round_complete` and `market_reading_report` exist
- missing: explicit interaction edges / conflict model / reinforcement model / round-level simulation summary

## Recommended split

### Track A: Interaction Core

Owner: main agent

Scope:
- add schemas for interaction outputs
- add resolver service from `list[RunnerResult] -> interaction model`
- integrate resolver into orchestrator/synthesis pipeline

Primary files:
- `src/sandbox/schemas/reports.py`
- `src/sandbox/services/synthesis.py`
- `src/sandbox/orchestrator/secondary.py`
- possible new file: `src/sandbox/services/interaction_resolver.py`

### Track B: Persistence + API/Test Contract

Owner: parallel codex agent

Scope:
- persist interaction output into report/checkpoint payloads
- update API serialization shape if needed
- add/adjust unit tests for round report contract

Primary files:
- `src/api/routers/sandbox.py`
- `src/sandbox/orchestrator/secondary.py`
- `tests/unit/...`
- possible adapter tests if backend response shape changes

## Merge rule

- Track A owns interaction schema + resolver logic
- Track B must not redefine schema semantics
- integration point is the final report payload only

## Execution order

1. Main agent defines canonical interaction schema
2. Parallel agent adapts persistence/tests to that schema
3. Main agent integrates and final-verifies
