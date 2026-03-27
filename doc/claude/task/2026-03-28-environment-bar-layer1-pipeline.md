# 2026-03-28 Environment Bar Layer 1 Pipeline

## Goal

Implement the first code slice for the Environment Bar refactor:

1. add explicit environment-layer types
2. normalize raw input events into environment signals
3. thread environment state into the sandbox request / orchestrator path
4. preserve the existing 5-agent flow while upgrading the input contract

## Scope

- frontend type additions for environment state
- frontend event classification / normalization helper
- backend request schema support for environment state
- backend orchestrator wiring for environment-aware execution
- minimal UI state exposure for future Environment Bar rendering

## Non-goals

- full UI redesign of CanvasStage
- final Environment Bar visual component
- SSE streaming
- multi-round environment decay model

## Notes

- Keep 5 agents as behavior subjects.
- Environment variables are upstream drivers, not new agents.
- Do not break existing sandbox run flow.

## Status

- [x] inspect current sandbox/frontend entry points
- [x] create task note
- [ ] create git checkpoint before edits
- [ ] implement frontend environment pipeline
- [ ] implement backend environment contract
- [ ] validate build/check
