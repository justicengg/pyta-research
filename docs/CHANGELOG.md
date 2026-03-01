# Changelog

## 2026-03-01 - Phase 1 MVP (INV-31 ~ INV-36)
- Added project Python scaffold with SQLAlchemy, Alembic, APScheduler, CLI, and tests.
- Added schema migration for raw_price/raw_fundamental/raw_macro with unique constraints and indexes.
- Added fetcher abstractions and implementations for market/fundamental/macro ingestion.
- Added quality checker rules and JSON report output.
- Added scheduler run-once/start orchestration with retry and logging.
- Added unit and integration tests for schema, dedupe, quality CLI, and scheduler.
