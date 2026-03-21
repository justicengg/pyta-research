# Legacy World Cleanup Audit

This document is a **cleanup audit list**, not a deletion checklist.
Its purpose is to help future cleanup work identify which files likely belong to the pre-rebuild world and should be reviewed after the rebuilt secondary-market line is stable.

## Cleanup Principle

Do not delete first.

Use this order:

1. confirm the rebuilt secondary-market implementation is the active source of truth
2. compare old files against the current implementation and handoff manual
3. decide one of:
   - keep
   - archive
   - replace
   - delete
4. execute cleanup in a separate pass

## Current Source Of Truth

For the rebuilt secondary-market line, the primary source of truth is now:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/SECONDARY_MARKET_BRANCH_HANDOFF.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox`
- `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/01 项目主结构/Layer 2`
- `/Users/sikaijiang/Documents/Obsidian Vault/PYTA/02 交互与界面`

## High-Priority Audit Targets

These areas most likely contain pre-rebuild concepts or legacy surfaces that may need archiving or deletion later.

### 1. Old product/API surfaces

Review whether these are still part of the intended product after the rebuild:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/actions.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/cards.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/dashboard.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/decision.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/executions.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/portfolio.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/risk.py`

Reason for audit:
- these routes appear aligned with the older action/decision/portfolio world
- the rebuilt MVP now centers on `sandbox.py` and the frontend canvas flow

### 2. Old server-rendered dashboard surface

Review whether this should be archived once the new frontend fully replaces it:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/templates/dashboard.html`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/dashboard.py`

Reason for audit:
- the rebuilt canvas UI now lives under `frontend/`
- this older template surface may become redundant

### 3. Old decision / action / execution domain modules

Review whether these modules still belong to the active system:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/decision`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/portfolio`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/risk`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/strategy`

Reason for audit:
- these names strongly suggest the older recommendation / action / trade-log world
- the rebuilt secondary-market MVP intentionally moved away from buy/sell/hold and execution-first semantics

### 4. Old migrations tied to pre-rebuild domains

Review older Alembic revisions before deleting anything:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260301_0001_init_schema.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260302_0002_add_derived_factors.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260302_0003_add_strategy_card.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260302_0004_add_trade_log.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260305_0005_strategy_card_v2_fields.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/alembic/versions/20260305_0006_add_action_queue_execution_log.py`

Reason for audit:
- these may still be needed for database history
- they should not be deleted casually
- but they likely represent the old world and should be reviewed against the new product direction

## Medium-Priority Audit Targets

These may still be useful, but need review against the rebuilt product direction.

### 1. Reporting modules

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/report`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/quality`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/screener`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/scheduler`

Reason for audit:
- some of these may still be useful as infrastructure
- some may be attached to older output/report concepts

### 2. Legacy docs

Review whether these docs remain active, need archiving, or should be replaced by the new frontend/canvas docs:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/README_PHASE5.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/FRAMEWORK.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/ERD.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/USAGE.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/CHANGELOG.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/FAQ.md`

Reason for audit:
- these may describe the old architecture or old usage path
- the new handoff doc may already supersede parts of them

## Low-Priority / Keep For Now

These are not current cleanup priorities.

### 1. Rebuilt sandbox implementation

Keep and treat as active:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/api/routers/sandbox.py`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/frontend`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/SECONDARY_MARKET_BRANCH_HANDOFF.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/RESEARCH_CANVAS_DESIGN_SPEC.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/UI_SYSTEM_STANDARD_MANUAL.md`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/docs/multi_agent_sandbox_fusion_direction.html`

### 2. Fetchers / shared infra

Keep for now unless product direction explicitly removes them:

- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/fetchers`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/config`
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/db`

## Suggested Cleanup Method Later

When the team is ready, perform cleanup in this order:

1. document which routes/pages are still actively used
2. archive or remove old server-rendered dashboard assets
3. review old API routers one by one
4. review old domain modules one by one
5. review docs and keep only the current source-of-truth set
6. only then consider migration strategy cleanup

## What Not To Do

Do not:

- mass-delete old files in one pass
- remove old migrations without understanding database history
- delete old docs before replacing their useful information
- mix legacy cleanup with active feature work

## Practical Next Step

When cleanup begins, start with a small audit issue or checklist such as:

1. verify whether `dashboard.html` is still referenced
2. verify whether non-sandbox API routers are still needed
3. verify whether `strategy` / `portfolio` / `decision` modules are still product-critical
4. move obsolete docs into an archive folder before deleting anything
