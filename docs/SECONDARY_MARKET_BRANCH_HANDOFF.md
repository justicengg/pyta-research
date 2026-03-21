# Secondary Market MVP Branch Handoff

## Branch

- Recommended development branch: `codex/secondary-market-mvp`
- Base branch target: `origin/main`

## Why This Branch Exists

The current `main` working tree contains ongoing design/prototype materials and is not the right place to start the next implementation round directly.

This branch is intended to be the clean implementation line for the **secondary market MVP**.

## Current Decision

Do **not** continue implementation directly on `main`.

Use `codex/secondary-market-mvp` as the development line for the next coding phase.

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
2. Switch to `codex/secondary-market-mvp`
3. Align sandbox schema from old `AgentAction / AgentSignal` world to the new `AgentPerspective / AgentNarrative` world
4. Add secondary-market orchestrator and parallel fan-out runner
5. Add timeout-window logic with fallback to previous-round perspective before degraded output
6. Add `RoundComplete` and `MarketReadingReport`
7. Expose minimal sandbox API

## Important Constraints

- Do not reintroduce `buy / sell / hold`, target price, stop loss, or position simulation into Layer 2 / Layer 3
- MVP should not add extra Layer 3 LLM synthesis
- Summary text should be generated from `key_observations + analytical_focus`, not by adding a new summary schema field
- Input contract should stay aligned with structured `events[]`

## Working Tree Note

The current repository has uncommitted local design files. Treat them carefully and avoid destructive cleanup.
