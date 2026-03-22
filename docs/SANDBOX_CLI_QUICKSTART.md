# Sandbox CLI Quickstart

This document explains how to run the rebuilt secondary-market sandbox from the command line.

## CLI Entry

Main file:
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/cli.py`

Helper file:
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp/src/sandbox/cli_helpers.py`

Run commands from:
- `/Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp`

## Basic Rule

The CLI currently supports **structured file input only**.

Your input file must be one of these:
- a JSON array of events
- a JSON object with an `events` array

## Minimal Example Input

Example file: `/tmp/pyta_events.json`

```json
{
  "events": [
    {
      "event_type": "manual_input",
      "source": "user",
      "content": "Tencent announced a new AI product update and the market is discussing whether this can improve long-term monetization.",
      "importance": 0.7
    }
  ]
}
```

## Command 1: Run One Secondary-Market Sandbox

```bash
cd /Users/sikaijiang/Desktop/pyta-research-worktrees/secondary-market-mvp

python -m src.sandbox.cli sandbox run-secondary \
  --ticker 0700.HK \
  --market HK \
  --input /tmp/pyta_events.json \
  --json
```

What it does:
- starts one secondary-market sandbox run
- runs the five market participant agents
- returns round result and report JSON

## Command 2: Inspect A Previous Sandbox

```bash
python -m src.sandbox.cli sandbox inspect \
  --sandbox-id <sandbox_id> \
  --json
```

What it does:
- loads the persisted sandbox result
- prints the latest report/checkpoint data

## Command 3: Replay A Previous Sandbox

```bash
python -m src.sandbox.cli sandbox replay-last \
  --sandbox-id <sandbox_id>
```

What it does:
- reuses the last sandbox input
- runs another round with the current code path

## Command 4: Dry-Run One Agent

```bash
python -m src.sandbox.cli sandbox agent-dry-run \
  --agent traditional_institution \
  --ticker 0700.HK \
  --market HK \
  --input /tmp/pyta_events.json \
  --json
```

What it does:
- runs only one agent
- useful for prompt tuning and debugging

Supported agents:
- `traditional_institution`
- `quant_institution`
- `retail`
- `offshore_capital`
- `short_term_capital`

## If You Want Real LLM Output

Make sure your local environment is configured before running the CLI.

Example runtime env:

```bash
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL=MiniMax-M2.5-highspeed
LLM_API_KEY=...
```

If model config is missing, the CLI may fall back to stub behavior depending on the code path.

## Recommended Use

Use the CLI when you want to:
- quickly test the sandbox without the frontend
- inspect persisted results
- replay a previous case
- debug one specific agent
