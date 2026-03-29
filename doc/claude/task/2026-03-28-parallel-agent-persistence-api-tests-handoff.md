# Parallel Agent Handoff: Persistence / API / Tests for Interaction Resolution

> Date: 2026-03-28
> Project: PYTA Research - Secondary Market MVP
> Repo root: `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp`
> Role: supporting implementation agent
> Scope: backend integration only, not core schema design

---

## 1. Mission

You are joining an in-progress backend refactor for the secondary-market sandbox.

The product is moving from:

`raw input -> 5 agents -> report`

to:

`raw input -> environment state -> agent action snapshot -> interaction resolution -> report`

The main agent owns the **canonical interaction schema** and **interaction resolver semantics**.

Your role is narrower and more execution-oriented:

1. wire the new interaction output into persistence
2. wire it into API response serialization
3. update tests so live and persisted response paths stay aligned

You are **not** expected to redesign the sandbox, rename schema concepts, or redefine interaction semantics.

---

## 2. Local Repo Context

### Repo path

Work only inside:

`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp`

This is a Git worktree, isolated from the main checkout.

### Important note about branch context

At the moment, there is an active hotfix branch in the worktree history because CI for PR #77 was fixed.

Do not assume that hotfix branch is your feature branch.

Before you make feature changes:

1. inspect current branch
2. inspect current git status
3. confirm whether you should keep working locally or create a new branch

If there is no explicit new branch instruction yet, treat your first step as **read-only exploration plus a local plan**, not immediate push behavior.

---

## 3. Read First

You should read these before changing anything:

### Project protocol

- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/AGENTS.md`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/AGENTS.md)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/PROJECT_BOOT_PROTOCOL.md`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/PROJECT_BOOT_PROTOCOL.md)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/UI_SYSTEM_STANDARD_MANUAL.md`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/UI_SYSTEM_STANDARD_MANUAL.md)

### Design notes

- [`/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/10 Environment Bar数据结构与时序设计.md`](/Users/sikaijiang/Documents/Obsidian%20Vault/PYTA/01%20项目主结构/Layer%202/10%20Environment%20Bar数据结构与时序设计.md)
- [`/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2/11 Agent Action与博弈解析层设计.md`](/Users/sikaijiang/Documents/Obsidian%20Vault/PYTA/01%20项目主结构/Layer%202/11%20Agent%20Action与博弈解析层设计.md)

### Existing task split note

- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/doc/claude/task/2026-03-28-backend-interaction-resolution-split.md`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/doc/claude/task/2026-03-28-backend-interaction-resolution-split.md)

---

## 4. What Is Already Implemented

The current backend already has these pieces:

1. `environment_state`
2. `action snapshot`
3. `round_complete`
4. `market_reading_report`

What is missing is the next layer:

- explicit `interaction resolution`
- round-level market-force structure
- consistent persistence/API retrieval of that structure

You are not starting from zero.

This is an integration task on top of an existing pipeline.

---

## 5. Your Exact Scope

You own:

1. **Persistence integration**
2. **API serialization integration**
3. **Test coverage**

More concretely, after the main agent defines the interaction fields, you should:

1. make sure live sandbox execution returns the new interaction output
2. make sure persisted sandbox result retrieval also returns the same interaction output shape
3. add or update tests that prove those two paths match
4. verify degraded / reused agent paths do not break the new response contract

---

## 6. Files You May Work In

These are the expected files for your scope:

- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/sandbox.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/sandbox.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_api_sandbox.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_api_sandbox.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_sandbox_stability.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_sandbox_stability.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/helpers/sandbox_assertions.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/helpers/sandbox_assertions.py)

You may need to inspect these too:

- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/schemas/memory.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/schemas/memory.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py)

---

## 7. Files You Should Not Redesign

These are owned by the main agent for this phase:

- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/schemas/reports.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/schemas/reports.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/services/synthesis.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/services/synthesis.py)
- [`/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py)

You can inspect these files for integration context.

But do not independently redefine:

- interaction schema names
- interaction field semantics
- round-level interaction summary semantics

If integration requires a small surgical change inside these files, note it clearly rather than taking ownership of the semantic design.

---

## 8. Non-Goals

Do not do these things:

1. do not redesign the product logic
2. do not create a new interpretation of what “interaction resolution” means
3. do not rename canonical fields once the main agent defines them
4. do not build frontend rendering for this task
5. do not over-expand persistence with a full graph if only summary persistence is needed
6. do not silently create divergence between live response and persisted response

This task is about **integration discipline**, not invention.

---

## 9. Technical Integration Map

These are the main touchpoints you should understand:

### 9.1 Live response path

File:
- [`sandbox.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/sandbox.py)

Function:
- `run_sandbox()`

Behavior:
- returns live in-memory `round_complete` and `report`
- this path usually gets new fields “for free” once the underlying schema changes

Risk:
- live output can look correct even when persisted retrieval is still missing fields

### 9.2 Persisted response path

File:
- [`sandbox.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/sandbox.py)

Functions:
- `_serialize_report_record()`
- `_serialize_checkpoint()`

Behavior:
- reconstructs persisted report output manually
- already has custom logic for rebuilding `action_detail`

Risk:
- this path can drift from live output if new interaction fields are not explicitly persisted and serialized back out

### 9.3 Report persistence

File:
- [`secondary.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py)

Function:
- `_persist_report_record()`

Behavior:
- persists report-oriented JSON structures

Risk:
- if new interaction output is only present in memory and never written into `ReportRecord`, `/sandbox/{id}/result` will not match `/sandbox/run`

### 9.4 Checkpoint persistence

File:
- [`secondary.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/orchestrator/secondary.py)

Function:
- `_persist_checkpoint()`

Guideline:
- checkpoint should only carry summary-level interaction metadata
- do not store the full interaction graph here unless explicitly required

### 9.5 Tests most likely to require updates

Files:
- [`test_api_sandbox.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_api_sandbox.py)
- [`test_sandbox_stability.py`](/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/tests/unit/test_sandbox_stability.py)

Why:
- one covers API contract
- one covers degraded / reused fallback behavior

---

## 10. Expected Implementation Strategy

Use this sequence:

1. inspect current persistence path
2. inspect current serializer path
3. inspect current tests
4. wait for or read the main agent’s canonical interaction schema
5. wire interaction output into persistence
6. wire interaction output into persisted serializer output
7. update tests to assert parity between live and persisted paths

Do not start from the tests alone.
First understand where the data is written and where it is reconstructed.

---

## 11. Standard for “Done”

Your work is done only if all of the following are true:

1. live sandbox response includes the expected interaction output
2. persisted sandbox result response includes the same interaction output shape
3. degraded / reused paths still produce a valid response
4. the new tests prove those claims
5. there is no silent mismatch between `/sandbox/run` and `/sandbox/{id}/result`

If live and persisted outputs are structurally different, the task is **not done**.

---

## 12. Validation Commands

At minimum, run:

```bash
python3 -m pytest -q tests/unit/test_api_sandbox.py
python3 -m pytest -q tests/unit/test_sandbox_stability.py
```

If your changes touch broader report or persistence behavior, also run:

```bash
python3 -m pytest -q
```

If a command fails because the local environment differs from CI, note the reason explicitly.

Do not claim success without giving real test results.

---

## 13. Git / Workflow Rules

Follow the repo protocol:

1. plan first
2. create or update a task note under `doc/claude/task/`
3. inspect git status before editing
4. commit intentionally
5. verify before handing back

If you create your own task note, keep it specific and implementation-oriented.

---

## 14. What To Report Back

When you finish, report back in this structure:

### A. Files changed

List exact file paths.

### B. What was integrated

State:
- where interaction output is persisted
- where it is serialized
- whether checkpoint summary changed

### C. Test coverage

List:
- tests added or changed
- commands run
- results

### D. Contract status

Answer explicitly:
- do live and persisted responses now match
- do degraded / reused branches still work

### E. Remaining blockers

List anything that still depends on the main agent’s schema work.

---

## 15. Short Summary

Your job is:

**take the main agent’s interaction output and make sure it survives persistence, comes back through the API, and is covered by tests without drifting between live and persisted response paths.**

That is the entire assignment.
