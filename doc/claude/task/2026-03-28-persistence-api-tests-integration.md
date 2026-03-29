# 2026-03-28 Persistence / API / Tests Integration

## Goal

Integrate the newly added `interaction_resolution` output into:

1. report persistence
2. persisted API serialization
3. checkpoint summary metadata
4. unit tests covering live vs persisted contract parity

## Scope

- `src/api/routers/sandbox.py`
- `src/sandbox/orchestrator/secondary.py`
- `tests/unit/test_api_sandbox.py`
- `tests/unit/test_sandbox_stability.py`
- `tests/helpers/sandbox_assertions.py`

## Plan

1. confirm live response already carries `interaction_resolution`
2. persist `interaction_resolution` into `ReportRecord.assembly_notes`
3. add summary-level interaction metadata into `Checkpoint.round_summary`
4. restore the same shape from `/sandbox/{id}/result`
5. add tests for persisted parity and degraded/reused paths
6. run focused pytest and update task status

## Status

- [x] Read handoff and current backend context
- [x] Confirm mainline interaction schema landed
- [x] Wire persistence and serializer parity
- [x] Update API/unit assertions
- [x] Run focused verification

## Verification

- `python3 -m pytest -q tests/unit/test_api_sandbox.py` -> `2 passed`
- `python3 -m pytest -q tests/unit/test_sandbox_stability.py` -> `1 passed`
- `python3 -m pytest -q` -> `37 passed`
