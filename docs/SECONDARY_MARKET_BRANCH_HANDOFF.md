# Secondary Market MVP Branch Handoff

This document is the **current implementation handoff manual** for the rebuilt secondary-market line.
It should be the first file Claude reads before continuing development or cleaning up legacy files.

## Branch

- Recommended development branch: `PYTA/secondary-market-mvp`
- Base branch target: `origin/main`

## Why This Branch Exists

The current `main` working tree contains ongoing design/prototype materials and is not the right place to start the next implementation round directly.

This branch is intended to be the clean implementation line for the **secondary market MVP**.

## Current Decision

Do **not** continue implementation directly on `main`.

Use `PYTA/secondary-market-mvp` as the development line for the next coding phase.

## Implementation Scope

The first implementation target is the **secondary market** only.

Architecture mode:
- `Parallel Perspective Simulation`

Default market participant agents:
- `传统机构 Agent`
- `量化机构 Agent`
- `普通散户 Agent`
- `海外资金 Agent`
- `游资 / 短线资金 Agent`

## Source of Truth

Primary docs to read before implementation:

1. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/00 Layer 2 群Agent通信架构总纲.md`
2. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/01 二级市场第一版最小能力规格.md`
3. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/07 单轮推演完整时序流程.md`
4. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/08 Agent System Prompt模板设计.md`
5. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/02 交互与界面/01 交互总纲.md`
6. `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/02 交互与界面/03 Research Canvas 原型草图.md`

## Immediate Coding Direction

Start from schema and orchestration alignment first, not UI.

Recommended order:

1. Sync latest `origin/main`
2. Switch to `PYTA/secondary-market-mvp`
3. Align sandbox schema from old `AgentAction / AgentSignal` world to the new `AgentPerspective / AgentNarrative` world
4. Add secondary-market orchestrator and parallel fan-out runner
5. Add timeout-window logic with fallback to previous-round perspective before degraded output
6. Add `RoundComplete` and `MarketReadingReport`
7. Expose minimal sandbox API

## Current Delivery Status

The secondary-market MVP branch now includes:

1. schema foundation rebuild
2. secondary orchestrator + parallel runner
3. synchronous sandbox API
4. sandbox persistence + migration
5. real-LLM-ready integration path
6. stability pass for persistence / fallback
7. developer CLI for local sandbox runs
8. frontend bootstrap app (`Vite + React + TypeScript`)
9. research canvas page skeleton based on the approved HTML prototype
10. frontend/backend wiring for the minimum interaction loop
11. local end-to-end integration run with real MiniMax responses

## What Was Built Today

### Backend

The rebuilt secondary-market backend now supports:

1. `AgentPerspective / AgentNarrative` schema world
2. five market participant agents:
   - `traditional_institution`
   - `quant_institution`
   - `retail`
   - `offshore_capital`
   - `short_term_capital`
3. synchronous `POST /api/v1/sandbox/run`
4. `GET /api/v1/sandbox/{sandbox_id}/result`
5. timeout fallback using snapshots
6. checkpoint + report persistence
7. MiniMax integration through an OpenAI-compatible base URL

### Frontend

A new frontend app was added under:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend`

Stack:

- `Vite`
- `React`
- `TypeScript`

The frontend now contains:

1. `ResearchCanvasPage`
2. left information panel
3. center canvas stage
4. bottom command console
5. five agent nodes
6. one result card slot below each agent node
7. frontend API client + adapter
8. real `/sandbox/run` binding from the command console

