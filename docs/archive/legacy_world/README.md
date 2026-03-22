# Legacy World Archive

This directory contains files from the pre-rebuild world.

They were archived on 2026-03-22 as part of the secondary-market MVP cleanup pass.

## Why archived, not deleted

- These files may contain useful reference logic or past design decisions.
- Nothing in the active sandbox pipeline depends on them.
- They should not be deleted until the product direction is fully stable (suggested review: 3 months after archiving).

## What is here

| File / Directory | Original path | Reason |
|------------------|---------------|--------|
| `cli.py` | `src/cli.py` | Entire file is legacy pipeline commands (fetch / screener / strategy / portfolio / decision / risk / report / quality). Active sandbox CLI lives at `src/sandbox/cli.py`. |
| `routers/actions.py` | `src/api/routers/actions.py` | Legacy action queue API — old world |
| `routers/cards.py` | `src/api/routers/cards.py` | Legacy strategy cards API — old world |
| `routers/dashboard.py` | `src/api/routers/dashboard.py` | Legacy server-rendered dashboard — replaced by frontend/ |
| `routers/decision.py` | `src/api/routers/decision.py` | Legacy decision/buy/sell/hold API — old world |
| `routers/executions.py` | `src/api/routers/executions.py` | Legacy execution log API — old world |
| `routers/portfolio.py` | `src/api/routers/portfolio.py` | Legacy portfolio snapshot API — old world |
| `routers/risk.py` | `src/api/routers/risk.py` | Legacy risk check API — old world |
| `templates/dashboard.html` | `src/api/templates/dashboard.html` | Legacy server-rendered dashboard HTML — replaced by frontend/ |
| `domain/decision/` | `src/decision/` | Legacy decision advisor — buy/sell/hold world |
| `domain/portfolio/` | `src/portfolio/` | Legacy portfolio tracker — old world |
| `domain/risk/` | `src/risk/` | Legacy risk checker — old world |
| `domain/strategy/` | `src/strategy/` | Legacy strategy card generator — stop-loss, target price world |

## Active CLI reference

The current developer CLI is:

```bash
python -m src.sandbox.cli sandbox run-secondary ...
python -m src.sandbox.cli sandbox inspect ...
python -m src.sandbox.cli sandbox replay-last ...
python -m src.sandbox.cli sandbox agent-dry-run ...
```

See: `docs/SANDBOX_CLI_QUICKSTART.md`
