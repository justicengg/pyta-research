# 2026-03-28 Interaction Resolution Core

## Goal

Implement the mainline backend core for sandbox interaction resolution:

1. define canonical interaction schema
2. build a rule-based interaction resolver from agent actions
3. integrate interaction output into round/report synthesis
4. add focused unit tests for resolver behavior

## Scope

- `src/sandbox/schemas/reports.py`
- `src/sandbox/services/interaction_resolver.py`
- `src/sandbox/services/synthesis.py`
- light integration only in orchestrator if needed
- dedicated unit tests for resolver/synthesis behavior

## Non-goals

- persisted serializer parity work
- API contract parity work
- broad frontend consumption

## Plan

1. add minimal interaction schema types
2. implement deterministic interaction resolver
3. thread resolved interaction output into round/report objects
4. add targeted unit tests
5. run focused tests, then full pytest if stable

## Status

- [completed] add minimal interaction schema types
- [completed] implement deterministic interaction resolver
- [completed] thread resolved interaction output into round/report objects
- [completed] add targeted unit tests
- [completed] run focused tests and full pytest

## Verification

- `python3 -m pytest -q tests/unit/test_interaction_resolver.py` -> `2 passed`
- `python3 -m pytest -q tests/unit/test_sandbox_stability.py` -> `1 passed`
- `python3 -m pytest -q` -> `37 passed`