Important files:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/pages/ResearchCanvasPage.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/hooks/useSandboxRun.ts`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/lib/api/sandbox.ts`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/lib/adapters/sandboxAdapter.ts`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/components/layout/InformationPanel.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/components/layout/CanvasStage.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/components/layout/CommandConsole.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/components/canvas/AgentNode.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/components/canvas/AgentResultCard.tsx`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend/src/styles/research-canvas.css`

## Minimum Interaction Loop Status

The current minimum interaction loop is now connected:

1. the page opens
2. the command console accepts input
3. the frontend sends a real `POST /api/v1/sandbox/run`
4. the backend runs the five-agent secondary-market sandbox
5. the frontend renders:
   - left-side input events
   - center canvas agent statuses
   - one result card below each agent

This is the current MVP UI loop. The right observation panel remains intentionally removed.

## Real LLM Integration Status

Provider used in local validation:

- `MiniMax-M2.5-highspeed`
- OpenAI-compatible endpoint style

The current branch has already passed a local real-LLM run where:

1. frontend proxy
2. backend API
3. MiniMax call
4. persistence
5. frontend rendering

all completed successfully.

Final successful integration state:

- `data_quality = complete`
- `stop_reason = all_perspectives_received`
- all five agents returned `live`

## Frontend Development Notes

### This branch now has a real frontend shell

It is no longer just a static prototype in `docs/`.

The HTML prototype remains a design reference:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/multi_agent_sandbox_fusion_direction.html`

But active UI development should now happen in:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend`

### UI constraints to preserve

Do not:

- change the established font system
- change the color system
- restore the removed right observation panel
- introduce external-agent UI in this phase
- redesign the page away from the approved canvas direction

## Suggested Start Point For Tomorrow

If Claude continues this branch tomorrow, the recommended read/use order is:

1. this handoff file
2. the Obsidian source-of-truth docs listed above
3. the frontend app under `frontend/`
4. the backend sandbox modules under `src/sandbox/`

Recommended first technical checks:

1. confirm backend boots
2. confirm frontend boots
3. confirm `POST /api/v1/sandbox/run` still returns a valid result
4. confirm the page still renders five live agent cards in the good path

## Legacy Cleanup Strategy

Do **not** start by deleting old repository files blindly.

The correct order is:

1. keep the rebuilt secondary-market line stable
2. use this handoff to identify what is now the new source of truth
3. audit old GitHub files against the new implementation
4. only then delete, archive, or move legacy files from the old world

The cleanup target later is:

- old backend concepts from the pre-rebuild world
- outdated UI/template files that are no longer used
- stale design remnants once the new frontend is fully adopted

The cleanup should be a **separate pass**, not mixed into continuation work.

## Current Uncommitted Work

At the time of writing, the branch contains local changes related to:

1. frontend app files under `frontend/`
2. one prompt hardening update:
   - `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/agents/templates/secondary_prompts.py`

Also note:

- local sqlite artifacts such as `pyta.db` may appear during development
- do not commit local runtime artifacts by accident

## Developer CLI

The branch now provides a local developer CLI:

```bash
python -m src.sandbox.cli sandbox run-secondary ...
python -m src.sandbox.cli sandbox inspect ...
python -m src.sandbox.cli sandbox replay-last ...
python -m src.sandbox.cli sandbox agent-dry-run ...
```

Recommended usage:

1. run one sandbox round from a structured JSON file
2. inspect persisted results by `sandbox_id`
3. replay a previous sandbox using persisted input events
4. dry-run a single market participant agent for prompt tuning

### Input format

`run-secondary` and `agent-dry-run` currently accept **structured file input only**:

- a JSON array of events
- or a JSON object with an `events` array

### Example

```bash
python -m src.sandbox.cli sandbox run-secondary \
  --ticker 0700.HK \
  --market HK \
  --input /tmp/pyta_events.json \
  --json
```

### Note

The CLI is a developer console, not a user-facing product surface.
It is meant for local iteration, prompt tuning, replay, and debugging.

## Important Constraints

- Do not reintroduce `buy / sell / hold`, target price, stop loss, or position simulation into Layer 2 / Layer 3
- MVP should not add extra Layer 3 LLM synthesis
- Summary text should be generated from `key_observations + analytical_focus`, not by adding a new summary schema field
- Input contract should stay aligned with structured `events[]`

## Collaboration Rule

For each implementation round:

1. discuss and align the plan first
2. wait for explicit confirmation
3. then start coding

Do not jump directly into implementation before plan alignment.

## Working Tree Note

The current repository has uncommitted local design files. Treat them carefully and avoid destructive cleanup.
