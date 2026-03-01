# pyta-research

PYTA Investment Framework 的 Phase 1（数据管道）MVP 实现。

## Scope (M1-T1 ~ M1-T6)
- M1-T1: PostgreSQL schema + Alembic migration
- M1-T2: 市场行情采集（baostock + yfinance）
- M1-T3: 财务数据采集（Point-in-time）
- M1-T4: 宏观数据采集（FRED + baostock）
- M1-T5: 数据质量检查与 CLI 报告
- M1-T6: APScheduler 日常调度（18:00）

## Quick Start

### 1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install sqlalchemy alembic pydantic-settings apscheduler requests yfinance python-dateutil psycopg2-binary pytest
```

### 2. Configure env
```bash
cp .env.example .env
# 修改 DATABASE_URL/FRED_API_KEY
```

### 3. Apply migration
```bash
alembic upgrade head
```

### 4. CLI examples
```bash
python -m src.cli fetch market --source yfinance --symbol SPY --market US --start 2026-01-01 --end 2026-02-01 --incremental
python -m src.cli fetch fundamental --symbol 600000 --market CN --asof 2026-02-01 --incremental
python -m src.cli fetch macro --series CPIAUCSL --source fred --market US --start 2025-01-01 --end 2026-02-01 --incremental
python -m src.cli quality check --table raw_price --date 2026-02-01 --out /tmp/quality.json
python -m src.cli scheduler run-once
```

## Testing
```bash
pytest
```

## Docs
- [FRAMEWORK](docs/FRAMEWORK.md)
- [USAGE](docs/USAGE.md)
- [CHANGELOG](docs/CHANGELOG.md)
- [FAQ](docs/FAQ.md)
- [ERD](docs/ERD.md)
