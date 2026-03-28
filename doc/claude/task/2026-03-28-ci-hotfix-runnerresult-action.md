# 2026-03-28 CI Hotfix: RunnerResult `action` Backward Compatibility

## Context

- PR #77 merged, but GitHub Actions `test (3.11)` failed on both the PR run and the follow-up `main push`.
- Failure is in `tests/unit/test_sandbox_stability.py`.
- Root cause: `RunnerResult` introduced a required `action` field, while the test `FakeRunner` still constructs `RunnerResult` with the older shape.

## Plan

1. Restore backward compatibility for `RunnerResult` by making optional fields default-safe.
2. Run the targeted failing test locally.
3. If green, recommend a minimal hotfix PR against `main`.

## Status

- [completed] Apply backward-compatible schema fix
- [completed] Run targeted pytest verification
- [completed] Run local full pytest verification (`35 passed`)
- [in_progress] Summarize hotfix path for GitHub

## Verification

- `python3 -m pytest -q tests/unit/test_sandbox_stability.py` -> `1 passed`
- `python3 -m pytest -q` -> `35 passed`
